from typing import Any, Dict, List, Optional, Type, cast
import asyncio
import json
import os
import re
import time
from loguru import logger

from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import BaseTool, tool
from langchain_core.output_parsers import PydanticOutputParser
from langchain.tools import ReadFileTool, WriteFileTool
from langchain.agents import AgentExecutor, create_structured_chat_agent

from .base_agent import BaseAgent
from utils.web_search import WebSearch, WebSearchTool
from utils.shell_executor import ShellExecutor, ShellExecutorTool


class Exception(BaseModel):
    """Information about an exception."""
    type: str = Field(description="Type of exception (e.g., 'SyntaxError', 'TypeError', 'ImportError')")
    message: str = Field(description="Error message from the exception")
    file: Optional[str] = Field(None, description="File where the exception occurred")
    line: Optional[int] = Field(None, description="Line number where the exception occurred")
    traceback: Optional[str] = Field(None, description="Full traceback of the exception")


class Fix(BaseModel):
    """Information about a fix applied to resolve an exception."""
    file: str = Field(description="File that was modified")
    description: str = Field(description="Description of the fix applied")
    diff: str = Field(description="Diff showing the changes made")
    resolved_exception: Optional[str] = Field(None, description="Type of exception that was resolved")


class BuildResult(BaseModel):
    """Result of a build and run attempt."""
    success: bool = Field(description="Whether the build and run was successful")
    exceptions: List[Exception] = Field(default_factory=list, description="Exceptions encountered during build/run")
    output: str = Field(description="Output from the build/run process")
    command: str = Field(description="Command that was executed")


class DebugResult(BaseModel):
    """Complete debugging result."""
    status: str = Field(description="Status of debugging (e.g., 'fixed', 'in_progress', 'failed')")
    initial_exceptions: List[Exception] = Field(description="Exceptions found in the initial run")
    fixes_applied: List[Fix] = Field(description="Fixes that were applied to resolve exceptions")
    remaining_exceptions: List[Exception] = Field(default_factory=list, description="Exceptions that still need to be fixed")
    build_attempts: int = Field(description="Number of build attempts made")
    final_build_result: Optional[BuildResult] = Field(None, description="Result of the final build attempt")
    research_findings: Optional[Dict[str, str]] = Field(None, description="Research findings for exceptions")


class ExceptionDebuggerAgent(BaseAgent):
    """Exception Debugger Agent.
    
    This agent is responsible for testing the final solution, detecting exceptions,
    and resolving issues.
    """
    
    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize the Exception Debugger Agent with specialized tools."""
        super().__init__(*args, **kwargs)
        
        # Create debugging tools
        debugging_tools = self._create_debugging_tools()
        self.tools.extend(debugging_tools)
        
        # Re-create the agent executor with the new tools
        self.agent_executor = self._create_agent_executor()
        
        # Track build attempts
        self.build_attempts = 0
        self.max_build_attempts = 10  # Maximum number of build attempts before giving up
    
    def _get_agent_system_message(self) -> str:
        """Override system message for the exception debugger agent."""
        return """You are an expert Exception Debugger Agent specialized in building, running, and fixing code.

Your task is to build and run the final solution, detect exceptions, and resolve issues until the code runs successfully.
You should:
- Build and run the code to identify any exceptions
- Analyze exceptions to determine their root cause
- Research solutions for the exceptions
- Apply fixes to resolve the exceptions
- Re-run the code to verify the fixes
- Continue this process until all exceptions are resolved

IMPORTANT: You MUST NOT STOP until all exceptions have been resolved and the code runs successfully.
If you encounter difficult exceptions, research them thoroughly and try multiple approaches.
Only ask for human input when you've exhausted all automated debugging options.

Provide clear, structured output including exceptions found, fixes applied, and build results.
Be persistent and methodical in your debugging approach.
"""
    
    def _create_debugging_tools(self) -> List[BaseTool]:
        """Create specialized tools for debugging tasks."""
        
        # Add standard tools
        read_file_tool = ReadFileTool()
        write_file_tool = WriteFileTool()
        web_search_tool = WebSearchTool(web_search=WebSearch())
        shell_executor_tool = ShellExecutorTool()
        
        @tool("build_and_run")
        def build_and_run(command: str, working_directory: Optional[str] = None) -> str:
            """
            Build and run the code to check for exceptions.
            
            Args:
                command: The command to build and run the code
                working_directory: Optional working directory for the command
                
            Returns:
                A JSON string containing the build and run results
            """
            parser = PydanticOutputParser(pydantic_object=BuildResult)
            
            # Execute the command
            shell_executor = ShellExecutor()
            
            try:
                # Increment build attempts counter
                self.build_attempts += 1
                logger.info(f"Build attempt #{self.build_attempts}: {command}")
                
                # Run the command
                result = asyncio.run(shell_executor.run_async(
                    command=command,
                    timeout=60,  # 1 minute timeout
                    cwd=working_directory
                ))
                
                # Parse the output for exceptions
                stdout = result.get("stdout", "")
                stderr = result.get("stderr", "")
                combined_output = stdout + "\n" + stderr
                
                # Check for common exception patterns
                exceptions = []
                
                # Python exceptions
                python_exceptions = re.findall(r'(Traceback \(most recent call last\):.*?)(?=\n\S|$)', 
                                              combined_output, re.DOTALL)
                
                for traceback in python_exceptions:
                    # Extract exception type and message
                    exception_match = re.search(r'(\w+Error|Exception): (.+?)$', traceback, re.MULTILINE)
                    if exception_match:
                        exception_type = exception_match.group(1)
                        exception_message = exception_match.group(2)
                        
                        # Try to extract file and line number
                        file_line_match = re.search(r'File "([^"]+)", line (\d+)', traceback)
                        file = file_line_match.group(1) if file_line_match else None
                        line = int(file_line_match.group(2)) if file_line_match else None
                        
                        exceptions.append({
                            "type": exception_type,
                            "message": exception_message,
                            "file": file,
                            "line": line,
                            "traceback": traceback
                        })
                
                # JavaScript/Node.js exceptions
                js_exceptions = re.findall(r'(\w+Error: .+?(?:\n\s+at .+)+)', combined_output, re.DOTALL)
                
                for traceback in js_exceptions:
                    # Extract exception type and message
                    exception_match = re.search(r'(\w+Error): (.+?)$', traceback, re.MULTILINE)
                    if exception_match:
                        exception_type = exception_match.group(1)
                        exception_message = exception_match.group(2)
                        
                        # Try to extract file and line number
                        file_line_match = re.search(r'at .+? \((.+?):(\d+):\d+\)', traceback)
                        file = file_line_match.group(1) if file_line_match else None
                        line = int(file_line_match.group(2)) if file_line_match else None
                        
                        exceptions.append({
                            "type": exception_type,
                            "message": exception_message,
                            "file": file,
                            "line": line,
                            "traceback": traceback
                        })
                
                # Create the build result
                build_result = {
                    "success": result.get("success", False) and len(exceptions) == 0,
                    "exceptions": exceptions,
                    "output": combined_output,
                    "command": command
                }
                
                return json.dumps(build_result)
            except Exception as e:
                logger.error(f"Error in build and run: {str(e)}")
                return json.dumps({
                    "success": False,
                    "exceptions": [
                        {
                            "type": "BuildError",
                            "message": f"Error executing build command: {str(e)}",
                            "file": None,
                            "line": None,
                            "traceback": str(e)
                        }
                    ],
                    "output": f"Error: {str(e)}",
                    "command": command
                })
        
        @tool("research_exception")
        def research_exception(exception_type: str, exception_message: str) -> str:
            """
            Research an exception to find potential solutions.
            
            Args:
                exception_type: The type of exception (e.g., 'SyntaxError', 'TypeError')
                exception_message: The error message from the exception
                
            Returns:
                JSON string with research findings and potential solutions
            """
            prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content=f"""
                You are an exception research expert. Research the following exception and provide solutions:
                
                Exception Type: {exception_type}
                Error Message: {exception_message}
                
                Provide:
                1. A brief explanation of what causes this exception
                2. At least 3 potential solutions with code examples
                3. Common mistakes that lead to this exception
                
                Format your response as a JSON object with these fields:
                {{
                    "explanation": "Brief explanation of the exception",
                    "solutions": [
                        {{
                            "description": "Solution description",
                            "code_example": "Code example"
                        }},
                        ...
                    ],
                    "common_mistakes": ["Mistake 1", "Mistake 2", ...]
                }}
                """)
            ])
            
            # Use the web search tool to gather information
            web_search = WebSearch()
            search_query = f"{exception_type} {exception_message} solution"
            
            try:
                # Search for solutions
                search_results = asyncio.run(web_search.search_and_fetch(search_query, num_results=3))
                
                # Extract content from search results
                content = "\n\n".join([
                    f"Title: {result.get('title', '')}\n" +
                    f"URL: {result.get('url', '')}\n" +
                    f"Content: {result.get('content', '')[:1000]}..."
                    for result in search_results
                ])
                
                # Generate research findings using the LLM
                chain = prompt | self.llm
                result = chain.invoke({"content": content})
                
                return result.content
            except Exception as e:
                logger.error(f"Error researching exception: {str(e)}")
                return json.dumps({
                    "explanation": f"Error researching exception: {str(e)}",
                    "solutions": [
                        {
                            "description": "Generic solution based on exception type",
                            "code_example": "# Example code not available due to research error"
                        }
                    ],
                    "common_mistakes": ["Unable to retrieve common mistakes due to research error"]
                })
        
        @tool("apply_fix")
        def apply_fix(file_path: str, original_content: str, fixed_content: str) -> str:
            """
            Apply a fix to a file and generate a diff of the changes.
            
            Args:
                file_path: Path to the file to fix
                original_content: Original content of the file
                fixed_content: Fixed content to write to the file
                
            Returns:
                JSON string with the fix details including a diff
            """
            try:
                # Generate a simple diff
                import difflib
                
                diff = '\n'.join(difflib.unified_diff(
                    original_content.splitlines(),
                    fixed_content.splitlines(),
                    fromfile=f'a/{file_path}',
                    tofile=f'b/{file_path}',
                    lineterm=''
                ))
                
                # Write the fixed content to the file
                with open(file_path, 'w') as f:
                    f.write(fixed_content)
                
                # Create a description of the fix
                if len(diff.splitlines()) > 2:  # Ignore the file headers in the diff
                    description = f"Applied fix to {file_path}"
                else:
                    description = "No changes were made to the file"
                
                return json.dumps({
                    "file": file_path,
                    "description": description,
                    "diff": diff
                })
            except Exception as e:
                logger.error(f"Error applying fix: {str(e)}")
                return json.dumps({
                    "file": file_path,
                    "description": f"Error applying fix: {str(e)}",
                    "diff": ""
                })
        
        @tool("ask_human")
        def ask_human(question: str) -> str:
            """
            Ask the human for input when automated debugging is stuck.
            
            Args:
                question: The question to ask the human
                
            Returns:
                A placeholder for human response
            """
            logger.info(f"Asking human: {question}")
            
            # In a real implementation, this would wait for human input
            # For now, we'll just return a placeholder
            return json.dumps({
                "question": question,
                "response": "This is a placeholder for human response. In a real implementation, this would wait for human input."
            })
        
        return [build_and_run, research_exception, apply_fix, ask_human, read_file_tool, write_file_tool, web_search_tool, shell_executor_tool]
    
    async def execute(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        """Execute the agent's main task - debugging code.
        
        Args:
            prompt: The input prompt describing debugging task
            **kwargs: Additional parameters for execution, including:
                code: The code to debug
                build_command: Command to build and run the code
                working_directory: Working directory for the build command
            
        Returns:
            Dictionary containing the debugging results
        """
        logger.info(f"Exception Debugger Agent {self.name} executing with prompt: {prompt[:100]}...")
        
        # Reset build attempts counter
        self.build_attempts = 0
        
        # Get parameters from kwargs
        code = kwargs.get("code", {})
        build_command = kwargs.get("build_command", "")
        working_directory = kwargs.get("working_directory", os.getcwd())
        
        if not code and not build_command:
            logger.warning("No code or build command provided for debugging")
            return {
                "success": False,
                "error": "No code or build command provided for debugging",
                "message": "Debugging failed - no code or build command provided"
            }
        
        try:
            # Prepare the input for the agent
            debug_input = f"""
            Debug the following code:
            
            {prompt}
            
            Build Command: {build_command}
            Working Directory: {working_directory}
            
            Your task is to:
            1. Build and run the code to identify any exceptions
            2. Analyze and fix each exception
            3. Continue until the code runs successfully without exceptions
            
            DO NOT STOP until all exceptions are resolved.
            """
            
            # Create a combined input with the prompt and history
            combined_input = debug_input
            if self.conversation_history:
                combined_input += "\n\nPrevious conversation:\n" + "\n".join(self.conversation_history)
            
            # Execute the agent
            logger.debug("Starting exception debugging process...")
            result = await self.agent_executor.ainvoke({
                "input": combined_input
            })
            
            # If successful, try to parse the debug result from the output
            if result:
                try:
                    # Try to extract structured debug result from the response
                    raw_output = result.get("output", "")
                    
                    # Look for JSON in the output
                    json_match = re.search(r'```json\n(.*?)\n```', raw_output, re.DOTALL)
                    
                    if json_match:
                        debug_json = json_match.group(1)
                    else:
                        # Try to find any JSON-like structure
                        json_match = re.search(r'({.*})', raw_output, re.DOTALL)
                        debug_json = json_match.group(1) if json_match else raw_output
                    
                    # Parse the JSON
                    debug_result = json.loads(debug_json)
                    
                    # If it doesn't have the expected structure, create a basic result
                    if not all(k in debug_result for k in ["status", "fixes_applied"]):
                        logger.warning("Debug result missing expected fields, creating basic result")
                        debug_result = {
                            "status": "completed",
                            "initial_exceptions": [],
                            "fixes_applied": [],
                            "remaining_exceptions": [],
                            "build_attempts": self.build_attempts,
                            "final_build_result": None
                        }
                    
                    # Add the debug result to the conversation
                    fixes_count = len(debug_result.get("fixes_applied", []))
                    remaining = len(debug_result.get("remaining_exceptions", []))
                    status = debug_result.get("status", "unknown")
                    
                    self.add_to_conversation(
                        "assistant", 
                        f"Debugging completed with status: {status}. Applied {fixes_count} fixes. Remaining exceptions: {remaining}."
                    )
                    
                    logger.info(f"Debugging complete with status {status}, applied {fixes_count} fixes")
                    return {
                        "success": status == "fixed" or status == "completed",
                        "debug_result": debug_result,
                        "message": f"Debugging completed with status: {status}"
                    }
                    
                except Exception as parse_error:
                    logger.warning(f"Error parsing debug result: {str(parse_error)}")
                    # Create a basic result from the raw output
                    debug_result = {
                        "status": "completed",
                        "initial_exceptions": [],
                        "fixes_applied": [],
                        "remaining_exceptions": [],
                        "build_attempts": self.build_attempts,
                        "raw_output": raw_output
                    }
                    
                    self.add_to_conversation(
                        "assistant", 
                        f"Debugging completed but encountered parsing errors. Build attempts: {self.build_attempts}."
                    )
                    
                    return {
                        "success": True,
                        "debug_result": debug_result,
                        "message": "Debugging completed with parsing errors"
                    }
            
            # If we get here, something went wrong with the agent execution
            logger.warning("Agent execution did not return expected result")
            return {
                "success": False,
                "error": "Agent execution failed to return valid results",
                "message": "Debugging failed"
            }
            
        except Exception as e:
            logger.exception(f"Debugging failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "Debugging failed"
            }
