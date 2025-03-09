#!/usr/bin/env python3
"""
Example script demonstrating how to use ClaudeAgents to build a complete software solution.

This example shows how to:
1. Set up and configure the manager agent
2. Execute a complex development task using all agent types
3. Process and display the results
"""

import os
import asyncio
import json
from loguru import logger

from claude_agents.utils.logging_setup import setup_logging
from claude_agents.utils.memory_manager import MemoryManager
from claude_agents.agents.manager_agent import ManagerAgent


async def run_example():
    """Run a complete example using all agent types."""
    # Setup logging
    setup_logging(log_file="logs/example.log", log_level="INFO")
    
    # Initialize memory manager with persistence
    memory_manager = MemoryManager(persist_to_disk=True, storage_dir="./memory")
    
    # Create the manager agent
    manager = ManagerAgent(name="Manager", memory_manager=memory_manager)
    
    # Example prompt that will require all agent functions
    prompt = """
    Create a weather dashboard application with the following features:
    
    1. A responsive web interface that displays current weather and 5-day forecast
    2. Backend API that fetches data from a public weather API
    3. Ability to search for weather by city name or zip code
    4. Show temperature, humidity, wind speed, and weather conditions
    5. Store user's recent searches
    6. Display weather data using charts and icons
    7. Automatically detect user's location on initial load
    
    The solution should be easy to deploy and use Docker for containerization.
    Make it accessible for developers to extend with new features.
    """
    
    print("\n" + "=" * 60)
    print(" ClaudeAgents - Multi-agent Collaborative Development Example ")
    print("=" * 60 + "\n")
    
    print(f"🚀 Starting development process with prompt:\n{prompt}\n")
    print("📋 This example will demonstrate the complete collaborative workflow using all agent types:\n")
    print("1. Manager Agent - Overall coordination")
    print("2. Architecture Designer - System architecture")
    print("3. Stack Builder - Technology stack setup")
    print("4. Library Researcher - Finding optimal libraries")
    print("5. Software Planner - Development planning")
    print("6. Software Programmer - Code implementation")
    print("7. Exception Debugger - Testing and debugging")
    print("8. Dependency Analyzer - Dependency management\n")
    
    # Execute the manager agent with the prompt
    try:
        print("⏳ Starting multi-agent process - this may take several minutes...\n")
        result = await manager.execute(prompt)
        
        if result["success"]:
            print("\n✅ Process completed successfully!\n")
            
            # Access detailed results
            final_result = result.get("result", {})
            
            # Print summary
            print("📑 Solution Summary:")
            print(f"  {final_result.get('summary', 'No summary available')[:500]}...\n")
            
            # Print architecture overview
            print("🏗️ Architecture Overview:")
            architecture = final_result.get("architecture", {})
            print(f"  {architecture.get('summary', 'No architecture details available')[:300]}...\n")
            
            # Print technology stack
            libraries = final_result.get("libraries", {})
            if isinstance(libraries, dict) and "libraries" in libraries:
                print("📚 Selected Libraries:")
                for lib in libraries["libraries"]:
                    print(f"  • {lib.get('name', 'Unknown')}: {lib.get('description', 'No description')[:100]}")
            
            # Print file summary
            files = final_result.get("files", {})
            if files:
                print("\n💻 Generated Files:")
                for filename, content in files.items():
                    print(f"  • {filename}")
            
            print("\n📁 Full solution details saved to memory directory.")
            
        else:
            print(f"\n❌ Process failed: {result.get('error', 'Unknown error')}")
    
    except Exception as e:
        logger.exception(f"Error in example: {str(e)}")
        print(f"\n❌ Error: {str(e)}")


# Run the example
if __name__ == "__main__":
    asyncio.run(run_example())