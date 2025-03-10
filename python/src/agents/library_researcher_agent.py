from typing import Any, Dict, List, Optional, Type, cast
import asyncio
import json
import re
from loguru import logger

from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.messages import SystemMessage
from langchain_core.tools import BaseTool, tool
from langchain_core.output_parsers import PydanticOutputParser
from langchain.agents import AgentExecutor, create_structured_chat_agent

from .base_agent import BaseAgent
from utils.web_search import WebSearch, WebSearchTool
from utils.shell_executor import ShellExecutor, ShellExecutorTool


class Library(BaseModel):
    """Information about a library."""
    name: str = Field(description="Name of the library")
    language: str = Field(description="Programming language the library is for")
    description: str = Field(description="Brief description of the library")
    github_stars: Optional[str] = Field(None, description="Number of GitHub stars (if available)")
    license: Optional[str] = Field(None, description="License type (e.g., MIT, Apache-2.0)")
    pros: List[str] = Field(description="Advantages of using this library")
    cons: List[str] = Field(description="Disadvantages or limitations of this library")
    requires_api_key: bool = Field(description="Whether the library requires an API key")
    installation: str = Field(description="How to install the library (e.g., pip install, npm install)")
    example_usage: Optional[str] = Field(None, description="Simple example of how to use the library")
    alternatives: List[str] = Field(default_factory=list, description="Alternative libraries that serve similar purposes")


class LibraryCategory(BaseModel):
    """A category of libraries with similar functionality."""
    name: str = Field(description="Name of the category (e.g., 'backend', 'data_processing')")
    description: str = Field(description="Description of what libraries in this category do")
    libraries: List[Library] = Field(description="Libraries in this category")
    recommended: Optional[str] = Field(None, description="Name of the recommended library in this category")


class ResearchResult(BaseModel):
    """Complete library research result."""
    query: str = Field(description="The original query that was researched")
    language: str = Field(description="The programming language requested")
    functionality: str = Field(description="The functionality being researched")
    categories: List[LibraryCategory] = Field(description="Categories of libraries found")
    selected_libraries: List[str] = Field(description="Names of the recommended libraries")
    dependencies: Dict[str, List[str]] = Field(description="Dependencies required by the selected libraries")
    installation_instructions: List[str] = Field(description="Instructions for installing all selected libraries")
    rationale: str = Field(description="Explanation of why these libraries were selected")


class LibraryResearcherAgent(BaseAgent):
    """Library Researcher Agent.
    
    This agent is responsible for researching and identifying the best
    free, open-source libraries for specific functions or requirements.
    """
    
    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize the Library Researcher Agent with specialized tools."""
        super().__init__(*args, **kwargs)
        
        # Create library research tools
        research_tools = self._create_research_tools()
        self.tools.extend(research_tools)
        
        # Re-create the agent executor with the new tools
        self.agent_executor = self._create_agent_executor()
    
    def _get_agent_system_message(self) -> str:
        """Override system message for the library researcher agent."""
        return """You are an expert Library Researcher Agent specialized in finding the best software libraries.

Your task is to research and identify the best free, open-source libraries for specific functions or requirements.
You should:
- Focus on libraries that are free and open-source
- Avoid paid services and APIs that require keys/registration when possible
- Analyze the pros and cons of different libraries
- Consider factors like popularity, maintenance, documentation, and ease of use
- Track dependencies and ensure they're added to the installation process
- Provide clear installation instructions for all recommended libraries

IMPORTANT: Prioritize libraries that don't require API keys or registration. Only recommend libraries requiring keys when there are no good alternatives.

Provide clear, structured output including library information, pros/cons, and installation instructions.
Be thorough in your analysis and provide specific details about each library.
"""
    
    def _create_research_tools(self) -> List[BaseTool]:
        """Create specialized tools for library research tasks."""
        
        # Add web search tool
        web_search_tool = WebSearchTool(web_search=WebSearch())
        
        @tool("research_libraries")
        def research_libraries(query: str, language: str) -> str:
            """
            Research libraries for a specific function in a given programming language.
            
            Args:
                query: Description of the functionality needed
                language: Programming language (e.g., 'python', 'javascript')
                
            Returns:
                A JSON string containing the library research results
            """
            parser = PydanticOutputParser(pydantic_object=ResearchResult)
            
            # Create a specialized prompt for library research
            template = """
            You are tasked with researching libraries for the following query:
            
            Query: {query}
            Language: {language}
            
            Research and identify the best free, open-source libraries that:
            1. Provide the functionality described in the query
            2. Are compatible with the specified programming language
            3. Preferably don't require API keys or registration
            4. Are well-maintained and have good documentation
            
            For each library, provide:
            - Name, description, and language
            - GitHub stars or popularity metrics if available
            - License type
            - Pros and cons
            - Whether it requires an API key
            - Installation instructions
            - A simple example of usage
            - Alternative libraries
            
            Group libraries into meaningful categories based on their functionality.
            
            {format_instructions}
            """
            
            prompt = ChatPromptTemplate.from_messages([
                SystemMessagePromptTemplate.from_template(template).format(
                    query=query,
                    language=language,
                    format_instructions=parser.get_format_instructions()
                )
            ])
            
            # Generate the research using the LLM
            chain = prompt | self.llm | parser
            
            try:
                # Use the web search tool to gather information
                web_search = WebSearch()
                search_query = f"best {language} libraries for {query} open source"
                
                # Search for libraries
                search_results = asyncio.run(web_search.search_and_fetch(search_query, num_results=5))
                
                # Extract content from search results
                content = "\n\n".join([
                    f"Title: {result.get('title', '')}\n" +
                    f"URL: {result.get('url', '')}\n" +
                    f"Content: {result.get('content', '')[:1500]}..."
                    for result in search_results
                ])
                
                # Invoke the LLM with the gathered information
                result = chain.invoke({"content": content})
                
                # Convert the Pydantic object to a dict
                return json.dumps(result.dict())
            except Exception as e:
                logger.error(f"Error in library research: {str(e)}")
                # Return a basic research result as fallback
                return json.dumps({
                    "query": query,
                    "language": language,
                    "functionality": query,
                    "categories": [
                        {
                            "name": "general",
                            "description": f"Libraries for {query}",
                            "libraries": [
                                {
                                    "name": "example_library",
                                    "language": language,
                                    "description": "Error occurred during research",
                                    "pros": ["Unknown"],
                                    "cons": ["Research failed"],
                                    "requires_api_key": False,
                                    "installation": f"pip install example_library" if language.lower() == "python" else "npm install example-library"
                                }
                            ],
                            "recommended": "example_library"
                        }
                    ],
                    "selected_libraries": ["example_library"],
                    "dependencies": {},
                    "installation_instructions": [f"pip install example_library" if language.lower() == "python" else "npm install example-library"],
                    "rationale": "Error during research: " + str(e)
                })
        
        @tool("analyze_library_dependencies")
        def analyze_library_dependencies(library_name: str, language: str) -> str:
            """
            Analyze the dependencies of a specific library.
            
            Args:
                library_name: Name of the library to analyze
                language: Programming language of the library
                
            Returns:
                JSON string with the library's dependencies
            """
            prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content=f"""
                You are a library dependency expert. Analyze the dependencies for the {library_name} library in {language}.
                
                Provide:
                1. Direct dependencies required by the library
                2. Any potential conflicts with other common libraries
                3. Installation instructions that include all necessary dependencies
                
                Format your response as a JSON object with these fields:
                {{
                    "dependencies": ["dep1", "dep2", ...],
                    "potential_conflicts": ["conflict1", "conflict2", ...],
                    "installation_instructions": "Instructions for installation including dependencies"
                }}
                """)
            ])
            
            # Use the web search tool to gather information
            web_search = WebSearch()
            search_query = f"{library_name} {language} dependencies requirements"
            
            try:
                # Search for dependency information
                search_results = asyncio.run(web_search.search_and_fetch(search_query, num_results=3))
                
                # Extract content from search results
                content = "\n\n".join([
                    f"Title: {result.get('title', '')}\n" +
                    f"URL: {result.get('url', '')}\n" +
                    f"Content: {result.get('content', '')[:1000]}..."
                    for result in search_results
                ])
                
                # Generate dependency analysis using the LLM
                chain = prompt | self.llm
                result = chain.invoke({"content": content})
                
                return result.content
            except Exception as e:
                logger.error(f"Error analyzing dependencies: {str(e)}")
                return json.dumps({
                    "dependencies": [],
                    "potential_conflicts": [],
                    "installation_instructions": f"Install using {'pip install ' + library_name if language.lower() == 'python' else 'npm install ' + library_name}"
                })
        
        @tool("compare_libraries")
        def compare_libraries(libraries: List[str], criteria: str) -> str:
            """
            Compare multiple libraries based on specific criteria.
            
            Args:
                libraries: List of library names to compare
                criteria: Criteria for comparison (e.g., 'performance', 'ease of use')
                
            Returns:
                JSON string with comparison results
            """
            prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content=f"""
                You are a library comparison expert. Compare the following libraries based on {criteria}:
                
                Libraries: {', '.join(libraries)}
                
                For each library, provide:
                1. Strengths related to the criteria
                2. Weaknesses related to the criteria
                3. A numerical score from 1-10 for the criteria
                
                Then provide an overall recommendation based on the comparison.
                
                Format your response as a JSON object with these fields:
                {{
                    "comparisons": [
                        {{
                            "library": "lib_name",
                            "strengths": ["strength1", "strength2", ...],
                            "weaknesses": ["weakness1", "weakness2", ...],
                            "score": score_value
                        }},
                        ...
                    ],
                    "recommendation": "Your overall recommendation"
                }}
                """)
            ])
            
            # Use the web search tool to gather information
            web_search = WebSearch()
            search_query = f"compare {' vs '.join(libraries)} {criteria}"
            
            try:
                # Search for comparison information
                search_results = asyncio.run(web_search.search_and_fetch(search_query, num_results=3))
                
                # Extract content from search results
                content = "\n\n".join([
                    f"Title: {result.get('title', '')}\n" +
                    f"URL: {result.get('url', '')}\n" +
                    f"Content: {result.get('content', '')[:1000]}..."
                    for result in search_results
                ])
                
                # Generate comparison using the LLM
                chain = prompt | self.llm
                result = chain.invoke({"content": content})
                
                return result.content
            except Exception as e:
                logger.error(f"Error comparing libraries: {str(e)}")
                return json.dumps({
                    "comparisons": [
                        {
                            "library": lib,
                            "strengths": ["Unable to determine due to research error"],
                            "weaknesses": ["Unable to determine due to research error"],
                            "score": 5
                        }
                        for lib in libraries
                    ],
                    "recommendation": "Unable to provide a recommendation due to research error"
                })
        
        return [research_libraries, analyze_library_dependencies, compare_libraries, web_search_tool]
    
    async def execute(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        """Execute the agent's main task - researching libraries.
        
        Args:
            prompt: The input prompt describing requirements
            **kwargs: Additional parameters for execution
            
        Returns:
            Dictionary containing the library research results
        """
        logger.info(f"Library Researcher Agent {self.name} executing with prompt: {prompt[:100]}...")
        
        try:
            # Extract language from prompt or kwargs
            language = kwargs.get("language", "")
            if not language:
                # Try to extract language from prompt
                language_match = re.search(r'language[:\s]+(\w+)', prompt, re.IGNORECASE)
                if language_match:
                    language = language_match.group(1)
                else:
                    # Default to Python if no language specified
                    language = "python"
            
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
            logger.debug("Researching libraries...")
            result = await agent_executor.ainvoke({
                "input": f"""
                Research libraries for the following requirements:
                
                {prompt}
                
                Programming Language: {language}
                
                Focus on free, open-source libraries that don't require API keys or registration when possible.
                Analyze pros and cons of each library and provide installation instructions.
                """
            })
            
            # If successful, try to parse the research result from the output
            if result:
                try:
                    # Try to extract structured research result from the response
                    raw_output = result.get("output", "")
                    
                    # Look for JSON in the output
                    json_match = re.search(r'```json\n(.*?)\n```', raw_output, re.DOTALL)
                    
                    if json_match:
                        research_json = json_match.group(1)
                    else:
                        # Try to find any JSON-like structure
                        json_match = re.search(r'({.*})', raw_output, re.DOTALL)
                        research_json = json_match.group(1) if json_match else raw_output
                    
                    # Parse the JSON
                    research_result = json.loads(research_json)
                    
                    # If it doesn't have the expected structure, use the research_libraries tool directly
                    if not all(k in research_result for k in ["categories", "selected_libraries"]):
                        logger.info("Using research_libraries tool directly")
                        research_result_str = await asyncio.to_thread(
                            self.tools[0].invoke,
                            {"query": prompt, "language": language}
                        )
                        research_result = json.loads(research_result_str)
                    
                    # Add the research result to the conversation
                    selected_count = len(research_result.get("selected_libraries", []))
                    categories_count = len(research_result.get("categories", []))
                    
                    self.add_to_conversation(
                        "assistant", 
                        f"Library research completed. Selected {selected_count} libraries across {categories_count} categories."
                    )
                    
                    logger.info(f"Library research complete, found {selected_count} libraries")
                    return {
                        "success": True,
                        "libraries": research_result,
                        "message": "Library research completed successfully"
                    }
                    
                except Exception as parse_error:
                    logger.warning(f"Error parsing research result: {str(parse_error)}")
                    # Try to use the research_libraries tool directly
                    try:
                        research_result_str = await asyncio.to_thread(
                            self.tools[0].invoke,
                            {"query": prompt, "language": language}
                        )
                        research_result = json.loads(research_result_str)
                        
                        selected_count = len(research_result.get("selected_libraries", []))
                        categories_count = len(research_result.get("categories", []))
                        
                        self.add_to_conversation(
                            "assistant", 
                            f"Library research completed using fallback. Selected {selected_count} libraries across {categories_count} categories."
                        )
                        
                        return {
                            "success": True,
                            "libraries": research_result,
                            "message": "Library research completed using fallback"
                        }
                    except Exception as tool_error:
                        logger.error(f"Research tool error: {str(tool_error)}")
                        # Create a basic fallback research result
                        research_result = {
                            "query": prompt,
                            "language": language,
                            "functionality": prompt,
                            "categories": [
                                {
                                    "name": "general",
                                    "description": f"Libraries for {prompt}",
                                    "libraries": [
                                        {
                                            "name": "example_library",
                                            "language": language,
                                            "description": "Error occurred during research",
                                            "pros": ["Unknown"],
                                            "cons": ["Research failed"],
                                            "requires_api_key": False,
                                            "installation": f"pip install example_library" if language.lower() == "python" else "npm install example-library"
                                        }
                                    ],
                                    "recommended": "example_library"
                                }
                            ],
                            "selected_libraries": ["example_library"],
                            "dependencies": {},
                            "installation_instructions": [f"pip install example_library" if language.lower() == "python" else "npm install example-library"],
                            "rationale": "Error during research: " + str(parse_error)
                        }
                        
                        self.add_to_conversation(
                            "assistant", 
                            "Library research encountered errors. Using fallback result."
                        )
                        
                        return {
                            "success": True,
                            "libraries": research_result,
                            "message": "Library research fallback used due to errors"
                        }
            
            # If we get here, something went wrong with the agent execution
            logger.warning("Agent execution did not return expected result")
            return {
                "success": False,
                "error": "Agent execution failed to return valid results",
                "message": "Library research failed"
            }
            
        except Exception as e:
            logger.exception(f"Library research failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "Library research failed"
            }
