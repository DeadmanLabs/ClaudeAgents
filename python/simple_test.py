import sys
import os

def main():
    # Create a log file in the current directory
    log_file = os.path.join(os.getcwd(), "test_log.txt")
    
    with open(log_file, "w") as f:
        try:
            f.write("Starting test...\n")
            
            # Import the necessary modules
            from src.agents.manager_agent import ManagerAgent
            from src.utils.memory_manager import MemoryManager
            
            f.write("Modules imported successfully\n")
            
            # Initialize memory manager
            memory_manager = MemoryManager(persist_to_disk=False)
            f.write("Memory manager initialized\n")
            
            # Initialize manager agent
            manager = ManagerAgent(
                name="Manager", 
                memory_manager=memory_manager
            )
            f.write("Manager agent initialized successfully\n")
            
            f.write("Test passed!\n")
            return 0
        except Exception as e:
            f.write(f"Error: {str(e)}\n")
            f.write(f"Test failed!\n")
            return 1

if __name__ == "__main__":
    exit_code = main()
    print(f"Test completed with exit code {exit_code}. Check test_log.txt for details.")
    sys.exit(exit_code)
