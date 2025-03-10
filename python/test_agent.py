import asyncio
import sys
import os
from src.agents.manager_agent import ManagerAgent
from src.utils.memory_manager import MemoryManager

async def test_agent():
    # Use absolute path for the output file
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_output.txt")
    with open(output_path, "w") as f:
        f.write("Initializing MemoryManager...\n")
        memory_manager = MemoryManager(persist_to_disk=False)
        
        f.write("Initializing ManagerAgent...\n")
        try:
            manager = ManagerAgent(
                name="Manager", 
                memory_manager=memory_manager
            )
            f.write("ManagerAgent initialized successfully!\n")
            f.write("Test passed!\n")
        except Exception as e:
            f.write(f"Error: {str(e)}\n")
            f.write(f"Test failed!\n")

if __name__ == "__main__":
    asyncio.run(test_agent())
    print("Test completed. Check test_output.txt for results.")
