from typing import Any, Dict, Optional
from loguru import logger
import json
import os


class MemoryManager:
    """Memory manager for maintaining context across agents and sessions.
    
    This class provides storage and retrieval of data for agents,
    with support for both in-memory and persistent storage.
    """
    
    def __init__(self, persist_to_disk: bool = False, storage_dir: str = "./memory"):
        """Initialize the memory manager.
        
        Args:
            persist_to_disk: Whether to persist memory to disk
            storage_dir: Directory for persistent storage
        """
        self._memory_store: Dict[str, Dict[str, Any]] = {}
        self.persist_to_disk = persist_to_disk
        self.storage_dir = storage_dir
        
        if persist_to_disk:
            os.makedirs(storage_dir, exist_ok=True)
            logger.info(f"Memory manager initialized with persistence at {storage_dir}")
        else:
            logger.info("Memory manager initialized with in-memory storage only")
    
    def store(self, agent_id: str, key: str, value: Any) -> None:
        """Store a value in memory.
        
        Args:
            agent_id: The ID of the agent storing the data
            key: The key to store the value under
            value: The value to store
        """
        if agent_id not in self._memory_store:
            self._memory_store[agent_id] = {}
        
        self._memory_store[agent_id][key] = value
        logger.debug(f"Stored value for agent {agent_id} under key '{key}'")
        
        if self.persist_to_disk:
            self._save_to_disk(agent_id)
    
    def retrieve(self, agent_id: str, key: str) -> Optional[Any]:
        """Retrieve a value from memory.
        
        Args:
            agent_id: The ID of the agent retrieving the data
            key: The key to retrieve
            
        Returns:
            The stored value if found, None otherwise
        """
        # If we're using persistence and don't have this agent's data in memory, try to load it
        if self.persist_to_disk and agent_id not in self._memory_store:
            self._load_from_disk(agent_id)
        
        if agent_id in self._memory_store and key in self._memory_store[agent_id]:
            logger.debug(f"Retrieved value for agent {agent_id} under key '{key}'")
            return self._memory_store[agent_id][key]
        
        logger.debug(f"No value found for agent {agent_id} under key '{key}'")
        return None
    
    def get_all(self, agent_id: str) -> Dict[str, Any]:
        """Get all stored values for an agent.
        
        Args:
            agent_id: The ID of the agent
            
        Returns:
            Dictionary of all keys and values for the agent
        """
        # If we're using persistence and don't have this agent's data in memory, try to load it
        if self.persist_to_disk and agent_id not in self._memory_store:
            self._load_from_disk(agent_id)
        
        return self._memory_store.get(agent_id, {})
    
    def clear(self, agent_id: Optional[str] = None) -> None:
        """Clear stored memory.
        
        Args:
            agent_id: If provided, clear only this agent's data, otherwise clear all
        """
        if agent_id:
            if agent_id in self._memory_store:
                del self._memory_store[agent_id]
                logger.info(f"Cleared memory for agent {agent_id}")
                
                if self.persist_to_disk:
                    file_path = os.path.join(self.storage_dir, f"{agent_id}.json")
                    if os.path.exists(file_path):
                        os.remove(file_path)
        else:
            self._memory_store.clear()
            logger.info("Cleared all memory")
            
            if self.persist_to_disk:
                for filename in os.listdir(self.storage_dir):
                    if filename.endswith('.json'):
                        os.remove(os.path.join(self.storage_dir, filename))
    
    def _save_to_disk(self, agent_id: str) -> None:
        """Save agent data to disk.
        
        Args:
            agent_id: The ID of the agent
        """
        try:
            file_path = os.path.join(self.storage_dir, f"{agent_id}.json")
            with open(file_path, 'w') as f:
                json.dump(self._memory_store[agent_id], f)
            logger.debug(f"Saved memory to disk for agent {agent_id}")
        except Exception as e:
            logger.error(f"Failed to save memory to disk for agent {agent_id}: {str(e)}")
    
    def _load_from_disk(self, agent_id: str) -> None:
        """Load agent data from disk.
        
        Args:
            agent_id: The ID of the agent
        """
        file_path = os.path.join(self.storage_dir, f"{agent_id}.json")
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    self._memory_store[agent_id] = json.load(f)
                logger.debug(f"Loaded memory from disk for agent {agent_id}")
            except Exception as e:
                logger.error(f"Failed to load memory from disk for agent {agent_id}: {str(e)}")
                # Initialize empty dict if load fails
                self._memory_store[agent_id] = {}