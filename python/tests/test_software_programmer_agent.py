import pytest
import asyncio
import json
import os
from unittest.mock import patch, MagicMock, AsyncMock, mock_open
from typing import Dict, Any, List

from src.agents.software_programmer_agent import SoftwareProgrammerAgent
from src.utils.file_operations import FileOperations
from conftest import MockLLM, MockMemoryManager


class TestSoftwareProgrammerAgent:
    """Tests for the SoftwareProgrammerAgent class."""
    
    def test_initialization(self, mock_llm, mock_memory_manager):
        """Test agent initialization."""
        agent = SoftwareProgrammerAgent(
            name="test_programmer",
            memory_manager=mock_memory_manager,
            config={"test_key": "test_value"},
            llm=mock_llm
        )
        
        # Check that the agent was initialized correctly
        assert agent.name == "test_programmer"
        assert agent.memory_manager == mock_memory_manager
        assert agent.config["test_key"] == "test_value"
        assert agent.llm == mock_llm
        
        # Check that tools were created
        assert len(agent.tools) > 0
        tool_names = [tool.name for tool in agent.tools]
        
        # Should have file operation tools
        assert any("file" in name.lower() or "read" in name.lower() or "write" in name.lower() for name in tool_names)
    
    def test_get_agent_system_message(self, mock_memory_manager):
        """Test the _get_agent_system_message method."""
        agent = SoftwareProgrammerAgent(
            name="test_programmer",
            memory_manager=mock_memory_manager
        )
        
        # Get the system message
        system_message = agent._get_agent_system_message()
        
        # Check that the system message contains expected text
        assert "Software Programmer" in system_message
        assert "code" in system_message.lower()
        assert "implement" in system_message.lower()
        
        # Check that it mentions key responsibilities
        assert "write" in system_message.lower()
        assert "generate" in system_message.lower()
        assert "best practices" in system_message.lower()
    
    @pytest.mark.asyncio
    async def test_execute_success(self, mock_llm, mock_memory_manager):
        """Test the execute method with successful execution."""
        agent = SoftwareProgrammerAgent(
            name="test_programmer",
            memory_manager=mock_memory_manager,
            llm=mock_llm
        )
        
        # Mock the agent executor
        mock_executor_result = {
            "output": json.dumps({
                "files": {
                    "app.py": "from flask import Flask\n\napp = Flask(__name__)\n\n@app.route('/')\ndef hello_world():\n    return 'Hello, World!'\n",
                    "requirements.txt": "flask==2.0.1\n"
                },
                "explanation": "This is a simple Flask application with a single route that returns 'Hello, World!'.",
                "next_steps": "You can run this application using 'flask run' after installing the requirements."
            })
        }
        
        with patch.object(agent, 'agent_executor') as mock_executor:
            mock_executor.invoke = AsyncMock(return_value=mock_executor_result)
            
            # Execute the agent
            result = await agent.execute("Create a basic Flask application with a single route")
            
            # Check that the agent executor was called
            mock_executor.invoke.assert_called_once()
            
            # Check that the result has the expected format
            assert result["success"] == True
            assert len(result["code"]["files"]) == 2
            assert "app.py" in result["code"]["files"]
            assert "requirements.txt" in result["code"]["files"]
            assert "explanation" in result["code"]
            assert "next_steps" in result["code"]
    
    @pytest.mark.asyncio
    async def test_execute_failure(self, mock_llm, mock_memory_manager):
        """Test the execute method with execution failure."""
        agent = SoftwareProgrammerAgent(
            name="test_programmer",
            memory_manager=mock_memory_manager,
            llm=mock_llm
        )
        
        # Mock the agent executor to raise an exception
        with patch.object(agent, 'agent_executor') as mock_executor:
            mock_executor.invoke = AsyncMock(side_effect=Exception("Test error"))
            
            # Execute the agent
            result = await agent.execute("Create a basic Flask application")
            
            # Check that the agent executor was called
            mock_executor.invoke.assert_called_once()
            
            # Check that the result indicates failure
            assert result["success"] == False
            assert "error" in result
            assert "Test error" in result["error"]
    
    @pytest.mark.asyncio
    async def test_execute_with_file_operations(self, mock_llm, mock_memory_manager):
        """Test the execute method with file operations."""
        agent = SoftwareProgrammerAgent(
            name="test_programmer",
            memory_manager=mock_memory_manager,
            llm=mock_llm
        )
        
        # Mock FileOperations.write_file
        with patch.object(FileOperations, 'write_file') as mock_write_file:
            mock_write_file.return_value = True
            
            # Mock the agent executor
            mock_executor_result = {
                "output": json.dumps({
                    "files": {
                        "app.py": "print('Hello, World!')",
                        "utils.py": "def greet(name):\n    return f'Hello, {name}!'"
                    }
                })
            }
            
            with patch.object(agent, 'agent_executor') as mock_executor:
                mock_executor.invoke = AsyncMock(return_value=mock_executor_result)
                
                # Execute the agent with save_files=True
                result = await agent.execute("Create a Python script that prints 'Hello, World!'", save_files=True)
                
                # Check that the agent executor was called
                mock_executor.invoke.assert_called_once()
                
                # Check that write_file was called for each file
                assert mock_write_file.call_count == 2
                
                # Check the result
                assert result["success"] == True
                assert "app.py" in result["code"]["files"]
                assert "utils.py" in result["code"]["files"]
    
    @pytest.mark.asyncio
    async def test_execute_with_existing_code_reading(self, mock_llm, mock_memory_manager):
        """Test the execute method with reading existing code."""
        agent = SoftwareProgrammerAgent(
            name="test_programmer",
            memory_manager=mock_memory_manager,
            llm=mock_llm
        )
        
        # Mock FileOperations.read_file
        with patch.object(FileOperations, 'read_file') as mock_read_file:
            mock_read_file.return_value = "def existing_function():\n    return 'This is an existing function.'"
            
            # Mock os.path.exists
            with patch.object(os.path, 'exists') as mock_exists:
                mock_exists.return_value = True
                
                # Mock the agent executor
                mock_executor_result = {
                    "output": json.dumps({
                        "files": {
                            "main.py": "from utils import existing_function\n\nprint(existing_function())"
                        }
                    })
                }
                
                with patch.object(agent, 'agent_executor') as mock_executor:
                    mock_executor.invoke = AsyncMock(return_value=mock_executor_result)
                    
                    # Execute the agent with existing_code parameter
                    result = await agent.execute(
                        "Create a script that uses the existing function",
                        existing_code={"utils.py": "path/to/utils.py"}
                    )
                    
                    # Check that read_file was called
                    mock_read_file.assert_called_with("path/to/utils.py")
                    
                    # Check the result
                    assert result["success"] == True
                    assert "main.py" in result["code"]["files"]