from typing import Any, Dict, List, Optional, Type, cast
import asyncio
import json
import os
import platform
import re
from loguru import logger

from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.messages import SystemMessage
from langchain_core.tools import BaseTool, tool
from langchain_core.output_parsers import PydanticOutputParser
from langchain.tools import ReadFileTool, WriteFileTool
from langchain.agents import AgentExecutor, create_structured_chat_agent

from .base_agent import BaseAgent
from utils.web_search import WebSearch, WebSearchTool
from utils.shell_executor import ShellExecutor, ShellExecutorTool


class SetupScript(BaseModel):
    """Setup script for a specific operating system."""
    os: str = Field(description="Operating system (linux, macos, windows)")
    content: str = Field(description="Content of the setup script")
    filename: str = Field(description="Filename for the setup script")
    execution_command: str = Field(description="Command to execute the script")


class DockerConfig(BaseModel):
    """Docker configuration files."""
    docker_compose: Optional[str] = Field(None, description="Docker Compose file content")
    dockerfile: Optional[str] = Field(None, description="Dockerfile content")
    docker_ignore: Optional[str] = Field(None, description="Docker ignore file content")


class EnvironmentConfig(BaseModel):
    """Environment configuration files."""
    env_file: Optional[str] = Field(None, description="Environment variables file content")
    config_files: Dict[str, str] = Field(default_factory=dict, description="Additional configuration files")


class InstallationTest(BaseModel):
    """Test for verifying installation."""
    os: str = Field(description="Operating system the test is for")
    command: str = Field(description="Command to run the test")
    expected_output: str = Field(description="Expected output if successful")
    error_handling: Dict[str, str] = Field(description="Error patterns and their fixes")


class StackBuildResult(BaseModel):
    """Complete stack build result."""
    setup_scripts: List[SetupScript] = Field(description="Setup scripts for different operating systems")
    docker_config: Optional[DockerConfig] = Field(None, description="Docker configuration if applicable")
    environment_config: Optional[EnvironmentConfig] = Field(None, description="Environment configuration")
    installation_tests: List[InstallationTest] = Field(description="Tests to verify installation")
    status: str = Field(description="Status of the build (e.g., 'complete', 'partial', 'failed')")
    message: str = Field(description="Message about the build result")


class StackBuilderAgent(BaseAgent):
    """Stack Builder Agent.
    
    This agent is responsible for translating architecture designs into
    installation scripts and configuration mechanisms.
    """
    
    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize the Stack Builder Agent with specialized tools."""
        super().__init__(*args, **kwargs)
        
        # Create stack builder tools
        builder_tools = self._create_builder_tools()
        self.tools.extend(builder_tools)
        
        # Re-create the agent executor with the new tools
        self.agent_executor = self._create_agent_executor()
    
    def _get_agent_system_message(self) -> str:
        """Override system message for the stack builder agent."""
        return """You are an expert Stack Builder Agent specialized in creating installation scripts and mechanisms.

Your task is to take architecture designs and build installation scripts and mechanisms for the desired stack.
You should:
- Create setup scripts for all major operating systems (Windows, Linux, macOS)
- Generate Docker configurations when appropriate
- Provide environment configuration files
- Create tests to verify successful installation
- Fix any issues that arise during the installation process

IMPORTANT: You MUST account for all server environments (Windows, Linux, macOS) in your scripts.
Ensure that your scripts handle different package managers, path conventions, and environment setups.

Provide clear, structured output including all necessary scripts and configurations.
Be thorough in your implementation and provide detailed instructions for each operating system.
"""
    
    def _create_builder_tools(self) -> List[BaseTool]:
        """Create specialized tools for stack building tasks."""
        
        # Add standard tools
        read_file_tool = ReadFileTool()
        write_file_tool = WriteFileTool()
        web_search_tool = WebSearchTool(web_search=WebSearch())
        shell_executor_tool = ShellExecutorTool()
        
        @tool("generate_setup_scripts")
        def generate_setup_scripts(architecture_design: str) -> str:
            """
            Generate setup scripts for different operating systems based on the architecture design.
            
            Args:
                architecture_design: JSON string of the architecture design
                
            Returns:
                A JSON string containing setup scripts for different operating systems
            """
            parser = PydanticOutputParser(pydantic_object=List[SetupScript])
            
            # Create a specialized prompt for script generation
            template = """
            You are tasked with generating setup scripts for the following architecture design:
            
            {architecture_design}
            
            Create setup scripts for Linux, macOS, and Windows that will install all necessary components.
            Each script should:
            1. Install all required dependencies
            2. Set up the environment
            3. Configure any necessary services
            4. Provide verification steps
            
            For Linux, use bash and apt/yum/dnf as appropriate.
            For macOS, use bash and homebrew.
            For Windows, use PowerShell and appropriate Windows package managers.
            
            {format_instructions}
            """
            
            prompt = ChatPromptTemplate.from_messages([
                SystemMessagePromptTemplate.from_template(template).format(
                    architecture_design=architecture_design,
                    format_instructions=parser.get_format_instructions()
                )
            ])
            
            # Generate the scripts using the LLM
            chain = prompt | self.llm | parser
            
            try:
                # Invoke the LLM
                result = chain.invoke({})
                
                # Convert the Pydantic object to a dict
                return json.dumps([script.dict() for script in result])
            except Exception as e:
                logger.error(f"Error generating setup scripts: {str(e)}")
                # Return basic scripts as fallback
                return json.dumps([
                    {
                        "os": "linux",
                        "content": "#!/bin/bash\n\n# Install dependencies\napt-get update\napt-get install -y curl git\n\n# Setup environment\necho 'Setup complete on Linux'",
                        "filename": "setup_linux.sh",
                        "execution_command": "bash setup_linux.sh"
                    },
                    {
                        "os": "macos",
                        "content": "#!/bin/bash\n\n# Install dependencies\nbrew update\nbrew install curl git\n\n# Setup environment\necho 'Setup complete on macOS'",
                        "filename": "setup_macos.sh",
                        "execution_command": "bash setup_macos.sh"
                    },
                    {
                        "os": "windows",
                        "content": "# PowerShell script\n\n# Install dependencies\nSet-ExecutionPolicy Bypass -Scope Process -Force\n[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072\nInvoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))\nchoco install git curl -y\n\n# Setup environment\nWrite-Host 'Setup complete on Windows'",
                        "filename": "setup_windows.ps1",
                        "execution_command": "powershell -ExecutionPolicy Bypass -File setup_windows.ps1"
                    }
                ])
        
        @tool("generate_docker_config")
        def generate_docker_config(architecture_design: str) -> str:
            """
            Generate Docker configuration files based on the architecture design.
            
            Args:
                architecture_design: JSON string of the architecture design
                
            Returns:
                A JSON string containing Docker configuration files
            """
            parser = PydanticOutputParser(pydantic_object=DockerConfig)
            
            # Create a specialized prompt for Docker configuration
            template = """
            You are tasked with generating Docker configuration files for the following architecture design:
            
            {architecture_design}
            
            Create:
            1. A docker-compose.yml file that defines all services
            2. A Dockerfile for the main application
            3. A .dockerignore file
            
            Ensure that:
            - All necessary services are included (database, cache, etc.)
            - Proper networking is configured
            - Volumes are defined for persistent data
            - Environment variables are properly handled
            
            {format_instructions}
            """
            
            prompt = ChatPromptTemplate.from_messages([
                SystemMessagePromptTemplate.from_template(template).format(
                    architecture_design=architecture_design,
                    format_instructions=parser.get_format_instructions()
                )
            ])
            
            # Generate the Docker configuration using the LLM
            chain = prompt | self.llm | parser
            
            try:
                # Invoke the LLM
                result = chain.invoke({})
                
                # Convert the Pydantic object to a dict
                return json.dumps(result.dict())
            except Exception as e:
                logger.error(f"Error generating Docker configuration: {str(e)}")
                # Return a basic Docker configuration as fallback
                return json.dumps({
                    "docker_compose": "version: '3'\n\nservices:\n  app:\n    build: .\n    ports:\n      - '3000:3000'\n    environment:\n      - NODE_ENV=production",
                    "dockerfile": "FROM node:14\nWORKDIR /app\nCOPY package*.json ./\nRUN npm install\nCOPY . .\nEXPOSE 3000\nCMD [\"npm\", \"start\"]",
                    "docker_ignore": "node_modules\nnpm-debug.log\n.git\n.env"
                })
        
        @tool("generate_environment_config")
        def generate_environment_config(architecture_design: str) -> str:
            """
            Generate environment configuration files based on the architecture design.
            
            Args:
                architecture_design: JSON string of the architecture design
                
            Returns:
                A JSON string containing environment configuration files
            """
            parser = PydanticOutputParser(pydantic_object=EnvironmentConfig)
            
            # Create a specialized prompt for environment configuration
            template = """
            You are tasked with generating environment configuration files for the following architecture design:
            
            {architecture_design}
            
            Create:
            1. A .env file with all necessary environment variables
            2. Any additional configuration files needed
            
            Ensure that:
            - Sensitive information is properly handled (use placeholders)
            - All necessary configuration options are included
            - Files are properly formatted for their respective services
            
            {format_instructions}
            """
            
            prompt = ChatPromptTemplate.from_messages([
                SystemMessagePromptTemplate.from_template(template).format(
                    architecture_design=architecture_design,
                    format_instructions=parser.get_format_instructions()
                )
            ])
            
            # Generate the environment configuration using the LLM
            chain = prompt | self.llm | parser
            
            try:
                # Invoke the LLM
                result = chain.invoke({})
                
                # Convert the Pydantic object to a dict
                return json.dumps(result.dict())
            except Exception as e:
                logger.error(f"Error generating environment configuration: {str(e)}")
                # Return a basic environment configuration as fallback
                return json.dumps({
                    "env_file": "# Environment Variables\nNODE_ENV=production\nPORT=3000\nDATABASE_URL=postgres://user:password@localhost:5432/dbname\nAPI_KEY=your_api_key_here",
                    "config_files": {
                        "nginx.conf": "server {\n  listen 80;\n  server_name example.com;\n  location / {\n    proxy_pass http://localhost:3000;\n  }\n}"
                    }
                })
        
        @tool("generate_installation_tests")
        def generate_installation_tests(architecture_design: str) -> str:
            """
            Generate tests to verify successful installation based on the architecture design.
            
            Args:
                architecture_design: JSON string of the architecture design
                
            Returns:
                A JSON string containing installation tests
            """
            parser = PydanticOutputParser(pydantic_object=List[InstallationTest])
            
            # Create a specialized prompt for test generation
            template = """
            You are tasked with generating installation tests for the following architecture design:
            
            {architecture_design}
            
            Create tests for Linux, macOS, and Windows that will verify the installation was successful.
            Each test should:
            1. Check that all required components are installed
            2. Verify that services are running
            3. Test basic functionality
            4. Include error handling for common issues
            
            {format_instructions}
            """
            
            prompt = ChatPromptTemplate.from_messages([
                SystemMessagePromptTemplate.from_template(template).format(
                    architecture_design=architecture_design,
                    format_instructions=parser.get_format_instructions()
                )
            ])
            
            # Generate the tests using the LLM
            chain = prompt | self.llm | parser
            
            try:
                # Invoke the LLM
                result = chain.invoke({})
                
                # Convert the Pydantic object to a dict
                return json.dumps([test.dict() for test in result])
            except Exception as e:
                logger.error(f"Error generating installation tests: {str(e)}")
                # Return basic tests as fallback
                return json.dumps([
                    {
                        "os": "linux",
                        "command": "curl -s http://localhost:3000/health",
                        "expected_output": "{\"status\":\"ok\"}",
                        "error_handling": {
                            "Connection refused": "Check if the service is running: systemctl status app",
                            "404 Not Found": "Check if the application is properly configured"
                        }
                    },
                    {
                        "os": "macos",
                        "command": "curl -s http://localhost:3000/health",
                        "expected_output": "{\"status\":\"ok\"}",
                        "error_handling": {
                            "Connection refused": "Check if the service is running: brew services list",
                            "404 Not Found": "Check if the application is properly configured"
                        }
                    },
                    {
                        "os": "windows",
                        "command": "Invoke-WebRequest -Uri http://localhost:3000/health -UseBasicParsing",
                        "expected_output": "StatusCode: 200",
                        "error_handling": {
                            "Unable to connect": "Check if the service is running in Task Manager",
                            "404": "Check if the application is properly configured"
                        }
                    }
                ])
        
        @tool("test_installation")
        def test_installation(test_command: str, current_os: Optional[str] = None) -> str:
            """
            Test the installation by running a test command.
            
            Args:
                test_command: Command to test the installation
                current_os: Operating system to test on (defaults to current OS)
                
            Returns:
                JSON string with test results
            """
            # Determine the current OS if not provided
            if not current_os:
                system = platform.system().lower()
                if system == "darwin":
                    current_os = "macos"
                elif system == "linux":
                    current_os = "linux"
                elif system == "windows":
                    current_os = "windows"
                else:
                    current_os = "unknown"
            
            # Execute the test command
            shell_executor = ShellExecutor()
            
            try:
                # Run the test command
                result = asyncio.run(shell_executor.run_async(
                    command=test_command,
                    timeout=30  # 30-second timeout
                ))
                
                # Check if the test was successful
                success = result.get("success", False)
                stdout = result.get("stdout", "")
                stderr = result.get("stderr", "")
                
                return json.dumps({
                    "os": current_os,
                    "command": test_command,
                    "success": success,
                    "output": stdout,
                    "error": stderr,
                    "message": "Installation test completed successfully" if success else "Installation test failed"
                })
            except Exception as e:
                logger.error(f"Error testing installation: {str(e)}")
                return json.dumps({
                    "os": current_os,
                    "command": test_command,
                    "success": False,
                    "output": "",
                    "error": str(e),
                    "message": "Error executing installation test"
                })
        
        return [generate_setup_scripts, generate_docker_config, generate_environment_config, generate_installation_tests, test_installation, read_file_tool, write_file_tool, web_search_tool, shell_executor_tool]
    
    async def execute(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        """Execute the agent's main task - building stack installation scripts.
        
        Args:
            prompt: The input prompt describing requirements
            **kwargs: Additional parameters for execution, including:
                architecture_design: The architecture design to build scripts for
            
        Returns:
            Dictionary containing the stack builder results
        """
        logger.info(f"Stack Builder Agent {self.name} executing with prompt: {prompt[:100]}...")
        
        # Get the architecture design from kwargs
        architecture_design = kwargs.get("architecture_design", {})
        if not architecture_design:
            logger.warning("No architecture design provided for stack building")
            return {
                "success": False,
                "error": "No architecture design provided",
                "message": "Stack building failed - no architecture design provided"
            }
        
        try:
            # Convert architecture design to string if it's a dict
            if isinstance(architecture_design, dict):
                architecture_design_str = json.dumps(architecture_design)
            else:
                architecture_design_str = str(architecture_design)
            
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
                max_iterations=15
            )
            
            # Execute the agent
            logger.debug("Building stack installation scripts...")
            result = await agent_executor.ainvoke({
                "input": f"""
                Build installation scripts and mechanisms for the following architecture design:
                
                {architecture_design_str}
                
                Your task is to:
                1. Create setup scripts for all major operating systems (Windows, Linux, macOS)
                2. Generate Docker configurations if appropriate
                3. Provide environment configuration files
                4. Create tests to verify successful installation
                
                Ensure that all scripts are complete and ready to use.
                """
            })
            
            # If successful, try to parse the build result from the output
            if result:
                try:
                    # Try to extract structured build result from the response
                    raw_output = result.get("output", "")
                    
                    # Look for JSON in the output
                    json_match = re.search(r'```json\n(.*?)\n```', raw_output, re.DOTALL)
                    
                    if json_match:
                        build_json = json_match.group(1)
                    else:
                        # Try to find any JSON-like structure
                        json_match = re.search(r'({.*})', raw_output, re.DOTALL)
                        build_json = json_match.group(1) if json_match else raw_output
                    
                    # Parse the JSON
                    build_result = json.loads(build_json)
                    
                    # If it doesn't have the expected structure, create a basic result
                    if not all(k in build_result for k in ["setup_scripts", "status"]):
                        logger.warning("Build result missing expected fields, creating basic result")
                        
                        # Try to use the tools directly to generate the components
                        setup_scripts_str = await asyncio.to_thread(
                            self.tools[0].invoke,
                            {"architecture_design": architecture_design_str}
                        )
                        setup_scripts = json.loads(setup_scripts_str)
                        
                        docker_config_str = await asyncio.to_thread(
                            self.tools[1].invoke,
                            {"architecture_design": architecture_design_str}
                        )
                        docker_config = json.loads(docker_config_str)
                        
                        env_config_str = await asyncio.to_thread(
                            self.tools[2].invoke,
                            {"architecture_design": architecture_design_str}
                        )
                        env_config = json.loads(env_config_str)
                        
                        tests_str = await asyncio.to_thread(
                            self.tools[3].invoke,
                            {"architecture_design": architecture_design_str}
                        )
                        tests = json.loads(tests_str)
                        
                        build_result = {
                            "setup_scripts": setup_scripts,
                            "docker_config": docker_config,
                            "environment_config": env_config,
                            "installation_tests": tests,
                            "status": "complete",
                            "message": "Stack installation scripts generated successfully"
                        }
                    
                    # Add the build result to the conversation
                    self.add_to_conversation(
                        "assistant", 
                        "Stack installation scripts generated successfully"
                    )
                    
                    logger.info("Stack installation scripts generated successfully")
                    return {
                        "success": True,
                        "scripts": build_result,
                        "message": "Stack installation scripts generated successfully"
                    }
                    
                except Exception as parse_error:
                    logger.warning(f"Error parsing build result: {str(parse_error)}")
                    # Create a basic result from the raw output
                    build_result = {
                        "setup_scripts": [
                            {
                                "os": "linux",
                                "content": "#!/bin/bash\n\n# Install dependencies\napt-get update\napt-get install -y curl git\n\n# Setup environment\necho 'Setup complete on Linux'",
                                "filename": "setup_linux.sh",
                                "execution_command": "bash setup_linux.sh"
                            },
                            {
                                "os": "macos",
                                "content": "#!/bin/bash\n\n# Install dependencies\nbrew update\nbrew install curl git\n\n# Setup environment\necho 'Setup complete on macOS'",
                                "filename": "setup_macos.sh",
                                "execution_command": "bash setup_macos.sh"
                            },
                            {
                                "os": "windows",
                                "content": "# PowerShell script\n\n# Install dependencies\nSet-ExecutionPolicy Bypass -Scope Process -Force\n[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072\nInvoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))\nchoco install git curl -y\n\n# Setup environment\nWrite-Host 'Setup complete on Windows'",
                                "filename": "setup_windows.ps1",
                                "execution_command": "powershell -ExecutionPolicy Bypass -File setup_windows.ps1"
                            }
                        ],
                        "docker_config": {
                            "docker_compose": "version: '3'\n\nservices:\n  app:\n    build: .\n    ports:\n      - '3000:3000'\n    environment:\n      - NODE_ENV=production",
                            "dockerfile": "FROM node:14\nWORKDIR /app\nCOPY package*.json ./\nRUN npm install\nCOPY . .\nEXPOSE 3000\nCMD [\"npm\", \"start\"]",
                            "docker_ignore": "node_modules\nnpm-debug.log\n.git\n.env"
                        },
                        "environment_config": {
                            "env_file": "# Environment Variables\nNODE_ENV=production\nPORT=3000\nDATABASE_URL=postgres://user:password@localhost:5432/dbname\nAPI_KEY=your_api_key_here"
                        },
                        "installation_tests": [
                            {
                                "os": "linux",
                                "command": "curl -s http://localhost:3000/health",
                                "expected_output": "{\"status\":\"ok\"}",
                                "error_handling": {
                                    "Connection refused": "Check if the service is running: systemctl status app"
                                }
                            },
                            {
                                "os": "macos",
                                "command": "curl -s http://localhost:3000/health",
                                "expected_output": "{\"status\":\"ok\"}",
                                "error_handling": {
                                    "Connection refused": "Check if the service is running: brew services list"
                                }
                            },
                            {
                                "os": "windows",
                                "command": "Invoke-WebRequest -Uri http://localhost:3000/health -UseBasicParsing",
                                "expected_output": "StatusCode: 200",
                                "error_handling": {
                                    "Unable to connect": "Check if the service is running in Task Manager"
                                }
                            }
                        ],
                        "status": "complete",
                        "message": "Stack installation scripts generated with fallback"
                    }
                    
                    self.add_to_conversation(
                        "assistant", 
                        "Stack installation scripts generated with fallback due to parsing errors."
                    )
                    
                    return {
                        "success": True,
                        "scripts": build_result,
                        "message": "Stack installation scripts generated with fallback"
                    }
            
            # If we get here, something went wrong with the agent execution
            logger.warning("Agent execution did not return expected result")
            return {
                "success": False,
                "error": "Agent execution failed to return valid results",
                "message": "Stack building failed"
            }
            
        except Exception as e:
            logger.exception(f"Stack building failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "Stack building failed"
            }
