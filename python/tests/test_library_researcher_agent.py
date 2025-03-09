import pytest
import asyncio
import json
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Dict, Any, List

from src.agents.library_researcher_agent import LibraryResearcherAgent
from src.utils.web_search import WebSearch
from conftest import MockLLM, MockMemoryManager


class TestLibraryResearcherAgent:
    """Tests for the LibraryResearcherAgent class."""
    
    def test_initialization(self, mock_llm, mock_memory_manager):
        """Test agent initialization."""
        agent = LibraryResearcherAgent(
            name="test_researcher",
            memory_manager=mock_memory_manager,
            config={"test_key": "test_value"},
            llm=mock_llm
        )
        
        # Check that the agent was initialized correctly
        assert agent.name == "test_researcher"
        assert agent.memory_manager == mock_memory_manager
        assert agent.config["test_key"] == "test_value"
        assert agent.llm == mock_llm
        
        # Check that tools were created
        assert len(agent.tools) > 0
        tool_names = [tool.name for tool in agent.tools]
        assert "web_search" in tool_names
    
    def test_get_agent_system_message(self, mock_memory_manager):
        """Test the _get_agent_system_message method."""
        agent = LibraryResearcherAgent(
            name="test_researcher",
            memory_manager=mock_memory_manager
        )
        
        # Get the system message
        system_message = agent._get_agent_system_message()
        
        # Check that the system message contains expected text
        assert "Library Researcher" in system_message
        assert "libraries" in system_message.lower()
        assert "research" in system_message.lower()
        
        # Check that it mentions key responsibilities
        assert "finding" in system_message.lower()
        assert "evaluate" in system_message.lower()
        assert "compare" in system_message.lower()
    
    @pytest.mark.asyncio
    async def test_execute_success(self, mock_llm, mock_memory_manager):
        """Test the execute method with successful execution."""
        agent = LibraryResearcherAgent(
            name="test_researcher",
            memory_manager=mock_memory_manager,
            llm=mock_llm
        )
        
        # Mock the agent executor
        mock_executor_result = {
            "output": json.dumps({
                "libraries": [
                    {
                        "name": "React",
                        "language": "JavaScript",
                        "category": "Frontend Framework",
                        "description": "A JavaScript library for building user interfaces",
                        "url": "https://reactjs.org/",
                        "pros": ["Popular", "Large community", "Good performance"],
                        "cons": ["Steep learning curve", "Requires additional libraries for state management"]
                    },
                    {
                        "name": "Express",
                        "language": "JavaScript",
                        "category": "Backend Framework",
                        "description": "Fast, unopinionated, minimalist web framework for Node.js",
                        "url": "https://expressjs.com/",
                        "pros": ["Minimal", "Flexible", "Well-documented"],
                        "cons": ["Requires additional middleware for many features"]
                    }
                ],
                "rationale": "These libraries were selected based on popularity, community support, and feature set.",
                "search_terms_used": ["best javascript frontend framework", "best node.js backend framework"]
            })
        }
        
        with patch.object(agent, 'agent_executor') as mock_executor:
            mock_executor.invoke = AsyncMock(return_value=mock_executor_result)
            
            # Execute the agent
            result = await agent.execute("Research JavaScript libraries for a web application with frontend and backend")
            
            # Check that the agent executor was called
            mock_executor.invoke.assert_called_once()
            
            # Check that the result has the expected format
            assert result["success"] == True
            assert len(result["libraries"]["libraries"]) == 2
            assert result["libraries"]["libraries"][0]["name"] == "React"
            assert result["libraries"]["libraries"][1]["name"] == "Express"
            assert "rationale" in result["libraries"]
            assert "search_terms_used" in result["libraries"]
    
    @pytest.mark.asyncio
    async def test_execute_failure(self, mock_llm, mock_memory_manager):
        """Test the execute method with execution failure."""
        agent = LibraryResearcherAgent(
            name="test_researcher",
            memory_manager=mock_memory_manager,
            llm=mock_llm
        )
        
        # Mock the agent executor to raise an exception
        with patch.object(agent, 'agent_executor') as mock_executor:
            mock_executor.invoke = AsyncMock(side_effect=Exception("Test error"))
            
            # Execute the agent
            result = await agent.execute("Research JavaScript libraries for a web application")
            
            # Check that the agent executor was called
            mock_executor.invoke.assert_called_once()
            
            # Check that the result indicates failure
            assert result["success"] == False
            assert "error" in result
            assert "Test error" in result["error"]
    
    @pytest.mark.asyncio
    async def test_execute_with_web_search(self, mock_llm, mock_memory_manager):
        """Test the execute method with web search integration."""
        agent = LibraryResearcherAgent(
            name="test_researcher",
            memory_manager=mock_memory_manager,
            llm=mock_llm
        )
        
        # Mock the WebSearch class
        mock_search_results = [
            {
                "title": "Top 10 JavaScript Frameworks",
                "url": "https://example.com/top-js-frameworks",
                "content": "React is the most popular JavaScript framework for building user interfaces."
            }
        ]
        
        # Create a mock for the search_and_fetch method
        with patch.object(WebSearch, 'search_and_fetch') as mock_search:
            mock_search.return_value = asyncio.Future()
            mock_search.return_value.set_result(mock_search_results)
            
            # Mock the agent executor
            mock_executor_result = {
                "output": json.dumps({
                    "libraries": [
                        {
                            "name": "React",
                            "description": "A JavaScript library for building user interfaces",
                            "url": "https://reactjs.org/"
                        }
                    ]
                })
            }
            
            with patch.object(agent, 'agent_executor') as mock_executor:
                mock_executor.invoke = AsyncMock(return_value=mock_executor_result)
                
                # Execute the agent
                result = await agent.execute("Research React library")
                
                # Check that the result is successful
                assert result["success"] == True
                assert "libraries" in result
                assert "React" in str(result["libraries"])