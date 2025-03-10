#!/usr/bin/env python3
import argparse
import asyncio
import os
import sys
from loguru import logger
from typing import Optional

from utils.logging_setup import setup_logging, get_log_file_path
from utils.memory_manager import MemoryManager
from utils.env_loader import load_env_file, get_env
from agents.manager_agent import ManagerAgent

# Load environment variables from .env file
load_env_file()


async def main(prompt: str, log_level: str = "INFO", 
               persist_memory: bool = False, memory_dir: str = "./memory",
               log_to_file: bool = False, dashboard_mode: bool = False) -> None:
    """Main entry point for the application.
    
    Args:
        prompt: The user input prompt
        log_level: Logging level to use
        persist_memory: Whether to persist memory to disk
        memory_dir: Directory for persistent memory storage
        log_to_file: Whether to log to a file
        dashboard_mode: Whether to run in dashboard mode
    """
    # Set up logging
    log_file = get_log_file_path() if log_to_file else None
    setup_logging(log_file, log_level)
    
    # Print banner
    print("\n" + "=" * 60)
    print(" ClaudeAgents - Multi-agent Collaborative Development System ")
    print("=" * 60 + "\n")
    
    # Initialize memory manager
    memory_manager = MemoryManager(persist_to_disk=persist_memory, storage_dir=memory_dir)
    
    try:
        # Initialize the manager agent with dashboard mode if specified
        manager = ManagerAgent(
            name="Manager", 
            memory_manager=memory_manager,
            dashboard_mode=dashboard_mode
        )
        
        # Execute the manager agent with the prompt
        logger.info(f"Starting execution with prompt: {prompt[:100]}...")
        result = await manager.execute(prompt)
        
        if result["success"]:
            logger.info("Execution completed successfully")
        else:
            logger.error(f"Execution failed: {result.get('error', 'Unknown error')}")
            
    except KeyboardInterrupt:
        logger.warning("Execution interrupted by user")
        print("\nExecution interrupted by user.")
    except Exception as e:
        logger.exception(f"Unhandled exception: {str(e)}")
        print(f"\nError: {str(e)}")
        return


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ClaudeAgents - Multi-agent Collaborative Development System")
    parser.add_argument("prompt", nargs="?", help="The task prompt")
    parser.add_argument("--prompt-file", "-f", help="File containing the task prompt")
    parser.add_argument("--log-level", "-l", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                       default="INFO", help="Set the logging level")
    parser.add_argument("--persist-memory", "-p", action="store_true", 
                        help="Persist memory to disk")
    parser.add_argument("--memory-dir", "-m", default="./memory",
                       help="Directory for persistent memory storage")
    parser.add_argument("--log-to-file", "-o", action="store_true",
                        help="Log to file")
    parser.add_argument("--dashboard-mode", action="store_true",
                        help="Run in dashboard mode with UI updates")
    
    args = parser.parse_args()
    
    # Get prompt from arguments or file
    prompt: Optional[str] = None
    if args.prompt:
        prompt = args.prompt
    elif args.prompt_file:
        try:
            with open(args.prompt_file, 'r') as f:
                prompt = f.read().strip()
        except Exception as e:
            print(f"Error reading prompt file: {str(e)}")
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)
    
    asyncio.run(main(
        prompt=prompt,
        log_level=args.log_level,
        persist_memory=args.persist_memory,
        memory_dir=args.memory_dir,
        log_to_file=args.log_to_file,
        dashboard_mode=args.dashboard_mode
    ))