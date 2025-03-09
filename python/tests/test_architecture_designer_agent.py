import pytest
import asyncio
import json
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Dict, Any, List

from src.agents.architecture_designer_agent import ArchitectureDesignerAgent, Component, ArchitectureDesign
from conftest import MockLLM, MockMemoryManager


class TestArchitectureDesignerAgent:
    """Tests for the ArchitectureDesignerAgent class."""
    
    def test_initialization(self, mock_llm, mock_memory_manager):
        """Test agent initialization."""
        agent = ArchitectureDesignerAgent(
            name="test_architecture_designer",
            memory_manager=mock_memory_manager,
            config={"test_key": "test_value"},
            llm=mock_llm
        )
        
        # Check that the agent was initialized correctly
        assert agent.name == "test_architecture_designer"
        assert agent.memory_manager == mock_memory_manager
        assert agent.config["test_key"] == "test_value"
        assert agent.llm == mock_llm
        assert len(agent.tools) > 0  # Should have created architecture tools
    
    def test_architecture_design_schema(self):
        """Test the architecture design schema."""
        # Create a valid component
        component = Component(
            name="API Gateway",
            technology="Express",
            responsibility="Routing"
        )
        
        assert component.name == "API Gateway"
        assert component.technology == "Express"
        assert component.responsibility == "Routing"
        
        # Create a valid architecture design
        architecture = ArchitectureDesign(
            summary="Microservices architecture",
            backend="Node.js and Python",
            frontend="React",
            database="PostgreSQL",
            deployment="Docker",
            components=[component],
            rationale="Scalable and modular design",
            messaging="RabbitMQ"
        )
        
        assert architecture.summary == "Microservices architecture"
        assert architecture.backend == "Node.js and Python"
        assert architecture.frontend == "React"
        assert architecture.database == "PostgreSQL"
        assert architecture.deployment == "Docker"
        assert len(architecture.components) == 1
        assert architecture.components[0].name == "API Gateway"
        assert architecture.rationale == "Scalable and modular design"
        assert architecture.messaging == "RabbitMQ"
    
    def test_get_agent_system_message(self, mock_memory_manager):
        """Test the _get_agent_system_message method."""
        agent = ArchitectureDesignerAgent(
            name="test_architecture_designer",
            memory_manager=mock_memory_manager
        )
        
        # Get the system message
        system_message = agent._get_agent_system_message()
        
        # Check that the system message contains expected text
        assert "Architecture Designer Agent" in system_message
        assert "analyze requirements" in system_message.lower()
        assert "design" in system_message.lower()
    
    def test_create_architecture_tools(self, mock_llm, mock_memory_manager):
        """Test the _create_architecture_tools method."""
        agent = ArchitectureDesignerAgent(
            name="test_architecture_designer",
            memory_manager=mock_memory_manager,
            llm=mock_llm
        )
        
        # Create architecture tools
        tools = agent._create_architecture_tools()
        
        # Check that the tools were created correctly
        assert len(tools) == 2
        assert tools[0].name == "design_architecture"
        assert tools[1].name == "evaluate_architecture"
        
        # Check that the tools have the correct metadata
        assert "Design a complete software architecture" in tools[0].description
        assert "Evaluate an architecture design" in tools[1].description
    
    @pytest.mark.asyncio
    async def test_execute_success(self, mock_llm, mock_memory_manager):
        """Test the execute method with successful execution."""
        agent = ArchitectureDesignerAgent(
            name="test_architecture_designer",
            memory_manager=mock_memory_manager,
            llm=mock_llm
        )
        
        # Create a mock super().execute that returns a successful result
        with patch('src.agents.base_agent.BaseAgent.execute') as mock_execute:
            # Create a mock response with JSON in it
            mock_execute.return_value = {
                "success": True,
                "data": """```json
                {
                    "summary": "Microservices architecture",
                    "backend": "Node.js and Python",
                    "frontend": "React",
                    "database": "PostgreSQL",
                    "deployment": "Docker",
                    "components": [
                        {
                            "name": "API Gateway",
                            "technology": "Express",
                            "responsibility": "Routing"
                        }
                    ],
                    "rationale": "Scalable and modular design"
                }
                ```"""
            }
            
            # Execute the agent
            result = await agent.execute("Design a microservices architecture for an e-commerce application")
            
            # Check that the super().execute method was called
            mock_execute.assert_called_once()
            
            # Check that the result has the expected format
            assert result["success"] == True
            assert "design" in result
            assert result["design"]["summary"] == "Microservices architecture"
            assert result["design"]["backend"] == "Node.js and Python"
            assert len(result["design"]["components"]) == 1
    
    @pytest.mark.asyncio
    async def test_execute_with_direct_tool_use(self, mock_llm, mock_memory_manager):
        """Test the execute method with direct tool use."""
        agent = ArchitectureDesignerAgent(
            name="test_architecture_designer",
            memory_manager=mock_memory_manager,
            llm=mock_llm
        )
        
        # Mock the parent execute method to return a result without JSON
        with patch('src.agents.base_agent.BaseAgent.execute') as mock_execute:
            mock_execute.return_value = {
                "success": True,
                "data": "I'll design an architecture for you!"
            }
            
            # Mock the design_architecture tool
            mock_design_tool = MagicMock()
            mock_design_tool.invoke = AsyncMock(return_value=json.dumps({
                "summary": "Microservices architecture",
                "backend": "Node.js and Python",
                "frontend": "React",
                "database": "PostgreSQL",
                "deployment": "Docker",
                "components": [
                    {
                        "name": "API Gateway",
                        "technology": "Express",
                        "responsibility": "Routing"
                    }
                ],
                "rationale": "Scalable and modular design"
            }))
            
            # Replace the first tool with our mock
            agent.tools[0] = mock_design_tool
            
            # Execute the agent
            result = await agent.execute("Design a microservices architecture for an e-commerce application")
            
            # Check that the tool was invoked
            mock_design_tool.invoke.assert_called_once()
            
            # Check that the result has the expected format
            assert result["success"] == True
            assert "design" in result
            assert result["design"]["summary"] == "Microservices architecture"
    
    @pytest.mark.asyncio
    async def test_execute_with_error(self, mock_llm, mock_memory_manager):
        """Test the execute method with an error."""
        agent = ArchitectureDesignerAgent(
            name="test_architecture_designer",
            memory_manager=mock_memory_manager,
            llm=mock_llm
        )
        
        # Mock the parent execute method to return an error
        with patch('src.agents.base_agent.BaseAgent.execute') as mock_execute:
            mock_execute.return_value = {
                "success": False,
                "error": "Test error"
            }
            
            # Execute the agent
            result = await agent.execute("Design a microservices architecture for an e-commerce application")
            
            # Check that the result indicates failure
            assert result["success"] == False
            assert "error" in result
            assert result["error"] == "Test error"