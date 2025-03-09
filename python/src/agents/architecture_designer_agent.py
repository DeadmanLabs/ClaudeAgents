from typing import Any, Dict, List, Optional, Type, cast
import asyncio
from loguru import logger
import json

from langchain.output_parsers import PydanticOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.messages import SystemMessage
from langchain_core.tools import BaseTool, tool

from .base_agent import BaseAgent


class Component(BaseModel):
    """Description of a component in the architecture."""
    name: str = Field(description="Name of the component")
    technology: str = Field(description="Technology used for the component")
    responsibility: str = Field(description="Primary responsibility of the component")


class ArchitectureDesign(BaseModel):
    """Structured format for architecture design output."""
    summary: str = Field(description="Brief summary of the overall architecture")
    backend: str = Field(description="Description of backend technologies")
    frontend: str = Field(description="Description of frontend technologies")
    database: str = Field(description="Description of data storage technologies")
    deployment: str = Field(description="Deployment strategy")
    components: List[Component] = Field(description="List of key components in the architecture")
    rationale: str = Field(description="Explanation of why this architecture was chosen")
    messaging: Optional[str] = Field(description="Messaging or event systems if applicable", default=None)


class ArchitectureDesignerAgent(BaseAgent):
    """Architecture Designer Agent.
    
    This agent is responsible for generating an infrastructure stack design
    based on the user's requirements.
    """
    
    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize the Architecture Designer Agent with specialized tools."""
        super().__init__(*args, **kwargs)
        
        # Create architecture design tools
        architecture_tools = self._create_architecture_tools()
        self.tools.extend(architecture_tools)
        
        # Re-create the agent executor with the new tools
        self.agent_executor = self._create_agent_executor()
    
    def _get_agent_system_message(self) -> str:
        """Override system message for the architecture designer agent."""
        return """You are an expert Architecture Designer Agent specialized in software and infrastructure architecture.

Your task is to analyze requirements and design an optimal architecture stack that meets those requirements.
You should consider:
- Scalability, maintainability, and performance needs
- Technology compatibility and integration points
- Deployment and operational concerns
- Security and compliance requirements
- Cost considerations where specified

Provide clear, structured output including components, technologies, and rationale for your choices.
Be specific about technologies and versions where appropriate.
"""
    
    def _create_architecture_tools(self) -> List[BaseTool]:
        """Create specialized tools for architecture design tasks."""
        
        @tool("design_architecture")
        def design_architecture(requirements: str) -> str:
            """
            Design a complete software architecture based on the provided requirements.
            
            Args:
                requirements: Detailed requirements for the architecture design
                
            Returns:
                A JSON string containing the complete architecture design
            """
            parser = PydanticOutputParser(pydantic_object=ArchitectureDesign)
            
            # Create a specialized prompt for architecture design
            template = """
            You are tasked with designing a complete software architecture based on these requirements:
            
            {requirements}
            
            Analyze these requirements and create a comprehensive architecture design.
            
            {format_instructions}
            """
            
            prompt = ChatPromptTemplate.from_messages([
                SystemMessagePromptTemplate.from_template(template).format(
                    requirements=requirements,
                    format_instructions=parser.get_format_instructions()
                )
            ])
            
            # Generate the architecture using the LLM
            chain = prompt | self.llm | parser
            
            try:
                result = chain.invoke({})
                # Convert the Pydantic object to a dict
                return json.dumps(result.dict())
            except Exception as e:
                logger.error(f"Error in architecture design: {str(e)}")
                # Return a basic architecture as fallback
                return json.dumps({
                    "summary": "Error occurred during architecture design",
                    "backend": "Generic backend services",
                    "frontend": "Generic frontend",
                    "database": "Appropriate database for requirements",
                    "deployment": "Standard deployment",
                    "components": [
                        {
                            "name": "Core Service",
                            "technology": "Recommended technology",
                            "responsibility": "Core functionality"
                        }
                    ],
                    "rationale": "Fallback design due to error in processing"
                })
        
        @tool("evaluate_architecture")
        def evaluate_architecture(architecture_json: str, requirements: str) -> str:
            """
            Evaluate an architecture design against the provided requirements.
            
            Args:
                architecture_json: JSON string of the architecture to evaluate
                requirements: The requirements to evaluate against
                
            Returns:
                Evaluation with strengths, weaknesses, and improvement suggestions
            """
            prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content="""
                You are an architecture evaluation expert. Evaluate the provided architecture against the requirements.
                Identify strengths, weaknesses, and provide suggestions for improvement.
                
                Format your response as:
                
                {
                    "strengths": ["list", "of", "strengths"],
                    "weaknesses": ["list", "of", "weaknesses"],
                    "suggestions": ["list", "of", "improvements"]
                }
                """),
                HumanMessagePromptTemplate.from_template("""
                Requirements:
                {requirements}
                
                Architecture:
                {architecture}
                
                Provide your evaluation:
                """)
            ])
            
            # Generate the evaluation using the LLM
            chain = prompt | self.llm
            
            try:
                result = chain.invoke({
                    "requirements": requirements,
                    "architecture": architecture_json
                })
                return result.content
            except Exception as e:
                logger.error(f"Error in architecture evaluation: {str(e)}")
                return json.dumps({
                    "strengths": ["Unable to evaluate strengths"],
                    "weaknesses": ["Error during evaluation"],
                    "suggestions": ["Retry evaluation"]
                })
        
        return [design_architecture, evaluate_architecture]
    
    async def execute(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        """Execute the agent's main task - designing an architecture stack.
        
        Args:
            prompt: The input prompt describing requirements
            **kwargs: Additional parameters for execution
            
        Returns:
            Dictionary containing the architecture design results
        """
        logger.info(f"Architecture Designer Agent {self.name} executing with prompt: {prompt[:100]}...")
        
        try:
            # Use the LangChain agent to handle the execution
            result = await super().execute(prompt, **kwargs)
            
            # If successful, try to parse the design from the result
            if result.get("success", False):
                try:
                    # Try to extract structured architecture from the response
                    raw_output = result.get("data", "")
                    
                    # Look for JSON in the output
                    import re
                    json_match = re.search(r'```json\n(.*?)\n```', raw_output, re.DOTALL)
                    
                    if json_match:
                        architecture_json = json_match.group(1)
                    else:
                        # Try to find any JSON-like structure
                        json_match = re.search(r'({.*})', raw_output, re.DOTALL)
                        architecture_json = json_match.group(1) if json_match else raw_output
                    
                    # Parse the JSON
                    architecture = json.loads(architecture_json)
                    
                    # If it doesn't have the expected structure, use the tool directly
                    if not all(k in architecture for k in ["summary", "backend", "frontend"]):
                        logger.info("Using architecture design tool directly")
                        design_result = await asyncio.to_thread(
                            self.tools[0].invoke,
                            {"requirements": prompt}
                        )
                        architecture = json.loads(design_result)
                    
                    # Add the parsed architecture to the result
                    result["design"] = architecture
                    result["message"] = "Architecture design completed successfully"
                    
                except Exception as parse_error:
                    logger.warning(f"Error parsing architecture design: {str(parse_error)}")
                    # Try to use the design tool directly
                    try:
                        design_result = await asyncio.to_thread(
                            self.tools[0].invoke,
                            {"requirements": prompt}
                        )
                        architecture = json.loads(design_result)
                        result["design"] = architecture
                        result["message"] = "Architecture design completed using fallback"
                    except Exception as tool_error:
                        logger.error(f"Design tool error: {str(tool_error)}")
                        result["design"] = {
                            "summary": "Error occurred during architecture design",
                            "backend": "Generic backend services",
                            "frontend": "Generic frontend",
                            "database": "Appropriate database for requirements",
                            "deployment": "Standard deployment",
                            "components": [
                                {
                                    "name": "Core Service",
                                    "technology": "Recommended technology",
                                    "responsibility": "Core functionality"
                                }
                            ],
                            "rationale": "Fallback design due to error in processing"
                        }
                        result["message"] = "Architecture design fallback used due to errors"
            
            return result
            
        except Exception as e:
            logger.exception(f"Architecture design failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "Architecture design failed"
            }