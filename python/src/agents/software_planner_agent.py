from typing import Any, Dict, List, Optional
import asyncio
import json
import sys
from loguru import logger
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain.tools import BaseTool
from langchain.tools.file_management import ReadFileTool
from langchain.agents import AgentExecutor, create_structured_chat_agent

from .base_agent import BaseAgent


class ComponentNode(BaseModel):
    """A component in the software architecture."""
    id: str = Field(description="Unique identifier for the component")
    name: str = Field(description="Display name of the component")
    type: str = Field(description="Type of component: module, class, function, etc.")
    description: Optional[str] = Field(None, description="Brief description of the component")


class ComponentLink(BaseModel):
    """A connection between components in the architecture."""
    source: str = Field(description="ID of the source component")
    target: str = Field(description="ID of the target component")
    label: Optional[str] = Field(None, description="Description of the relationship")


class SoftwareArchitecture(BaseModel):
    """Software architecture plan."""
    modules: List[Dict[str, Any]] = Field(description="List of modules in the architecture")
    files: List[str] = Field(description="List of files to be created")
    interfaces: Dict[str, str] = Field(description="Key interfaces and their descriptions")
    nodes: List[ComponentNode] = Field(description="Graph nodes representing components")
    links: List[ComponentLink] = Field(description="Graph edges representing relationships")


class EmitGraphUpdatesToUI(BaseTool):
    """Tool for emitting graph updates to the dashboard UI."""
    name: str = "emit_graph_updates"
    description: str = """
    Send graph visualization updates to the dashboard UI.
    
    Args:
        nodes: List of nodes representing components. Each node should have:
            - id: Unique identifier for the component
            - name: Display name for the component
            - type: Type of component (module, class, function, etc.)
            - description: Brief description of the component
        links: List of links representing relationships. Each link should have:
            - source: ID of the source component
            - target: ID of the target component
            - label: Optional description of the relationship
    
    Example:
        emit_graph_updates(
            nodes=[
                {"id": "app_module", "name": "App", "type": "module", "description": "Main application module"},
                {"id": "auth_module", "name": "Auth", "type": "module", "description": "Authentication module"}
            ],
            links=[
                {"source": "app_module", "target": "auth_module", "label": "imports"}
            ]
        )
    """
    dashboard_mode: bool = False
    
    def __init__(self, dashboard_mode: bool = False):
        super().__init__()
        self.dashboard_mode = dashboard_mode
    
    def _run(self, nodes: List[Dict], links: List[Dict]) -> str:
        """Emit the graph data to the UI."""
        if self.dashboard_mode:
            # Format the update for the dashboard
            update = {
                "type": "componentGraph",
                "data": {"nodes": nodes, "links": links}
            }
            # Print a special marker that will be caught by the dashboard
            print(f"DASHBOARD_UPDATE:{json.dumps(update)}")
            return f"Graph updates sent to dashboard UI with {len(nodes)} nodes and {len(links)} links"
        else:
            return "Dashboard updates disabled (not in dashboard mode)"


class SoftwarePlannerAgent(BaseAgent):
    """Software Planner Agent.
    
    This agent is responsible for architecting the code structure including
    parent-child relationships, function signatures, and module boundaries.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dashboard_mode = "--dashboard-mode" in sys.argv
        
        # Get dashboard mode from config if provided
        if kwargs.get("config") and isinstance(kwargs["config"], dict):
            if kwargs["config"].get("dashboard_mode"):
                self.dashboard_mode = True
                
        # Log dashboard mode for debugging
        print(f"SoftwarePlannerAgent initialized with dashboard_mode={self.dashboard_mode}")
    
    async def execute(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        """Execute the agent's main task - planning software architecture.
        
        Args:
            prompt: The input prompt describing requirements
            **kwargs: Additional parameters for execution
            
        Returns:
            Dictionary containing the software plan results
        """
        logger.info(f"Software Planner Agent {self.name} executing with prompt: {prompt[:100]}...")
        
        # Custom tools for the planner agent
        read_file_tool = ReadFileTool()
        graph_update_tool = EmitGraphUpdatesToUI(dashboard_mode=self.dashboard_mode)
        
        tools = [read_file_tool, graph_update_tool]
        
        # Define output parser for structured output
        output_parser = PydanticOutputParser(pydantic_object=SoftwareArchitecture)
        
        # Create a specialized prompt for the software planner
        system_prompt = """You are a Software Planner Agent.
        Your task is to architect the code structure including parent-child relationships,
        function signatures, and module boundaries.
        
        Based on the user requirements, create a detailed software architecture plan that includes:
        1. Modules and their purpose
        2. Files that need to be created
        3. Key interfaces/classes with brief descriptions
        4. Component relationships (parent-child or dependency relationships)
        
        IMPORTANT:
        - Follow clean architecture principles with clear separation of concerns
        - Create a logical hierarchy of components
        - Ensure modules are properly organized
        - Identify reusable components
        - Define clear interfaces between modules
        
        CRITICAL FOR VISUALIZATION:
        You MUST create a visualization graph with nodes and links:
        - Each node represents a component (module, class, function, etc.) with:
          * id: A unique identifier (e.g., "auth_module", "user_service")
          * name: A display name for the component
          * type: The type of component (e.g., "module", "class", "function", "interface")
          * description: A brief description of the component's purpose
          
        - Each link represents a relationship between components with:
          * source: The ID of the source component
          * target: The ID of the target component
          * label: Optional description of the relationship (e.g., "imports", "extends", "uses")
          
        Example nodes:
        [
          {"id": "core_module", "name": "Core Module", "type": "module", "description": "Core functionality"},
          {"id": "user_service", "name": "UserService", "type": "class", "description": "Handles user operations"}
        ]
        
        Example links:
        [
          {"source": "core_module", "target": "user_service", "label": "contains"}
        ]
        
        When your plan is complete, use the emit_graph_updates tool to send the visualization data to the dashboard.
        
        Format your final response using the following schema:
        {format_instructions}
        """
        
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="history"),
            ("user", "{input}"),
        ]).partial(format_instructions=output_parser.get_format_instructions())
        
        try:
            # Create a structured agent with tools
            agent = create_structured_chat_agent(
                self.llm, 
                tools, 
                prompt_template
            )
            
            # Create the agent executor
            agent_executor = AgentExecutor(
                agent=agent,
                tools=tools,
                verbose=True,
                handle_parsing_errors=True,
                max_iterations=10
            )
            
            # Execute the agent
            logger.debug("Planning software architecture...")
            result = await agent_executor.ainvoke({
                "input": prompt,
                "history": self.conversation_history
            })
            
            # Parse the final output to ensure it matches our schema
            try:
                if isinstance(result.get("output"), str):
                    # Try to extract a structured output if it's embedded in text
                    architecture = output_parser.parse(result["output"])
                else:
                    # Already structured output
                    architecture = SoftwareArchitecture(**result["output"])
                
                # Add the response to the conversation history
                plan_summary = f"Software planning completed. Designed structure with {len(architecture.modules)} modules and {len(architecture.files)} files."
                self.add_to_conversation("assistant", plan_summary)
                
                # Emit the graph updates again to ensure they're visible
                if self.dashboard_mode:
                    # Check if nodes and links exist, create them if they don't
                    if not hasattr(architecture, 'nodes') or not architecture.nodes:
                        # Create default nodes from modules and files
                        nodes = []
                        for i, module in enumerate(architecture.modules):
                            # Create a node for the module
                            module_id = f"module_{i}"
                            nodes.append(ComponentNode(
                                id=module_id,
                                name=module.get('name', f"Module {i}"),
                                type="module",
                                description=module.get('description', '')
                            ))
                            
                            # Create nodes for components in this module
                            for j, component in enumerate(module.get('components', [])):
                                comp_id = f"comp_{i}_{j}"
                                nodes.append(ComponentNode(
                                    id=comp_id,
                                    name=component,
                                    type="component",
                                    description=f"Component in {module.get('name', 'module')}"
                                ))
                                
                                # Link component to its module
                                if not hasattr(architecture, 'links'):
                                    architecture.links = []
                                architecture.links.append(ComponentLink(
                                    source=module_id,
                                    target=comp_id,
                                    label="contains"
                                ))
                        
                        # Set the nodes in the architecture
                        architecture.nodes = nodes
                    
                    # Ensure links exist
                    if not hasattr(architecture, 'links') or not architecture.links:
                        architecture.links = []
                        # Create some basic links between modules if none exist
                        if len(architecture.nodes) > 1:
                            for i in range(len(architecture.nodes) - 1):
                                architecture.links.append(ComponentLink(
                                    source=architecture.nodes[i].id,
                                    target=architecture.nodes[i+1].id,
                                    label="depends on"
                                ))
                    
                    # Now emit the graph to the UI
                    nodes_list = [node.dict() for node in architecture.nodes]
                    links_list = [link.dict() for link in architecture.links]
                    graph_update_tool._run(nodes_list, links_list)
                
                logger.info(f"Software planning complete with {len(architecture.files)} planned files")
                return {
                    "success": True,
                    "plan": architecture.dict(),
                    "message": "Software planning completed successfully"
                }
            except Exception as parse_error:
                logger.error(f"Error parsing architecture output: {str(parse_error)}")
                # Create a basic fallback plan with some default components
                fallback_plan = {
                    "modules": [
                        {
                            "name": "core",
                            "description": "Core functionality",
                            "components": ["BaseComponent", "Config"]
                        },
                        {
                            "name": "api",
                            "description": "API layer",
                            "components": ["Routes", "Controllers"]
                        },
                        {
                            "name": "services",
                            "description": "Business logic",
                            "components": ["UserService", "DataService"]
                        },
                        {
                            "name": "utils",
                            "description": "Utilities",
                            "components": ["Logger", "Helpers"]
                        }
                    ],
                    "files": ["src/core/base.py", "src/api/routes.py", "src/services/user_service.py", "src/utils/logger.py"],
                    "interfaces": {"BaseComponent": "Base class for all components"}
                }
                
                # Create nodes and links for the graph
                nodes = []
                links = []
                
                # Add module nodes
                for i, module in enumerate(fallback_plan["modules"]):
                    module_id = f"module_{i}"
                    nodes.append({
                        "id": module_id,
                        "name": module["name"],
                        "type": "module",
                        "description": module["description"]
                    })
                    
                    # Add component nodes and links
                    for j, component in enumerate(module["components"]):
                        comp_id = f"comp_{i}_{j}"
                        nodes.append({
                            "id": comp_id,
                            "name": component,
                            "type": "component",
                            "description": f"Component in {module['name']}"
                        })
                        
                        # Link component to its module
                        links.append({
                            "source": module_id,
                            "target": comp_id,
                            "label": "contains"
                        })
                
                # Add some inter-module dependencies
                if len(fallback_plan["modules"]) > 1:
                    for i in range(len(fallback_plan["modules"]) - 1):
                        links.append({
                            "source": f"module_{i+1}",
                            "target": f"module_{i}",
                            "label": "depends on"
                        })
                
                # Send graph to dashboard
                if self.dashboard_mode:
                    graph_update_tool._run(nodes, links)
                
                fallback_plan["nodes"] = nodes
                fallback_plan["links"] = links
                
                return {
                    "success": True,
                    "plan": fallback_plan,
                    "message": "Software planning completed with fallback output"
                }
            
        except Exception as e:
            logger.exception(f"Software planning failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "Software planning failed"
            }
