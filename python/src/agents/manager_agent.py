from typing import Any, Dict, List, Optional, Union
import asyncio
from loguru import logger

from .base_agent import BaseAgent
from .architecture_designer_agent import ArchitectureDesignerAgent
from .stack_builder_agent import StackBuilderAgent
from .library_researcher_agent import LibraryResearcherAgent
from .software_planner_agent import SoftwarePlannerAgent
from .software_programmer_agent import SoftwareProgrammerAgent
from .exception_debugger_agent import ExceptionDebuggerAgent
from .dependency_analyzer_agent import DependencyAnalyzerAgent


class ManagerAgent(BaseAgent):
    """Final Manager Agent that coordinates all specialized agents.
    
    This agent orchestrates the collaborative workflow between specialized agents,
    delegating tasks and integrating results to produce a complete software solution.
    """
    
    def __init__(self, name: str, memory_manager: Any = None, config: Optional[Dict[str, Any]] = None):
        """Initialize the Manager Agent.
        
        Args:
            name: A unique name for this agent instance
            memory_manager: The memory manager for storing context
            config: Configuration parameters for the agent
        """
        super().__init__(name, memory_manager, config)
        self.specialized_agents = {}
        
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
            final_result = self._create_final_summary()
            
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
        """Analyze the prompt to extract key requirements.
        
        Args:
            prompt: The user input prompt
            
        Returns:
            Dictionary of extracted requirements
        """
        # This would typically involve NLP processing or a specialized agent
        # For now, we'll use a simple placeholder
        return {
            "prompt": prompt,
            "extracted_requirements": [
                "Implement multi-agent system",
                "Support Python and JavaScript",
                "Handle real-time output",
                "Coordinate multiple agents"
            ]
        }
    
    async def _design_architecture(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Delegate architecture design to the ArchitectureDesignerAgent.
        
        Args:
            requirements: The extracted requirements
            
        Returns:
            Architecture design result
        """
        designer = self._get_or_create_agent("architecture_designer", ArchitectureDesignerAgent)
        arch_prompt = f"Design an architecture for: {requirements['prompt'][:500]}"
        result = await designer.execute(arch_prompt)
        
        if not result.get("success", False):
            logger.error(f"Architecture design failed: {result.get('error', 'Unknown error')}")
            raise Exception(f"Architecture design failed: {result.get('error', 'Unknown error')}")
            
        return result.get("design", {})
    
    async def _research_libraries(self, requirements: Dict[str, Any], 
                                 architecture: Dict[str, Any]) -> Dict[str, Any]:
        """Research necessary libraries using the LibraryResearcherAgent.
        
        Args:
            requirements: The extracted requirements
            architecture: The architecture design
            
        Returns:
            Library research result
        """
        researcher = self._get_or_create_agent("library_researcher", LibraryResearcherAgent)
        
        # Create a prompt for the library researcher
        lib_prompt = (
            f"Research libraries for the following architecture: "
            f"{architecture.get('summary', 'Not specified')}. "
            f"Requirements: {', '.join(requirements.get('extracted_requirements', []))}"
        )
        
        result = await researcher.execute(lib_prompt)
        
        if not result.get("success", False):
            logger.error(f"Library research failed: {result.get('error', 'Unknown error')}")
            raise Exception(f"Library research failed: {result.get('error', 'Unknown error')}")
            
        return result.get("libraries", {})
    
    async def _plan_software(self, requirements: Dict[str, Any], 
                           architecture: Dict[str, Any],
                           libraries: Dict[str, Any]) -> Dict[str, Any]:
        """Plan the software structure using the SoftwarePlannerAgent.
        
        Args:
            requirements: The extracted requirements
            architecture: The architecture design
            libraries: The researched libraries
            
        Returns:
            Software plan result
        """
        planner = self._get_or_create_agent("software_planner", SoftwarePlannerAgent)
        
        # Create a prompt for the software planner
        plan_prompt = (
            f"Create a software plan for: {requirements['prompt'][:500]}. "
            f"Architecture: {architecture.get('summary', 'Not specified')}. "
            f"Using libraries: {', '.join(libraries.get('selected_libraries', []))}"
        )
        
        result = await planner.execute(plan_prompt)
        
        if not result.get("success", False):
            logger.error(f"Software planning failed: {result.get('error', 'Unknown error')}")
            raise Exception(f"Software planning failed: {result.get('error', 'Unknown error')}")
            
        return result.get("plan", {})
    
    async def _generate_code(self, software_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Generate code using the SoftwareProgrammerAgent.
        
        Args:
            software_plan: The software plan
            
        Returns:
            Code generation result
        """
        programmer = self._get_or_create_agent("software_programmer", SoftwareProgrammerAgent)
        
        # Create a prompt for the code generator
        code_prompt = (
            f"Implement the following software plan: "
            f"{software_plan.get('summary', 'Not specified')}. "
            f"Files to create: {', '.join(software_plan.get('files', []))}"
        )
        
        result = await programmer.execute(code_prompt)
        
        if not result.get("success", False):
            logger.error(f"Code generation failed: {result.get('error', 'Unknown error')}")
            raise Exception(f"Code generation failed: {result.get('error', 'Unknown error')}")
            
        return result.get("code", {})
    
    async def _debug_code(self, code_result: Dict[str, Any]) -> Dict[str, Any]:
        """Debug code using the ExceptionDebuggerAgent.
        
        Args:
            code_result: The generated code
            
        Returns:
            Debugging result
        """
        debugger = self._get_or_create_agent("exception_debugger", ExceptionDebuggerAgent)
        
        # Create a prompt for the debugger
        debug_prompt = "Debug the following code implementation"
        
        result = await debugger.execute(debug_prompt, code=code_result)
        
        if not result.get("success", False):
            logger.error(f"Debugging failed: {result.get('error', 'Unknown error')}")
            raise Exception(f"Debugging failed: {result.get('error', 'Unknown error')}")
            
        return result.get("debug_result", {})
    
    async def _analyze_dependencies(self) -> Dict[str, Any]:
        """Analyze dependencies using the DependencyAnalyzerAgent.
        
        Returns:
            Dependency analysis result
        """
        analyzer = self._get_or_create_agent("dependency_analyzer", DependencyAnalyzerAgent)
        
        # Create a prompt for the dependency analyzer
        analyze_prompt = "Analyze dependencies in the current codebase"
        
        result = await analyzer.execute(analyze_prompt)
        
        if not result.get("success", False):
            logger.error(f"Dependency analysis failed: {result.get('error', 'Unknown error')}")
            raise Exception(f"Dependency analysis failed: {result.get('error', 'Unknown error')}")
            
        return result.get("analysis", {})
    
    def _create_final_summary(self) -> Dict[str, Any]:
        """Create a final summary of the complete solution.
        
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
        
        # Create a comprehensive summary
        summary = (
            "Multi-agent software development process completed. "
            f"Architecture: {architecture.get('summary', 'Not specified')}. "
            f"Libraries used: {', '.join(libraries.get('selected_libraries', []))}. "
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
    
    def _get_or_create_agent(self, agent_key: str, agent_class: type) -> BaseAgent:
        """Get an existing agent instance or create a new one.
        
        Args:
            agent_key: Key to store/retrieve the agent under
            agent_class: Class of the agent to create
            
        Returns:
            An instance of the requested agent
        """
        if agent_key not in self.specialized_agents:
            logger.debug(f"Creating new agent instance: {agent_class.__name__}")
            self.specialized_agents[agent_key] = agent_class(
                name=f"{agent_key}_{self.id[:8]}",
                memory_manager=self.memory_manager,
                config=self.config
            )
        
        return self.specialized_agents[agent_key]