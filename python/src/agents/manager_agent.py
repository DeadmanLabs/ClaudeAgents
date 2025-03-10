from typing import Any, Dict, List, Optional, Union, Type, cast
import asyncio
import json
import sys
from loguru import logger

from langchain_core.tools import BaseTool, tool
from langchain.tools import Tool
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langchain.agents import AgentExecutor, create_structured_chat_agent
from langchain_core.language_models import BaseLanguageModel
from langchain_core.memory import BaseMemory
from langchain.output_parsers import PydanticOutputParser
try:
    # Try pydantic v2 first
    from pydantic import BaseModel, Field
except ImportError:
    # Fall back to pydantic v1 or langchain compatibility layer
    try:
        from pydantic.v1 import BaseModel, Field
    except ImportError:
        from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.runnables import RunnablePassthrough, RunnableConfig

from .base_agent import BaseAgent
from .architecture_designer_agent import ArchitectureDesignerAgent
from .stack_builder_agent import StackBuilderAgent
from .library_researcher_agent import LibraryResearcherAgent
from .software_planner_agent import SoftwarePlannerAgent
from .software_programmer_agent import SoftwareProgrammerAgent
from .exception_debugger_agent import ExceptionDebuggerAgent
from .dependency_analyzer_agent import DependencyAnalyzerAgent


class RequirementsOutput(BaseModel):
    """Structured output for requirements analysis."""
    prompt: str = Field(description="The original prompt")
    extracted_requirements: List[str] = Field(description="List of extracted requirements")
    primary_language: Optional[str] = Field(description="Primary programming language (if specified)", default=None)
    technologies: List[str] = Field(description="List of technologies mentioned in requirements", default_factory=list)
    constraints: List[str] = Field(description="List of constraints or limitations", default_factory=list)


class ManagerAgent(BaseAgent):
    """Final Manager Agent that coordinates all specialized agents.
    
    This agent orchestrates the collaborative workflow between specialized agents,
    delegating tasks and integrating results to produce a complete software solution.
    """
    
    def __init__(
        self, 
        name: str, 
        memory_manager: Any = None, 
        config: Optional[Dict[str, Any]] = None,
        llm: Optional[BaseLanguageModel] = None,
        tools: Optional[List[BaseTool]] = None,
        memory: Optional[BaseMemory] = None,
        verbose: bool = False,
        dashboard_mode: bool = False
    ):
        """Initialize the Manager Agent with LangChain components.
        
        Args:
            name: A unique name for this agent instance
            memory_manager: The memory manager for storing context
            config: Configuration parameters for the agent
            llm: The language model to use for this agent
            tools: List of tools the agent can use
            memory: LangChain memory instance for conversation history
            verbose: Whether to output verbose logging
            dashboard_mode: Whether to run in dashboard mode with UI updates
        """
        # Create manager tools first
        manager_tools = self._create_manager_tools()
        
        # Initialize with all tools
        all_tools = (tools or []) + manager_tools
        
        super().__init__(name, memory_manager, config, llm, all_tools, memory, verbose)
        self.specialized_agents = {}
        self.dashboard_mode = dashboard_mode or ("--dashboard-mode" in sys.argv)
    
    def _get_agent_system_message(self) -> str:
        """Override system message for the manager agent."""
        return """You are a Manager Agent, responsible for coordinating a team of specialized AI agents to deliver complete software solutions.
        
Your primary responsibilities are:
1. Analyze user requirements to determine the needs and constraints
2. Delegate specialized tasks to the appropriate sub-agents
3. Coordinate the workflow between these agents
4. Integrate results into a cohesive solution
5. Ensure all components work together properly
6. Produce comprehensive documentation and summaries

You have access to the following specialized agents:
- Architecture Designer: Creates overall system architecture
- Stack Builder: Defines technology stacks and configurations
- Library Researcher: Identifies optimal libraries and frameworks
- Software Planner: Creates detailed development plans and roadmaps
- Software Programmer: Implements actual code
- Exception Debugger: Detects and fixes potential issues
- Dependency Analyzer: Manages dependencies between components

Work methodically through each step of the software development process, delegating to specialized agents as needed.
"""
    
    def _create_manager_tools(self) -> List[BaseTool]:
        """Create specialized tools for the manager agent."""
        
        @tool("analyze_requirements")
        def analyze_requirements(prompt: str) -> str:
            """
            Analyze a user prompt to extract key requirements, constraints, and preferences.
            
            Args:
                prompt: The user input prompt to analyze
                
            Returns:
                JSON string containing structured requirements analysis
            """
            parser = PydanticOutputParser(pydantic_object=RequirementsOutput)
            
            template = """
            Analyze the following user request to extract software requirements:
            
            {prompt}
            
            Extract the key requirements, desired technologies, constraints, and other relevant details.
            
            {format_instructions}
            """
            
            prompt_template = ChatPromptTemplate.from_messages([
                SystemMessagePromptTemplate.from_template(template).format(
                    prompt=prompt,
                    format_instructions=parser.get_format_instructions()
                )
            ])
            
            # Generate the requirements using the LLM with structured output
            chain = prompt_template | self.llm | parser
            
            try:
                result = chain.invoke({})
                return json.dumps(result.dict())
            except Exception as e:
                logger.error(f"Error in requirements analysis: {str(e)}")
                # Return a basic requirements structure as fallback
                return json.dumps({
                    "prompt": prompt,
                    "extracted_requirements": ["Software development", "Multi-agent system"],
                    "primary_language": None,
                    "technologies": [],
                    "constraints": []
                })
        
        @tool("process_agent_result")
        def process_agent_result(agent_result: str, agent_type: str) -> str:
            """
            Process and validate the result from a specialized agent.
            
            Args:
                agent_result: The JSON string result from an agent
                agent_type: The type of agent that produced the result
                
            Returns:
                Processed and validated result as JSON string
            """
            prompt_template = ChatPromptTemplate.from_messages([
                SystemMessage(content=f"""
                You are analyzing the output from a {agent_type} agent.
                Verify that the result is complete, well-structured, and meets expectations.
                
                Extract the key information and return a processed version with any issues noted.
                """),
                HumanMessagePromptTemplate.from_template("""
                Agent result:
                {agent_result}
                
                Process this result and provide a structured analysis in JSON format.
                """)
            ])
            
            chain = prompt_template | self.llm
            
            try:
                result = chain.invoke({
                    "agent_result": agent_result
                })
                return result.content
            except Exception as e:
                logger.error(f"Error processing agent result: {str(e)}")
                return json.dumps({
                    "status": "error",
                    "message": f"Failed to process {agent_type} result: {str(e)}",
                    "original_data": agent_result
                })
        
        @tool("create_final_summary")
        def create_final_summary(
            architecture: str,
            libraries: str,
            software_plan: str,
            code_result: str,
            debug_result: str,
            dependency_analysis: str
        ) -> str:
            """
            Create a comprehensive summary of the complete solution.
            
            Args:
                architecture: The architecture design JSON
                libraries: The library research JSON
                software_plan: The software plan JSON
                code_result: The code generation result JSON
                debug_result: The debugging result JSON
                dependency_analysis: The dependency analysis JSON
                
            Returns:
                A comprehensive solution summary as JSON string
            """
            prompt_template = ChatPromptTemplate.from_messages([
                SystemMessage(content="""
                Create a comprehensive summary of the entire software solution based on the provided components.
                
                The summary should integrate all aspects of the project, highlight key decisions, and explain how
                components work together. Structure the response as a JSON object with the following keys:
                - summary: A detailed executive summary of the solution
                - architecture_overview: Key architectural decisions and patterns
                - technology_stack: Summary of technologies, libraries and frameworks
                - implementation_details: How the code implements the requirements
                - testing_validation: Results of debugging and validation
                - next_steps: Recommended future improvements or considerations
                """),
                HumanMessagePromptTemplate.from_template("""
                Architecture Design:
                {architecture}
                
                Library Research:
                {libraries}
                
                Software Plan:
                {software_plan}
                
                Code Result:
                {code_result}
                
                Debug Result:
                {debug_result}
                
                Dependency Analysis:
                {dependency_analysis}
                
                Create a comprehensive summary of this solution:
                """)
            ])
            
            chain = prompt_template | self.llm
            
            try:
                result = chain.invoke({
                    "architecture": architecture,
                    "libraries": libraries,
                    "software_plan": software_plan,
                    "code_result": code_result,
                    "debug_result": debug_result,
                    "dependency_analysis": dependency_analysis
                })
                
                # Extract JSON from the result if possible
                import re
                json_match = re.search(r'```json\n([\s\S]*?)\n```', result.content)
                if json_match:
                    return json_match.group(1)
                    
                # Try to find JSON-like structure
                json_match = re.search(r'({[\s\S]*})', result.content)
                if json_match:
                    return json_match.group(1)
                    
                return result.content
                
            except Exception as e:
                logger.error(f"Error creating final summary: {str(e)}")
                return json.dumps({
                    "summary": "Multi-agent software development process completed with errors in summary generation.",
                    "architecture_overview": "See architecture details in separate section.",
                    "technology_stack": "See libraries section for details.",
                    "implementation_details": "Implementation completed. See code result for details.",
                    "testing_validation": "Testing completed. See debug result for details.",
                    "next_steps": "Review the solution components individually."
                })
        
        return [analyze_requirements, process_agent_result, create_final_summary]
        
    async def execute(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        """Execute the manager agent's task, orchestrating all specialized agents.
        
        Args:
            prompt: The user input prompt describing the software solution needed
            **kwargs: Additional parameters for execution
            
        Returns:
            Dictionary containing the results of the execution
        """
        logger.info(f"Manager Agent {self.name} starting execution")
        print(f"📋 Received prompt: {prompt[:100]}...")
        print("🔄 Starting multi-agent collaboration process...")
        
        try:
            # Save the original prompt to memory
            self.save_to_memory("original_prompt", prompt)
            self.add_to_conversation("user", prompt)
            
            # Step 1: Analyze the prompt to identify requirements
            logger.info("Analyzing prompt to identify requirements")
            print("🔍 Analyzing requirements...")
            requirements = await self._analyze_requirements(prompt)
            self.save_to_memory("requirements", requirements)
            
            # Step 2: Design the architecture
            logger.info("Delegating architecture design task")
            print("🏗️ Designing architecture...")
            architecture = await self._design_architecture(requirements)
            self.save_to_memory("architecture", architecture)
            
            # Step 3: Research necessary libraries
            logger.info("Researching necessary libraries")
            print("📚 Researching libraries...")
            libraries = await self._research_libraries(requirements, architecture)
            self.save_to_memory("libraries", libraries)
            
            # Step 4: Plan the software structure
            logger.info("Planning software structure")
            print("📝 Planning software structure...")
            software_plan = await self._plan_software(requirements, architecture, libraries)
            self.save_to_memory("software_plan", software_plan)
            
            # Step 5: Generate the code
            logger.info("Generating code according to plan")
            print("💻 Generating code...")
            code_result = await self._generate_code(software_plan)
            self.save_to_memory("code_result", code_result)
            
            # Step 6: Debug and handle exceptions
            logger.info("Debugging code and handling exceptions")
            print("🔧 Debugging code...")
            debug_result = await self._debug_code(code_result)
            self.save_to_memory("debug_result", debug_result)
            
            # Step 7: Analyze dependencies for the final solution
            logger.info("Analyzing dependencies for final solution")
            print("🔄 Analyzing dependencies...")
            dependency_analysis = await self._analyze_dependencies()
            self.save_to_memory("dependency_analysis", dependency_analysis)
            
            # Step 8: Produce final summary and integration
            logger.info("Creating final integration and summary")
            print("✅ Finalizing solution...")
            final_result = await self._create_final_summary()
            
            print("\n✨ Multi-agent process completed successfully!")
            print(f"📋 Final solution summary: {final_result['summary'][:100]}...")
            
            return {
                "success": True,
                "result": final_result,
                "message": "Multi-agent process completed successfully"
            }
            
        except Exception as e:
            logger.exception(f"Manager Agent execution failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "Multi-agent process failed"
            }
    
    async def _analyze_requirements(self, prompt: str) -> Dict[str, Any]:
        """Analyze the prompt to extract key requirements using LangChain tools.
        
        Args:
            prompt: The user input prompt
            
        Returns:
            Dictionary of extracted requirements
        """
        try:
            # Find the analyze_requirements tool
            analyze_tool = next((t for t in self.tools if t.name == "analyze_requirements"), None)
            
            if not analyze_tool:
                logger.warning("Analyze requirements tool not found, using basic analysis")
                # Fallback to basic analysis
                return {
                    "prompt": prompt,
                    "extracted_requirements": [
                        "Implement multi-agent system",
                        "Support Python and JavaScript",
                        "Handle real-time output",
                        "Coordinate multiple agents"
                    ]
                }
            
            # Use the tool to analyze requirements
            result = await asyncio.to_thread(
                analyze_tool.invoke,
                {"prompt": prompt}
            )
            
            # Parse the JSON result
            return json.loads(result)
            
        except Exception as e:
            logger.error(f"Error analyzing requirements: {str(e)}")
            # Return a basic analysis as fallback
            return {
                "prompt": prompt,
                "extracted_requirements": [
                    "Implement multi-agent system",
                    "Support Python and JavaScript"
                ],
                "primary_language": None,
                "technologies": [],
                "constraints": []
            }
    
    async def _design_architecture(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Delegate architecture design to the ArchitectureDesignerAgent using LangChain.
        
        Args:
            requirements: The extracted requirements
            
        Returns:
            Architecture design result
        """
        designer = self._get_or_create_agent("architecture_designer", ArchitectureDesignerAgent)
        
        # Create a detailed prompt for the architecture designer
        req_list = ", ".join(requirements.get("extracted_requirements", []))
        tech_list = ", ".join(requirements.get("technologies", []))
        constraints = ", ".join(requirements.get("constraints", []))
        
        arch_prompt = (
            f"Design an architecture for the following requirements: {req_list}. "
            f"Technologies mentioned: {tech_list}. "
            f"Constraints to consider: {constraints}. "
            f"Original request: {requirements.get('prompt', '')[:300]}"
        )
        
        # Convert the requirements dictionary to a string for the design_architecture tool
        requirements_str = json.dumps(requirements)
        
        result = await designer.execute(requirements_str)
        
        if not result.get("success", False):
            logger.error(f"Architecture design failed: {result.get('error', 'Unknown error')}")
            raise Exception(f"Architecture design failed: {result.get('error', 'Unknown error')}")
            
        return result.get("design", {})
    
    async def _research_libraries(self, requirements: Dict[str, Any], 
                                 architecture: Dict[str, Any]) -> Dict[str, Any]:
        """Research necessary libraries using the LibraryResearcherAgent with LangChain.
        
        Args:
            requirements: The extracted requirements
            architecture: The architecture design
            
        Returns:
            Library research result
        """
        researcher = self._get_or_create_agent("library_researcher", LibraryResearcherAgent)
        
        # Create a prompt for the library researcher
        req_list = ", ".join(requirements.get("extracted_requirements", []))
        primary_lang = requirements.get("primary_language", "No specific language")
        
        lib_prompt = (
            f"Research libraries for the following architecture: "
            f"{architecture.get('summary', 'Not specified')}. "
            f"Backend: {architecture.get('backend', 'Not specified')}. "
            f"Frontend: {architecture.get('frontend', 'Not specified')}. "
            f"Requirements: {req_list}. "
            f"Primary language: {primary_lang}."
        )
        
        result = await researcher.execute(lib_prompt)
        
        if not result.get("success", False):
            logger.error(f"Library research failed: {result.get('error', 'Unknown error')}")
            raise Exception(f"Library research failed: {result.get('error', 'Unknown error')}")
            
        # Process the result using our tool if available
        process_tool = next((t for t in self.tools if t.name == "process_agent_result"), None)
        
        if process_tool:
            try:
                processed_result = await asyncio.to_thread(
                    process_tool.invoke,
                    {
                        "agent_result": json.dumps(result.get("libraries", {})),
                        "agent_type": "Library Researcher"
                    }
                )
                # Try to parse the processed result
                libraries = json.loads(processed_result)
                return libraries
            except Exception as e:
                logger.warning(f"Error processing library result: {str(e)}")
                
        return result.get("libraries", {})
    
    async def _plan_software(self, requirements: Dict[str, Any], 
                           architecture: Dict[str, Any],
                           libraries: Dict[str, Any]) -> Dict[str, Any]:
        """Plan the software structure using the SoftwarePlannerAgent with LangChain.
        
        Args:
            requirements: The extracted requirements
            architecture: The architecture design
            libraries: The researched libraries
            
        Returns:
            Software plan result
        """
        planner = self._get_or_create_agent("software_planner", SoftwarePlannerAgent)
        
        # Create a prompt for the software planner
        req_list = ", ".join(requirements.get("extracted_requirements", []))
        
        # Extract libraries if they're in a nested format
        if isinstance(libraries, dict) and "selected_libraries" in libraries:
            lib_list = ", ".join(libraries.get("selected_libraries", []))
        elif isinstance(libraries, dict) and "libraries" in libraries and isinstance(libraries["libraries"], list):
            lib_list = ", ".join(lib["name"] for lib in libraries["libraries"] if "name" in lib)
        else:
            lib_list = "No specific libraries"
        
        plan_prompt = (
            f"Create a software development plan for: {req_list}. "
            f"Architecture: {architecture.get('summary', 'Not specified')}. "
            f"Components: {', '.join([comp.get('name', 'Unknown') for comp in architecture.get('components', [])])}. "
            f"Using libraries: {lib_list}. "
            f"Original request: {requirements.get('prompt', '')[:300]}"
        )
        
        result = await planner.execute(plan_prompt)
        
        if not result.get("success", False):
            logger.error(f"Software planning failed: {result.get('error', 'Unknown error')}")
            raise Exception(f"Software planning failed: {result.get('error', 'Unknown error')}")
            
        # Store the plan for use by other agents
        plan = result.get("plan", {})
        self.save_to_memory("software_plan_detail", plan)
            
        return plan
    
    async def _generate_code(self, software_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Generate code using the SoftwareProgrammerAgent with LangChain.
        
        Args:
            software_plan: The software plan
            
        Returns:
            Code generation result
        """
        programmer = self._get_or_create_agent("software_programmer", SoftwareProgrammerAgent)
        
        # Create a prompt for the code generator
        files_to_create = software_plan.get("files", [])
        if isinstance(files_to_create, list):
            files_str = ", ".join(files_to_create)
        elif isinstance(files_to_create, dict):
            files_str = ", ".join(files_to_create.keys())
        else:
            files_str = "as needed based on the plan"
        
        code_prompt = (
            f"Implement the following software plan: "
            f"{software_plan.get('summary', 'Not specified')}. "
            f"Files to create: {files_str}. "
            f"Tasks: {', '.join(software_plan.get('tasks', []))}"
        )
        
        # Pass the software plan to the programmer agent to ensure it follows the structure
        result = await programmer.execute(code_prompt, software_plan=software_plan)
        
        if not result.get("success", False):
            logger.error(f"Code generation failed: {result.get('error', 'Unknown error')}")
            raise Exception(f"Code generation failed: {result.get('error', 'Unknown error')}")
            
        return result.get("code", {})
    
    async def _debug_code(self, code_result: Dict[str, Any]) -> Dict[str, Any]:
        """Debug code using the ExceptionDebuggerAgent with LangChain.
        
        Args:
            code_result: The generated code
            
        Returns:
            Debugging result
        """
        debugger = self._get_or_create_agent("exception_debugger", ExceptionDebuggerAgent)
        
        # Create a prompt for the debugger with code details
        files = code_result.get("files", {})
        if isinstance(files, dict):
            file_list = "\n".join([f"- {filename}" for filename in files.keys()])
        else:
            file_list = "Generated code files"
        
        debug_prompt = (
            f"Debug and validate the following code implementation:\n"
            f"Files generated:\n{file_list}\n"
            f"Check for potential exceptions, bugs, and inconsistencies."
        )
        
        result = await debugger.execute(debug_prompt, code=code_result)
        
        if not result.get("success", False):
            logger.error(f"Debugging failed: {result.get('error', 'Unknown error')}")
            raise Exception(f"Debugging failed: {result.get('error', 'Unknown error')}")
            
        return result.get("debug_result", {})
    
    async def _analyze_dependencies(self) -> Dict[str, Any]:
        """Analyze dependencies using the DependencyAnalyzerAgent with LangChain.
        
        Returns:
            Dependency analysis result
        """
        analyzer = self._get_or_create_agent("dependency_analyzer", DependencyAnalyzerAgent)
        
        # Gather all the context for dependency analysis
        architecture = self.retrieve_from_memory("architecture") or {}
        libraries = self.retrieve_from_memory("libraries") or {}
        code_result = self.retrieve_from_memory("code_result") or {}
        
        # Create a prompt for the dependency analyzer
        analyze_prompt = (
            f"Analyze dependencies for a project with: "
            f"Architecture: {architecture.get('summary', 'Not specified')}. "
            f"Components: {', '.join([comp.get('name', 'Unknown') for comp in architecture.get('components', [])])}. "
            f"Check version compatibility and dependency conflicts."
        )
        
        result = await analyzer.execute(analyze_prompt)
        
        if not result.get("success", False):
            logger.error(f"Dependency analysis failed: {result.get('error', 'Unknown error')}")
            raise Exception(f"Dependency analysis failed: {result.get('error', 'Unknown error')}")
            
        return result.get("analysis", {})
    
    async def _create_final_summary(self) -> Dict[str, Any]:
        """Create a final summary of the complete solution using LangChain.
        
        Returns:
            Final solution summary
        """
        # Retrieve all stored data from memory
        architecture = self.retrieve_from_memory("architecture") or {}
        libraries = self.retrieve_from_memory("libraries") or {}
        software_plan = self.retrieve_from_memory("software_plan") or {}
        code_result = self.retrieve_from_memory("code_result") or {}
        debug_result = self.retrieve_from_memory("debug_result") or {}
        dependency_analysis = self.retrieve_from_memory("dependency_analysis") or {}
        
        # Use the summary creation tool if available
        summary_tool = next((t for t in self.tools if t.name == "create_final_summary"), None)
        
        if summary_tool:
            try:
                summary_result = await asyncio.to_thread(
                    summary_tool.invoke,
                    {
                        "architecture": json.dumps(architecture),
                        "libraries": json.dumps(libraries),
                        "software_plan": json.dumps(software_plan),
                        "code_result": json.dumps(code_result),
                        "debug_result": json.dumps(debug_result),
                        "dependency_analysis": json.dumps(dependency_analysis)
                    }
                )
                
                # Try to parse the result as JSON
                try:
                    final_result = json.loads(summary_result)
                except json.JSONDecodeError:
                    # If it's not valid JSON, create a basic structure with the text
                    final_result = {
                        "summary": summary_result[:500] + "..." if len(summary_result) > 500 else summary_result,
                        "architecture": architecture,
                        "libraries": libraries,
                        "plan": software_plan,
                        "files": code_result.get("files", {}),
                        "debug_info": debug_result,
                        "dependencies": dependency_analysis
                    }
                
                return final_result
                
            except Exception as e:
                logger.error(f"Error creating final summary with tool: {str(e)}")
        
        # Fallback to basic summary creation
        # Create a comprehensive summary
        libraries_list = []
        if isinstance(libraries, dict) and "selected_libraries" in libraries:
            libraries_list = libraries.get("selected_libraries", [])
        elif isinstance(libraries, dict) and "libraries" in libraries and isinstance(libraries["libraries"], list):
            libraries_list = [lib["name"] for lib in libraries["libraries"] if "name" in lib]
        
        summary = (
            "Multi-agent software development process completed. "
            f"Architecture: {architecture.get('summary', 'Not specified')}. "
            f"Libraries used: {', '.join(libraries_list)}. "
            f"Implementation: {software_plan.get('summary', 'Not specified')}. "
            f"Code status: {debug_result.get('status', 'Unknown')}. "
            f"Dependency status: {dependency_analysis.get('status', 'Unknown')}."
        )
        
        # Compile all files and resources
        files = code_result.get("files", {})
        
        return {
            "summary": summary,
            "architecture": architecture,
            "libraries": libraries,
            "plan": software_plan,
            "files": files,
            "debug_info": debug_result,
            "dependencies": dependency_analysis
        }
    
    def _get_or_create_agent(self, agent_key: str, agent_class: Type[BaseAgent]) -> BaseAgent:
        """Get an existing agent instance or create a new one with LangChain components.
        
        Args:
            agent_key: Key to store/retrieve the agent under
            agent_class: Class of the agent to create
            
        Returns:
            An instance of the requested agent
        """
        if agent_key not in self.specialized_agents:
            logger.debug(f"Creating new agent instance: {agent_class.__name__}")
            
            # Create new agent with LangChain components and our memory manager for storage
            self.specialized_agents[agent_key] = agent_class(
                name=f"{agent_key}_{self.id[:8]}",
                memory_manager=self.memory_manager,
                config=self.config,
                llm=self.llm,  # Share the same LLM for consistency
                verbose=self.verbose
            )
        
        return self.specialized_agents[agent_key]
