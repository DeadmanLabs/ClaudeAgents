from typing import Any, Dict, List, Optional, Type, cast
import asyncio
import json
import os
import re
from loguru import logger

from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.messages import SystemMessage
from langchain_core.tools import BaseTool, tool
from langchain_core.output_parsers import PydanticOutputParser
from langchain.tools import ReadFileTool
from langchain.agents import AgentExecutor, create_structured_chat_agent

from .base_agent import BaseAgent
from utils.web_search import WebSearch, WebSearchTool
from utils.shell_executor import ShellExecutor, ShellExecutorTool


class DependencyIssue(BaseModel):
    """Issue with a dependency."""
    type: str = Field(description="Type of issue (e.g., 'missing_dependency', 'version_conflict', 'security_vulnerability')")
    severity: str = Field(description="Severity level (e.g., 'info', 'warning', 'error', 'critical')")
    description: str = Field(description="Detailed description of the issue")
    file: Optional[str] = Field(None, description="File where the issue was found")
    line: Optional[int] = Field(None, description="Line number where the issue was found")
    recommendation: Optional[str] = Field(None, description="Recommended action to resolve the issue")


class DependencyInfo(BaseModel):
    """Information about a single dependency."""
    name: str = Field(description="Name of the dependency")
    version: Optional[str] = Field(None, description="Version or version constraint")
    usage_locations: List[str] = Field(description="Files where the dependency is used")
    issues: List[DependencyIssue] = Field(default_factory=list, description="Issues related to this dependency")
    alternatives: List[Dict[str, str]] = Field(default_factory=list, description="Alternative libraries that could be used instead")


class DependencyAnalysis(BaseModel):
    """Complete dependency analysis result."""
    status: str = Field(description="Status of the analysis (e.g., 'completed', 'partial', 'failed')")
    external_dependencies: Dict[str, List[DependencyInfo]] = Field(description="External dependencies by language")
    internal_dependencies: Dict[str, List[str]] = Field(description="Internal dependencies by file")
    issues: List[DependencyIssue] = Field(description="Overall issues found during analysis")
    recommendations: List[str] = Field(description="Recommendations for improving dependencies")


class DependencyAnalyzerAgent(BaseAgent):
    """Dependency Analyzer Agent.
    
    This agent is responsible for analyzing a codebase to map out all internal
    and external dependencies and identify potential issues.
    """
    
    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize the Dependency Analyzer Agent with specialized tools."""
        super().__init__(*args, **kwargs)
        
        # Create dependency analysis tools
        dependency_tools = self._create_dependency_tools()
        self.tools.extend(dependency_tools)
        
        # Re-create the agent executor with the new tools
        self.agent_executor = self._create_agent_executor()
    
    def _get_agent_system_message(self) -> str:
        """Override system message for the dependency analyzer agent."""
        return """You are an expert Dependency Analyzer Agent specialized in software dependency management.

Your task is to analyze codebases to map out all internal and external dependencies and identify potential issues.
You should:
- Identify all external library dependencies and their versions
- Map internal dependencies between files and modules
- Detect issues like missing dependencies, version conflicts, or security vulnerabilities
- Search for alternative libraries when appropriate
- Communicate with the Software Planner to ensure all required dependencies are accounted for

Provide clear, structured output including dependency information, issues found, and recommendations.
Be thorough in your analysis and provide specific details about each dependency.
"""
    
    def _create_dependency_tools(self) -> List[BaseTool]:
        """Create specialized tools for dependency analysis tasks."""
        
        # Add standard tools
        read_file_tool = ReadFileTool()
        web_search_tool = WebSearchTool(web_search=WebSearch())
        shell_executor_tool = ShellExecutorTool()
        
        @tool("analyze_dependencies")
        def analyze_dependencies(codebase_path: str) -> str:
            """
            Analyze dependencies in a codebase to identify external and internal dependencies.
            
            Args:
                codebase_path: Path to the codebase to analyze
                
            Returns:
                A JSON string containing the dependency analysis results
            """
            parser = PydanticOutputParser(pydantic_object=DependencyAnalysis)
            
            # Create a specialized prompt for dependency analysis
            template = """
            You are tasked with analyzing dependencies in a codebase at this path:
            
            {codebase_path}
            
            Analyze the codebase to identify:
            1. External dependencies (libraries, frameworks, etc.)
            2. Internal dependencies between files and modules
            3. Issues with dependencies (missing, conflicting versions, etc.)
            4. Recommendations for improving dependency management
            
            Use the following approach:
            - For Python projects, look for imports, requirements.txt, setup.py, pyproject.toml
            - For JavaScript/TypeScript projects, look for import/require statements, package.json
            - For other languages, look for their respective dependency management files
            - Trace internal dependencies by analyzing import statements between files
            
            {format_instructions}
            """
            
            prompt = ChatPromptTemplate.from_messages([
                SystemMessagePromptTemplate.from_template(template).format(
                    codebase_path=codebase_path,
                    format_instructions=parser.get_format_instructions()
                )
            ])
            
            # Generate the analysis using the LLM
            chain = prompt | self.llm | parser
            
            try:
                # Execute shell commands to gather dependency information
                shell_executor = ShellExecutor()
                
                # Check if it's a Python project
                python_deps_cmd = f"cd {codebase_path} && pip list --format=json"
                python_deps_result = asyncio.run(shell_executor.run_async(python_deps_cmd))
                
                # Check if it's a JavaScript project
                js_deps_cmd = f"cd {codebase_path} && npm list --json"
                js_deps_result = asyncio.run(shell_executor.run_async(js_deps_cmd))
                
                # Find all import statements in Python files
                find_imports_cmd = f'cd {codebase_path} && findstr /s /i "import from require" *.py *.js *.ts'
                imports_result = asyncio.run(shell_executor.run_async(find_imports_cmd))
                
                # Combine the information for the LLM to analyze
                context = {
                    "python_dependencies": python_deps_result.get("stdout", ""),
                    "javascript_dependencies": js_deps_result.get("stdout", ""),
                    "import_statements": imports_result.get("stdout", "")
                }
                
                # Invoke the LLM with the gathered information
                result = chain.invoke(context)
                
                # Convert the Pydantic object to a dict
                return json.dumps(result.dict())
            except Exception as e:
                logger.error(f"Error in dependency analysis: {str(e)}")
                # Return a basic analysis as fallback
                return json.dumps({
                    "status": "partial",
                    "external_dependencies": {
                        "python": [],
                        "javascript": []
                    },
                    "internal_dependencies": {},
                    "issues": [
                        {
                            "type": "analysis_error",
                            "severity": "error",
                            "description": f"Error during dependency analysis: {str(e)}",
                            "recommendation": "Try analyzing manually or with a different tool"
                        }
                    ],
                    "recommendations": [
                        "Review dependencies manually",
                        "Check for missing requirements"
                    ]
                })
        
        @tool("search_alternatives")
        def search_alternatives(dependency: str, language: str) -> str:
            """
            Search for alternative libraries to a given dependency.
            
            Args:
                dependency: The name of the dependency to find alternatives for
                language: The programming language (e.g., python, javascript)
                
            Returns:
                JSON string with alternative libraries and their descriptions
            """
            prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content=f"""
                You are a dependency research expert. Find alternative libraries to {dependency} for {language}.
                For each alternative, provide:
                1. Name of the library
                2. Brief description
                3. Key advantages compared to {dependency}
                4. Popularity metrics (stars, downloads, etc. if available)
                
                Format your response as a JSON array of objects with these fields:
                [
                    {{
                        "name": "library_name",
                        "description": "Brief description",
                        "advantages": "Key advantages",
                        "popularity": "Popularity metrics"
                    }},
                    ...
                ]
                """)
            ])
            
            # Use the web search tool to gather information
            web_search = WebSearch()
            search_query = f"alternative to {dependency} library in {language}"
            
            try:
                # Search for alternatives
                search_results = asyncio.run(web_search.search_and_fetch(search_query, num_results=3))
                
                # Extract content from search results
                content = "\n\n".join([
                    f"Title: {result.get('title', '')}\n" +
                    f"URL: {result.get('url', '')}\n" +
                    f"Content: {result.get('content', '')[:1000]}..."
                    for result in search_results
                ])
                
                # Generate alternatives using the LLM
                chain = prompt | self.llm
                result = chain.invoke({"content": content})
                
                return result.content
            except Exception as e:
                logger.error(f"Error searching for alternatives: {str(e)}")
                return json.dumps([
                    {
                        "name": "alternative_1",
                        "description": "Error fetching alternatives",
                        "advantages": "Unknown",
                        "popularity": "Unknown"
                    }
                ])
        
        @tool("communicate_with_planner")
        def communicate_with_planner(dependencies: str, plan_details: str) -> str:
            """
            Communicate with the Software Planner to ensure all required dependencies are accounted for.
            
            Args:
                dependencies: JSON string of current dependencies
                plan_details: Details of the software plan to check against
                
            Returns:
                Analysis of dependencies needed for the plan
            """
            prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content="""
                You are coordinating between dependency analysis and software planning.
                Analyze the current dependencies and the software plan to:
                1. Identify dependencies required by the plan but not currently included
                2. Identify dependencies that may be unnecessary for the plan
                3. Suggest version constraints for critical dependencies
                
                Format your response as:
                {
                    "missing_dependencies": [{"name": "lib_name", "reason": "why needed"}],
                    "unnecessary_dependencies": [{"name": "lib_name", "reason": "why not needed"}],
                    "version_constraints": [{"name": "lib_name", "constraint": "version constraint", "reason": "why this constraint"}]
                }
                """),
                HumanMessagePromptTemplate.from_template("""
                Current Dependencies:
                {dependencies}
                
                Software Plan:
                {plan_details}
                
                Provide your analysis:
                """)
            ])
            
            # Generate the analysis using the LLM
            chain = prompt | self.llm
            
            try:
                result = chain.invoke({
                    "dependencies": dependencies,
                    "plan_details": plan_details
                })
                return result.content
            except Exception as e:
                logger.error(f"Error in planner communication: {str(e)}")
                return json.dumps({
                    "missing_dependencies": [],
                    "unnecessary_dependencies": [],
                    "version_constraints": []
                })
        
        return [analyze_dependencies, search_alternatives, communicate_with_planner, read_file_tool, web_search_tool, shell_executor_tool]
    
    async def execute(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        """Execute the agent's main task - analyzing dependencies.
        
        Args:
            prompt: The input prompt describing the analysis task
            **kwargs: Additional parameters for execution
            
        Returns:
            Dictionary containing the dependency analysis results
        """
        logger.info(f"Dependency Analyzer Agent {self.name} executing with prompt: {prompt[:100]}...")
        
        try:
            # Create a structured agent with tools
            agent = create_structured_chat_agent(
                self.llm,
                self.tools,
                ChatPromptTemplate.from_messages([
                    ("system", self._get_agent_system_message()),
                    ("human", "{input}")
                ])
            )
            
            # Create the agent executor
            agent_executor = AgentExecutor(
                agent=agent,
                tools=self.tools,
                verbose=True,
                handle_parsing_errors=True,
                max_iterations=10
            )
            
            # Execute the agent
            logger.debug("Analyzing dependencies...")
            result = await agent_executor.ainvoke({"input": prompt})
            
            # If successful, try to parse the analysis from the result
            if result:
                try:
                    # Try to extract structured analysis from the response
                    raw_output = result.get("output", "")
                    
                    # Look for JSON in the output
                    json_match = re.search(r'```json\n(.*?)\n```', raw_output, re.DOTALL)
                    
                    if json_match:
                        analysis_json = json_match.group(1)
                    else:
                        # Try to find any JSON-like structure
                        json_match = re.search(r'({.*})', raw_output, re.DOTALL)
                        analysis_json = json_match.group(1) if json_match else raw_output
                    
                    # Parse the JSON
                    analysis = json.loads(analysis_json)
                    
                    # If it doesn't have the expected structure, use the tool directly
                    if not all(k in analysis for k in ["status", "external_dependencies", "internal_dependencies"]):
                        logger.info("Using dependency analysis tool directly")
                        # Get the codebase path from the prompt or use current directory
                        codebase_path = kwargs.get("codebase_path", os.getcwd())
                        analysis_result = await asyncio.to_thread(
                            self.tools[0].invoke,
                            {"codebase_path": codebase_path}
                        )
                        analysis = json.loads(analysis_result)
                    
                    # Add the parsed analysis to the result
                    self.add_to_conversation(
                        "assistant", 
                        f"Dependency analysis completed. Found {sum(len(deps) for deps in analysis['external_dependencies'].values())} external dependencies and {len(analysis['issues'])} issues."
                    )
                    
                    logger.info(f"Dependency analysis complete, found {len(analysis['issues'])} issues")
                    return {
                        "success": True,
                        "analysis": analysis,
                        "message": "Dependency analysis completed successfully"
                    }
                    
                except Exception as parse_error:
                    logger.warning(f"Error parsing dependency analysis: {str(parse_error)}")
                    # Try to use the analysis tool directly
                    try:
                        codebase_path = kwargs.get("codebase_path", os.getcwd())
                        analysis_result = await asyncio.to_thread(
                            self.tools[0].invoke,
                            {"codebase_path": codebase_path}
                        )
                        analysis = json.loads(analysis_result)
                        
                        self.add_to_conversation(
                            "assistant", 
                            f"Dependency analysis completed using fallback. Found {sum(len(deps) for deps in analysis['external_dependencies'].values())} external dependencies and {len(analysis['issues'])} issues."
                        )
                        
                        return {
                            "success": True,
                            "analysis": analysis,
                            "message": "Dependency analysis completed using fallback"
                        }
                    except Exception as tool_error:
                        logger.error(f"Analysis tool error: {str(tool_error)}")
                        # Create a basic fallback analysis
                        analysis = {
                            "status": "partial",
                            "external_dependencies": {
                                "python": [
                                    {
                                        "name": "langchain",
                                        "version": "latest",
                                        "usage_locations": ["unknown"],
                                        "issues": []
                                    }
                                ],
                                "javascript": []
                            },
                            "internal_dependencies": {},
                            "issues": [
                                {
                                    "type": "analysis_error",
                                    "severity": "error",
                                    "description": f"Error during dependency analysis: {str(parse_error)}",
                                    "recommendation": "Try analyzing manually or with a different tool"
                                }
                            ],
                            "recommendations": [
                                "Review dependencies manually",
                                "Check for missing requirements"
                            ]
                        }
                        
                        self.add_to_conversation(
                            "assistant", 
                            "Dependency analysis encountered errors. Using fallback analysis."
                        )
                        
                        return {
                            "success": True,
                            "analysis": analysis,
                            "message": "Dependency analysis fallback used due to errors"
                        }
            
            # If we get here, something went wrong with the agent execution
            logger.warning("Agent execution did not return expected result")
            return {
                "success": False,
                "error": "Agent execution failed to return valid results",
                "message": "Dependency analysis failed"
            }
            
        except Exception as e:
            logger.exception(f"Dependency analysis failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "Dependency analysis failed"
            }
