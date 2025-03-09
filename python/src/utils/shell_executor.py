import os
import subprocess
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Union
from loguru import logger

from langchain_core.callbacks.manager import CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from langchain.tools import tool


class ShellExecutor:
    """Utility for executing shell commands.
    
    This class provides methods for running shell commands synchronously
    and asynchronously, with support for timeouts and error handling.
    """
    
    @staticmethod
    async def run_async(
        command: str, 
        timeout: Optional[int] = None, 
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        shell: bool = True
    ) -> Dict[str, Any]:
        """Run a shell command asynchronously.
        
        Args:
            command: The command to execute
            timeout: Optional timeout in seconds
            cwd: Optional working directory for the command
            env: Optional environment variables
            shell: Whether to run through the shell
            
        Returns:
            Dictionary with command output details
        """
        logger.info(f"Executing command: {command}")
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Create subprocess
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=env if env else os.environ,
                shell=shell
            )
            
            # Wait for the command to complete with timeout
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), 
                timeout=timeout
            )
            
            end_time = asyncio.get_event_loop().time()
            duration = end_time - start_time
            
            stdout_str = stdout.decode('utf-8', errors='replace')
            stderr_str = stderr.decode('utf-8', errors='replace')
            
            logger.debug(f"Command completed in {duration:.2f}s with return code {process.returncode}")
            
            if process.returncode != 0:
                logger.warning(f"Command exited with non-zero code: {process.returncode}")
                logger.debug(f"stderr: {stderr_str}")
            
            return {
                "success": process.returncode == 0,
                "return_code": process.returncode,
                "stdout": stdout_str,
                "stderr": stderr_str,
                "duration": duration,
                "command": command
            }
            
        except asyncio.TimeoutError:
            logger.error(f"Command timed out after {timeout}s: {command}")
            return {
                "success": False,
                "return_code": None,
                "stdout": "",
                "stderr": "Command execution timed out",
                "duration": asyncio.get_event_loop().time() - start_time,
                "command": command,
                "error": "timeout"
            }
        except Exception as e:
            logger.error(f"Error executing command: {str(e)}")
            return {
                "success": False,
                "return_code": None,
                "stdout": "",
                "stderr": str(e),
                "duration": asyncio.get_event_loop().time() - start_time,
                "command": command,
                "error": "execution_error"
            }
    
    @staticmethod
    def run(
        command: str, 
        timeout: Optional[int] = None, 
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        shell: bool = True
    ) -> Dict[str, Any]:
        """Run a shell command synchronously.
        
        Args:
            command: The command to execute
            timeout: Optional timeout in seconds
            cwd: Optional working directory for the command
            env: Optional environment variables
            shell: Whether to run through the shell
            
        Returns:
            Dictionary with command output details
        """
        logger.info(f"Executing command synchronously: {command}")
        
        try:
            # Execute the command
            process = subprocess.run(
                command,
                shell=shell,
                cwd=cwd,
                env=env if env else os.environ,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            logger.debug(f"Command completed with return code {process.returncode}")
            
            if process.returncode != 0:
                logger.warning(f"Command exited with non-zero code: {process.returncode}")
                logger.debug(f"stderr: {process.stderr}")
            
            return {
                "success": process.returncode == 0,
                "return_code": process.returncode,
                "stdout": process.stdout,
                "stderr": process.stderr,
                "command": command
            }
            
        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out after {timeout}s: {command}")
            return {
                "success": False,
                "return_code": None,
                "stdout": "",
                "stderr": "Command execution timed out",
                "command": command,
                "error": "timeout"
            }
        except Exception as e:
            logger.error(f"Error executing command: {str(e)}")
            return {
                "success": False,
                "return_code": None,
                "stdout": "",
                "stderr": str(e),
                "command": command,
                "error": "execution_error"
            }


class ShellExecutorTool(BaseTool):
    """Tool for executing shell commands with LangChain."""
    
    name: str = "shell_executor"
    description: str = "Execute shell commands on the local system"
    
    def __init__(self):
        """Initialize the shell executor tool."""
        super().__init__()
        self.shell_executor = ShellExecutor()
        
    async def _arun(self, command: str, timeout: Optional[int] = None, 
                   cwd: Optional[str] = None,
                   run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Run the shell command asynchronously.
        
        Args:
            command: The command to execute
            timeout: Optional timeout in seconds
            cwd: Optional working directory
            run_manager: Optional callback manager
            
        Returns:
            Command execution results as a string
        """
        if run_manager:
            await run_manager.on_text("Executing shell command: " + command)
            
        result = await self.shell_executor.run_async(command, timeout, cwd)
        
        # Format the result for easier readability by the LLM
        output = (
            f"Command: {command}\n"
            f"Success: {result['success']}\n"
            f"Return Code: {result['return_code']}\n\n"
            f"STDOUT:\n{result['stdout']}\n\n"
            f"STDERR:\n{result['stderr']}\n"
        )
        
        return output


@tool
def execute_shell(command: str, timeout: Optional[int] = None, cwd: Optional[str] = None) -> str:
    """
    Execute a shell command on the local system.
    
    Args:
        command: The command to execute
        timeout: Optional timeout in seconds
        cwd: Optional working directory
        
    Returns:
        Command execution results
    """
    # Create a synchronous wrapper for the shell executor
    shell_executor = ShellExecutor()
    
    # Use the event loop to run the async function
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(shell_executor.run_async(command, timeout, cwd))
    
    # Format the result
    output = (
        f"Command: {command}\n"
        f"Success: {result['success']}\n"
        f"Return Code: {result['return_code']}\n\n"
        f"STDOUT:\n{result['stdout']}\n\n"
        f"STDERR:\n{result['stderr']}\n"
    )
    
    return output