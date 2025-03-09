import pytest
import asyncio
import json
import os
from unittest.mock import patch, MagicMock, AsyncMock, mock_open
from typing import Dict, Any, List

from src.agents.exception_debugger_agent import ExceptionDebuggerAgent
from src.utils.file_operations import FileOperations
from src.utils.shell_executor import ShellExecutor
from conftest import MockLLM, MockMemoryManager


class TestExceptionDebuggerAgent:
    """Tests for the ExceptionDebuggerAgent class."""
    
    def test_initialization(self, mock_llm, mock_memory_manager):
        """Test agent initialization."""
        agent = ExceptionDebuggerAgent(
            name="test_debugger",
            memory_manager=mock_memory_manager,
            config={"test_key": "test_value"},
            llm=mock_llm
        )
        
        # Check that the agent was initialized correctly
        assert agent.name == "test_debugger"
        assert agent.memory_manager == mock_memory_manager
        assert agent.config["test_key"] == "test_value"
        assert agent.llm == mock_llm
        
        # Check that tools were created
        assert len(agent.tools) > 0
        tool_names = [tool.name for tool in agent.tools]
        
        # Should have debugging-related tools
        assert any("shell" in name.lower() or "execute" in name.lower() for name in tool_names)
        assert any("file" in name.lower() or "read" in name.lower() or "write" in name.lower() for name in tool_names)
    
    def test_get_agent_system_message(self, mock_memory_manager):
        """Test the _get_agent_system_message method."""
        agent = ExceptionDebuggerAgent(
            name="test_debugger",
            memory_manager=mock_memory_manager
        )
        
        # Get the system message
        system_message = agent._get_agent_system_message()
        
        # Check that the system message contains expected text
        assert "Exception Debugger" in system_message
        assert "debug" in system_message.lower()
        assert "exception" in system_message.lower()
        
        # Check that it mentions key responsibilities
        assert "identify" in system_message.lower()
        assert "fix" in system_message.lower()
        assert "test" in system_message.lower()
    
    @pytest.mark.asyncio
    async def test_execute_success(self, mock_llm, mock_memory_manager):
        """Test the execute method with successful execution."""
        agent = ExceptionDebuggerAgent(
            name="test_debugger",
            memory_manager=mock_memory_manager,
            llm=mock_llm
        )
        
        # Mock the agent executor
        mock_executor_result = {
            "output": json.dumps({
                "status": "success",
                "issues_found": [
                    {
                        "file": "app.py",
                        "line": 5,
                        "description": "Missing parenthesis in function call",
                        "fix": "Added missing parenthesis"
                    }
                ],
                "fixes_applied": [
                    {
                        "file": "app.py",
                        "original": "print 'Hello, World!'",
                        "fixed": "print('Hello, World!')"
                    }
                ],
                "tests_run": [
                    {
                        "command": "python app.py",
                        "result": "success",
                        "output": "Hello, World!"
                    }
                ],
                "summary": "Fixed a syntax error in app.py. The code now runs successfully."
            })
        }
        
        with patch.object(agent, 'agent_executor') as mock_executor:
            mock_executor.invoke = AsyncMock(return_value=mock_executor_result)
            
            # Execute the agent
            result = await agent.execute("Debug the Python script in app.py")
            
            # Check that the agent executor was called
            mock_executor.invoke.assert_called_once()
            
            # Check that the result has the expected format
            assert result["success"] == True
            assert result["debug_result"]["status"] == "success"
            assert len(result["debug_result"]["issues_found"]) == 1
            assert result["debug_result"]["issues_found"][0]["file"] == "app.py"
            assert len(result["debug_result"]["fixes_applied"]) == 1
            assert len(result["debug_result"]["tests_run"]) == 1
    
    @pytest.mark.asyncio
    async def test_execute_failure(self, mock_llm, mock_memory_manager):
        """Test the execute method with execution failure."""
        agent = ExceptionDebuggerAgent(
            name="test_debugger",
            memory_manager=mock_memory_manager,
            llm=mock_llm
        )
        
        # Mock the agent executor to raise an exception
        with patch.object(agent, 'agent_executor') as mock_executor:
            mock_executor.invoke = AsyncMock(side_effect=Exception("Test error"))
            
            # Execute the agent
            result = await agent.execute("Debug the Python script")
            
            # Check that the agent executor was called
            mock_executor.invoke.assert_called_once()
            
            # Check that the result indicates failure
            assert result["success"] == False
            assert "error" in result
            assert "Test error" in result["error"]
    
    @pytest.mark.asyncio
    async def test_execute_with_shell_commands(self, mock_llm, mock_memory_manager):
        """Test the execute method with shell command execution."""
        agent = ExceptionDebuggerAgent(
            name="test_debugger",
            memory_manager=mock_memory_manager,
            llm=mock_llm
        )
        
        # Mock ShellExecutor.run_async
        mock_shell_result = {
            "success": False,
            "return_code": 1,
            "stdout": "",
            "stderr": "SyntaxError: Missing parentheses in call to 'print'",
            "command": "python app.py"
        }
        
        with patch.object(ShellExecutor, 'run_async') as mock_run_async:
            # First call fails, second call succeeds
            mock_run_async.side_effect = [
                mock_shell_result,
                {
                    "success": True,
                    "return_code": 0,
                    "stdout": "Hello, World!",
                    "stderr": "",
                    "command": "python app.py"
                }
            ]
            
            # Mock FileOperations for reading and writing files
            with patch.object(FileOperations, 'read_file') as mock_read_file, \
                 patch.object(FileOperations, 'write_file') as mock_write_file:
                
                mock_read_file.return_value = "print 'Hello, World!'"
                mock_write_file.return_value = True
                
                # Mock the agent executor
                mock_executor_result = {
                    "output": json.dumps({
                        "status": "success",
                        "issues_found": [
                            {
                                "file": "app.py",
                                "description": "Missing parenthesis in function call",
                                "fix": "Added missing parenthesis"
                            }
                        ],
                        "fixes_applied": [
                            {
                                "file": "app.py",
                                "original": "print 'Hello, World!'",
                                "fixed": "print('Hello, World!')"
                            }
                        ],
                        "tests_run": [
                            {
                                "command": "python app.py",
                                "result": "success",
                                "output": "Hello, World!"
                            }
                        ]
                    })
                }
                
                with patch.object(agent, 'agent_executor') as mock_executor:
                    mock_executor.invoke = AsyncMock(return_value=mock_executor_result)
                    
                    # Execute the agent with code parameter
                    code = {
                        "files": {
                            "app.py": "print 'Hello, World!'"
                        }
                    }
                    
                    result = await agent.execute("Debug the Python script", code=code)
                    
                    # Check that file operations were called
                    mock_read_file.assert_called()
                    mock_write_file.assert_called()
                    
                    # Check that shell commands were executed
                    assert mock_run_async.call_count == 2
                    
                    # Check the result
                    assert result["success"] == True
                    assert result["debug_result"]["status"] == "success"
                    assert len(result["debug_result"]["issues_found"]) == 1
    
    @pytest.mark.asyncio
    async def test_execute_with_retries(self, mock_llm, mock_memory_manager):
        """Test the execute method with retries."""
        agent = ExceptionDebuggerAgent(
            name="test_debugger",
            memory_manager=mock_memory_manager,
            llm=mock_llm
        )
        
        # Set up multiple iterations of debugging
        with patch.object(agent, 'agent_executor') as mock_executor:
            # First call reports issues but not success
            first_result = {
                "output": json.dumps({
                    "status": "in_progress",
                    "issues_found": [
                        {
                            "file": "app.py",
                            "description": "Missing parenthesis in function call"
                        }
                    ],
                    "fixes_applied": [
                        {
                            "file": "app.py",
                            "original": "print 'Hello, World!'",
                            "fixed": "print('Hello, World!')"
                        }
                    ],
                    "tests_run": [
                        {
                            "command": "python app.py",
                            "result": "failure",
                            "output": "IndentationError: unexpected indent"
                        }
                    ],
                    "needs_more_fixes": True
                })
            }
            
            # Second call reports success
            second_result = {
                "output": json.dumps({
                    "status": "success",
                    "issues_found": [
                        {
                            "file": "app.py",
                            "description": "Unexpected indentation"
                        }
                    ],
                    "fixes_applied": [
                        {
                            "file": "app.py",
                            "original": "  print('Hello, World!')",
                            "fixed": "print('Hello, World!')"
                        }
                    ],
                    "tests_run": [
                        {
                            "command": "python app.py",
                            "result": "success",
                            "output": "Hello, World!"
                        }
                    ],
                    "needs_more_fixes": False
                })
            }
            
            # Set up the mock to return different values on successive calls
            mock_executor.invoke = AsyncMock(side_effect=[first_result, second_result])
            
            # Mock the retry logic in the agent
            with patch.object(agent, '_should_retry_debugging') as mock_should_retry:
                mock_should_retry.side_effect = [True, False]
                
                # Execute the agent
                result = await agent.execute("Debug the Python script with multiple issues")
                
                # Check that the agent executor was called twice
                assert mock_executor.invoke.call_count == 2
                
                # Check that _should_retry_debugging was called
                assert mock_should_retry.call_count == 2
                
                # Check the result
                assert result["success"] == True
                assert result["debug_result"]["status"] == "success"