import pytest
import asyncio
import json
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Dict, Any, List

from src.agents.manager_agent import ManagerAgent, RequirementsOutput
from conftest import MockLLM, MockMemoryManager


class TestManagerAgent:
    """Tests for the ManagerAgent class."""
    
    def test_initialization(self, mock_llm, mock_memory_manager):
        """Test agent initialization."""
        agent = ManagerAgent(
            name="test_manager",
            memory_manager=mock_memory_manager,
            config={"test_key": "test_value"},
            llm=mock_llm
        )
        
        # Check that the agent was initialized correctly
        assert agent.name == "test_manager"
        assert agent.memory_manager == mock_memory_manager
        assert agent.config["test_key"] == "test_value"
        assert agent.llm == mock_llm
        assert agent.specialized_agents == {}
        assert len(agent.tools) > 0  # Should have created manager tools
    
    def test_get_agent_system_message(self, mock_memory_manager):
        """Test the _get_agent_system_message method."""
        agent = ManagerAgent(
            name="test_manager",
            memory_manager=mock_memory_manager
        )
        
        # Get the system message
        system_message = agent._get_agent_system_message()
        
        # Check that the system message contains expected text
        assert "Manager Agent" in system_message
        assert "coordinate" in system_message.lower()
        assert "specialized" in system_message.lower()
        
        # Check that it mentions all the agent types
        assert "Architecture Designer" in system_message
        assert "Library Researcher" in system_message
        assert "Software Planner" in system_message
        assert "Software Programmer" in system_message
        assert "Exception Debugger" in system_message
        assert "Dependency Analyzer" in system_message
    
    def test_create_manager_tools(self, mock_llm, mock_memory_manager):
        """Test the _create_manager_tools method."""
        agent = ManagerAgent(
            name="test_manager",
            memory_manager=mock_memory_manager,
            llm=mock_llm
        )
        
        # Create manager tools
        tools = agent._create_manager_tools()
        
        # Check that the tools were created correctly
        assert len(tools) == 3
        tool_names = [tool.name for tool in tools]
        assert "analyze_requirements" in tool_names
        assert "process_agent_result" in tool_names
        assert "create_final_summary" in tool_names
    
    @pytest.mark.asyncio
    async def test_analyze_requirements(self, mock_llm, mock_memory_manager):
        """Test the _analyze_requirements method."""
        agent = ManagerAgent(
            name="test_manager",
            memory_manager=mock_memory_manager,
            llm=mock_llm
        )
        
        # Mock the analyze_requirements tool
        mock_analyze_tool = MagicMock()
        mock_analyze_tool.name = "analyze_requirements"
        mock_analyze_tool.invoke = AsyncMock(return_value=json.dumps({
            "prompt": "Create a web application",
            "extracted_requirements": ["Web application", "User authentication"],
            "primary_language": "Python",
            "technologies": ["Flask", "React"],
            "constraints": ["Must be secure"]
        }))
        
        # Replace the tool with our mock
        for i, tool in enumerate(agent.tools):
            if tool.name == "analyze_requirements":
                agent.tools[i] = mock_analyze_tool
                break
        
        # Call analyze_requirements
        result = await agent._analyze_requirements("Create a web application")
        
        # Check that the tool was invoked
        mock_analyze_tool.invoke.assert_called_once()
        
        # Check that the result has the expected format
        assert result["prompt"] == "Create a web application"
        assert "Web application" in result["extracted_requirements"]
        assert result["primary_language"] == "Python"
        assert "Flask" in result["technologies"]
        assert "Must be secure" in result["constraints"]
    
    @pytest.mark.asyncio
    async def test_design_architecture(self, mock_llm, mock_memory_manager):
        """Test the _design_architecture method."""
        agent = ManagerAgent(
            name="test_manager",
            memory_manager=mock_memory_manager,
            llm=mock_llm
        )
        
        # Mock the architecture designer agent
        mock_designer = MagicMock()
        mock_designer.execute = AsyncMock(return_value={
            "success": True,
            "design": {
                "summary": "Microservices architecture",
                "backend": "Flask",
                "frontend": "React",
                "database": "PostgreSQL",
                "deployment": "Docker",
                "components": [
                    {
                        "name": "API Gateway",
                        "technology": "Flask",
                        "responsibility": "Routing"
                    }
                ],
                "rationale": "Scalable and modular design"
            }
        })
        
        # Mock the _get_or_create_agent method to return our mock
        with patch.object(agent, '_get_or_create_agent', return_value=mock_designer):
            # Call design_architecture
            requirements = {
                "prompt": "Create a web application",
                "extracted_requirements": ["Web application", "User authentication"],
                "primary_language": "Python",
                "technologies": ["Flask", "React"],
                "constraints": ["Must be secure"]
            }
            
            result = await agent._design_architecture(requirements)
            
            # Check that the agent was called
            mock_designer.execute.assert_called_once()
            
            # Check that the result has the expected format
            assert result["summary"] == "Microservices architecture"
            assert result["backend"] == "Flask"
            assert len(result["components"]) == 1
    
    @pytest.mark.asyncio
    async def test_execute_success(self, mock_llm, mock_memory_manager):
        """Test the execute method with successful execution."""
        agent = ManagerAgent(
            name="test_manager",
            memory_manager=mock_memory_manager,
            llm=mock_llm
        )
        
        # Mock all the individual steps
        with patch.object(agent, '_analyze_requirements') as mock_analyze, \
             patch.object(agent, '_design_architecture') as mock_design, \
             patch.object(agent, '_research_libraries') as mock_research, \
             patch.object(agent, '_plan_software') as mock_plan, \
             patch.object(agent, '_generate_code') as mock_generate, \
             patch.object(agent, '_debug_code') as mock_debug, \
             patch.object(agent, '_analyze_dependencies') as mock_dependencies, \
             patch.object(agent, '_create_final_summary') as mock_summary:
            
            # Set up the return values for all the mocks
            mock_analyze.return_value = {"prompt": "Test", "extracted_requirements": ["Requirement"]}
            mock_design.return_value = {"summary": "Architecture"}
            mock_research.return_value = {"selected_libraries": ["Library"]}
            mock_plan.return_value = {"summary": "Plan"}
            mock_generate.return_value = {"files": {"file.py": "code"}}
            mock_debug.return_value = {"status": "Passed"}
            mock_dependencies.return_value = {"status": "Compatible"}
            mock_summary.return_value = {"summary": "Final summary"}
            
            # Execute the agent
            result = await agent.execute("Create a web application")
            
            # Check that all the methods were called
            mock_analyze.assert_called_once()
            mock_design.assert_called_once()
            mock_research.assert_called_once()
            mock_plan.assert_called_once()
            mock_generate.assert_called_once()
            mock_debug.assert_called_once()
            mock_dependencies.assert_called_once()
            mock_summary.assert_called_once()
            
            # Check that the result has the expected format
            assert result["success"] == True
            assert result["result"]["summary"] == "Final summary"
    
    @pytest.mark.asyncio
    async def test_execute_with_error(self, mock_llm, mock_memory_manager):
        """Test the execute method with an error."""
        agent = ManagerAgent(
            name="test_manager",
            memory_manager=mock_memory_manager,
            llm=mock_llm
        )
        
        # Mock the _analyze_requirements method to raise an exception
        with patch.object(agent, '_analyze_requirements', side_effect=Exception("Test error")):
            # Execute the agent
            result = await agent.execute("Create a web application")
            
            # Check that the result indicates failure
            assert result["success"] == False
            assert "error" in result
            assert "Test error" in result["error"]
    
    def test_get_or_create_agent(self, mock_llm, mock_memory_manager):
        """Test the _get_or_create_agent method."""
        from src.agents.architecture_designer_agent import ArchitectureDesignerAgent
        
        agent = ManagerAgent(
            name="test_manager",
            memory_manager=mock_memory_manager,
            llm=mock_llm
        )
        
        # Get an agent
        designer = agent._get_or_create_agent("architecture_designer", ArchitectureDesignerAgent)
        
        # Check that the agent was created correctly
        assert isinstance(designer, ArchitectureDesignerAgent)
        assert designer.llm == mock_llm
        assert designer.memory_manager == mock_memory_manager
        
        # Check that the agent is cached
        assert "architecture_designer" in agent.specialized_agents
        
        # Get the same agent again
        designer2 = agent._get_or_create_agent("architecture_designer", ArchitectureDesignerAgent)
        
        # Check that we got the same instance
        assert designer2 is designer