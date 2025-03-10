from typing import Any, Dict, List, Optional
import asyncio
import json
import os
import sys
from pathlib import Path
from loguru import logger
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import AgentExecutor, create_structured_chat_agent
from langchain.tools import BaseTool, Tool
from langchain.tools.file_management import ReadFileTool, WriteFileTool

from .base_agent import BaseAgent


class EmitFileUpdateToUI(BaseTool):
    """Tool for emitting file updates to the dashboard UI."""
    name: str = "emit_file_update"
    description: str = "Send file content updates to the dashboard UI"
    dashboard_mode: bool = False
    
    def __init__(self, dashboard_mode: bool = False):
        super().__init__()
        self.dashboard_mode = dashboard_mode
    
    def _run(self, file_path: str, content: str) -> str:
        """Emit the file update to the UI."""
        if self.dashboard_mode:
            # Format the update for the dashboard
            update = {
                "type": "fileChange",
                "filePath": file_path,
                "content": content
            }
            # Print a special marker that will be caught by the dashboard
            print(f"DASHBOARD_UPDATE:{json.dumps(update)}")
            return f"File update for {file_path} sent to dashboard UI"
        else:
            return "Dashboard updates disabled (not in dashboard mode)"


class SoftwareProgrammerAgent(BaseAgent):
    """Software Programmer Agent.
    
    This agent is responsible for writing code as specified by the 
    Software Planner Agent.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dashboard_mode = "--dashboard-mode" in sys.argv
        self.code_files = {}
        
        # Get dashboard mode from config if provided
        if kwargs.get("config") and isinstance(kwargs["config"], dict):
            if kwargs["config"].get("dashboard_mode"):
                self.dashboard_mode = True
                
        # Log dashboard mode for debugging
        print(f"SoftwareProgrammerAgent initialized with dashboard_mode={self.dashboard_mode}")
    
    async def execute(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        """Execute the agent's main task - writing code.
        
        Args:
            prompt: The input prompt describing code to write
            **kwargs: Additional parameters for execution
            
        Returns:
            Dictionary containing the code generation results
        """
        logger.info(f"Software Programmer Agent {self.name} executing with prompt: {prompt[:100]}...")
        
        # Get the software plan if it was provided
        software_plan = kwargs.get("software_plan", {})
        
        # Custom tools for the programmer agent
        read_file_tool = ReadFileTool()
        write_file_tool = WriteFileTool()
        file_update_tool = EmitFileUpdateToUI(dashboard_mode=self.dashboard_mode)
        
        # Add a file creation tool that both writes the file and updates the UI
        def create_file_with_ui_update(file_path: str, content: str) -> str:
            """Create a file and update the UI dashboard."""
            # Ensure directory exists
            directory = os.path.dirname(file_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
            
            # Write the file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Store the file info
            self.code_files[file_path] = content
            
            # Update the UI if in dashboard mode
            if self.dashboard_mode:
                file_update_tool._run(file_path, content)
            
            return f"File {file_path} created successfully"
        
        create_file_tool = Tool(
            name="create_file",
            description="Create a new file with the given content. Also updates the dashboard UI.",
            func=create_file_with_ui_update
        )
        
        tools = [read_file_tool, create_file_tool, file_update_tool]
        
        # Create a specialized prompt for the software programmer
        system_prompt = """You are a Software Programmer Agent.
        Your task is to write clean, well-structured code as specified by the Software Planner Agent.
        
        Implement the code files required based on the software plan and provided specifications.
        For each file you create:
        1. Consider design patterns appropriate for the task
        2. Add proper error handling
        3. Include useful comments and docstrings
        4. Follow consistent naming conventions
        5. Ensure proper imports
        
        Use the create_file tool to create each file, which will automatically update the dashboard UI.
        
        IMPORTANT: When creating files, provide the FULL content of the file, not just snippets.
        """
        
        if software_plan:
            system_prompt += """
            The software plan includes the following structure:
            - Files to create: {files}
            - Module structure: {modules}
            - Key interfaces: {interfaces}
            """
        
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="history"),
            ("user", "{input}"),
        ])
        
        # Format the system prompt with software plan details if available
        if software_plan:
            files_str = "\n- " + "\n- ".join(software_plan.get("files", []))
            modules_str = json.dumps(software_plan.get("modules", []), indent=2)
            interfaces_str = json.dumps(software_plan.get("interfaces", {}), indent=2)
            prompt_template = prompt_template.partial(
                files=files_str,
                modules=modules_str,
                interfaces=interfaces_str
            )
        
        try:
            # Execute the agent
            logger.debug("Generating code...")
            # Create a combined input with the prompt and history
            combined_input = prompt
            if self.conversation_history:
                combined_input += "\n\nPrevious conversation:\n" + "\n".join(self.conversation_history)
            
            result = await self.agent_executor.ainvoke({
                "input": combined_input
            })
            
            # Collect code metadata
            code_metadata = {
                "files_generated": len(self.code_files),
                "total_lines": sum(len(content.split("\n")) for content in self.code_files.values()),
                "language_distribution": {
                    "python": sum(1 for f in self.code_files.keys() if f.endswith('.py')),
                    "javascript": sum(1 for f in self.code_files.keys() if f.endswith(('.js', '.ts')))
                }
            }
            
            # Add the response to the conversation history
            summary = f"Code generation completed. Generated {code_metadata['files_generated']} files with {code_metadata['total_lines']} total lines."
            self.add_to_conversation("assistant", summary)
            
            logger.info(f"Code generation complete, created {len(self.code_files)} files")
            return {
                "success": True,
                "code": {
                    "files": self.code_files,
                    "metadata": code_metadata
                },
                "message": "Code generation completed successfully",
                "output": result.get("output", "")
            }
            
        except Exception as e:
            logger.exception(f"Code generation failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "Code generation failed"
            }
