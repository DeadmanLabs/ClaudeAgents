import pytest
import asyncio
from unittest.mock import patch, MagicMock
import json
from typing import Dict, Any

from src.agents.base_agent import BaseAgent
from conftest import MockLLM, MockMemoryManager


class TestAgent(BaseAgent):
    """Concrete implementation of BaseAgent for testing."""
    
    async def execute(self, prompt: str, **kwargs):
        """Execute the agent's task."""
        # Use the parent class implementation
        return await super().execute(prompt, **kwargs)


class TestBaseAgent:
    """Tests for the BaseAgent class."""
    
    def test_initialization(self, mock_llm, mock_memory_manager):
        """Test agent initialization."""
        agent = TestAgent(
            name="test_agent",
            memory_manager=mock_memory_manager,
            config={"test_key": "test_value"},
            llm=mock_llm
        )
        
        # Check that the agent was initialized correctly
        assert agent.name == "test_agent"
        assert agent.memory_manager == mock_memory_manager
        assert agent.config["test_key"] == "test_value"
        assert agent.llm == mock_llm
        assert agent.conversation_history == []
        assert agent.tools == []
        
    def test_save_and_retrieve_from_memory(self, mock_memory_manager):
        """Test saving and retrieving data from memory."""
        agent = TestAgent(name="test_agent", memory_manager=mock_memory_manager)
        
        # Save data to memory
        agent.save_to_memory("test_key", "test_value")
        
        # Retrieve data from memory
        value = agent.retrieve_from_memory("test_key")
        
        # Check that the data was saved and retrieved correctly
        assert value == "test_value"
        
    def test_add_to_conversation(self, mock_memory_manager):
        """Test adding messages to the conversation history."""
        agent = TestAgent(name="test_agent", memory_manager=mock_memory_manager)
        
        # Add messages to the conversation
        agent.add_to_conversation("user", "Hello")
        agent.add_to_conversation("assistant", "Hi there")
        agent.add_to_conversation("system", "Test system message")
        
        # Check that the messages were added correctly
        assert len(agent.conversation_history) == 3
        assert agent.conversation_history[0] == {"role": "user", "content": "Hello"}
        assert agent.conversation_history[1] == {"role": "assistant", "content": "Hi there"}
        assert agent.conversation_history[2] == {"role": "system", "content": "Test system message"}
        
    @pytest.mark.asyncio
    async def test_execute(self, mock_llm, mock_memory_manager):
        """Test the execute method."""
        agent = TestAgent(
            name="test_agent",
            memory_manager=mock_memory_manager,
            config={"test_key": "test_value"},
            llm=mock_llm
        )
        
        # Execute the agent
        result = await agent.execute("Test prompt")
        
        # Check that the result has the expected format
        assert "success" in result
        assert result["success"] == True
        assert "data" in result
        
        # Check that the conversation history was updated
        assert len(agent.conversation_history) == 2
        assert agent.conversation_history[0]["role"] == "user"
        assert agent.conversation_history[0]["content"] == "Test prompt"
        assert agent.conversation_history[1]["role"] == "assistant"
    
    @pytest.mark.asyncio
    async def test_execute_with_error(self, mock_llm, mock_memory_manager):
        """Test the execute method with an error."""
        agent = TestAgent(
            name="test_agent",
            memory_manager=mock_memory_manager,
            config={"test_key": "test_value"},
            llm=mock_llm
        )
        
        # Create a mock agent_executor that raises an exception
        agent.agent_executor = MagicMock()
        agent.agent_executor.invoke = MagicMock(side_effect=Exception("Test error"))
        
        # Execute the agent
        result = await agent.execute("Test prompt")
        
        # Check that the result indicates failure
        assert "success" in result
        assert result["success"] == False
        assert "error" in result
        assert "Test error" in result["error"]
    
    def test_get_agent_system_message(self):
        """Test the _get_agent_system_message method."""
        agent = TestAgent(name="test_agent")
        
        # Get the system message
        system_message = agent._get_agent_system_message()
        
        # Check that the system message contains the agent's name
        assert "test_agent" in system_message
        
    def test_create_agent_executor(self, mock_llm):
        """Test the _create_agent_executor method."""
        agent = TestAgent(
            name="test_agent",
            llm=mock_llm,
            tools=[]
        )
        
        # Create the agent executor
        executor = agent._create_agent_executor()
        
        # Check that the executor was created correctly
        assert hasattr(executor, "agent")
        assert hasattr(executor, "tools")
        assert hasattr(executor, "memory")