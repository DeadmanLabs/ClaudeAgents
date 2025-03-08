from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from loguru import logger
import uuid


class BaseAgent(ABC):
    """Base class for all agents in the system.
    
    This abstract class defines the common interface and functionality
    that all specialized agents must implement.
    """
    
    def __init__(self, name: str, memory_manager: Any = None, config: Optional[Dict[str, Any]] = None):
        """Initialize a new agent.
        
        Args:
            name: A unique name for this agent instance
            memory_manager: The memory manager for storing context
            config: Configuration parameters for the agent
        """
        self.id = str(uuid.uuid4())
        self.name = name
        self.memory_manager = memory_manager
        self.config = config or {}
        self.conversation_history: List[Dict[str, Any]] = []
        logger.info(f"Initialized {self.__class__.__name__} - {self.name} ({self.id})")
    
    @abstractmethod
    async def execute(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        """Execute the agent's main task based on a prompt.
        
        Args:
            prompt: The input prompt or task description
            **kwargs: Additional parameters for execution
            
        Returns:
            Dictionary containing the results of the agent's execution
        """
        pass
    
    def save_to_memory(self, key: str, value: Any) -> None:
        """Save data to the agent's memory manager.
        
        Args:
            key: Key to store the value under
            value: Data to store
        """
        if self.memory_manager:
            self.memory_manager.store(self.id, key, value)
            logger.debug(f"Agent {self.name} stored data under key '{key}'")
    
    def retrieve_from_memory(self, key: str) -> Any:
        """Retrieve data from the agent's memory manager.
        
        Args:
            key: Key to retrieve data for
            
        Returns:
            The stored data if found, None otherwise
        """
        if self.memory_manager:
            data = self.memory_manager.retrieve(self.id, key)
            logger.debug(f"Agent {self.name} retrieved data for key '{key}'")
            return data
        return None
    
    def add_to_conversation(self, role: str, content: str) -> None:
        """Add a message to the conversation history.
        
        Args:
            role: The role of the message sender (e.g., "user", "agent", "system")
            content: The message content
        """
        self.conversation_history.append({"role": role, "content": content})