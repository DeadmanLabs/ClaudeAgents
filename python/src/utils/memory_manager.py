from typing import Any, Dict, Optional, List, Tuple, Type, cast
from loguru import logger
import json
import os
import pickle
import datetime

from langchain_core.memory import BaseMemory
from langchain.memory import (
    ConversationBufferMemory,
    ConversationSummaryMemory,
    CombinedMemory,
    ConversationEntityMemory
)
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage
from langchain_core.language_models import BaseLanguageModel

# BaseEntityStore was moved in newer versions of langchain
try:
    from langchain_core.message_history import BaseEntityStore
except ImportError:
    try:
        from langchain_core.entity_stores import BaseEntityStore
    except ImportError:
        # If both imports fail, create a stub class
        class BaseEntityStore:
            pass


class MemoryManager:
    """Memory manager for maintaining context across agents and sessions.
    
    This class provides storage and retrieval of data for agents,
    with support for both in-memory and persistent storage, and
    integration with LangChain memory components.
    """
    
    def __init__(self, persist_to_disk: bool = False, storage_dir: str = "./memory", 
                llm: Optional[BaseLanguageModel] = None):
        """Initialize the memory manager.
        
        Args:
            persist_to_disk: Whether to persist memory to disk
            storage_dir: Directory for persistent storage
            llm: Optional language model for memory operations
        """
        self._memory_store: Dict[str, Dict[str, Any]] = {}
        self._langchain_memories: Dict[str, BaseMemory] = {}
        self.persist_to_disk = persist_to_disk
        self.storage_dir = storage_dir
        self.llm = llm
        
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
                
                if agent_id in self._langchain_memories:
                    del self._langchain_memories[agent_id]
                    logger.info(f"Cleared LangChain memory for agent {agent_id}")
                
                if self.persist_to_disk:
                    file_path = os.path.join(self.storage_dir, f"{agent_id}.json")
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    
                    # Also remove LangChain memory files
                    lc_file_path = os.path.join(self.storage_dir, f"{agent_id}_langchain.pkl")
                    if os.path.exists(lc_file_path):
                        os.remove(lc_file_path)
        else:
            self._memory_store.clear()
            self._langchain_memories.clear()
            logger.info("Cleared all memory")
            
            if self.persist_to_disk:
                for filename in os.listdir(self.storage_dir):
                    if filename.endswith(('.json', '.pkl')):
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
            
            # Also save LangChain memory if it exists
            if agent_id in self._langchain_memories:
                lc_file_path = os.path.join(self.storage_dir, f"{agent_id}_langchain.pkl")
                with open(lc_file_path, 'wb') as f:
                    pickle.dump(self._langchain_memories[agent_id], f)
                logger.debug(f"Saved LangChain memory to disk for agent {agent_id}")
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
        
        # Also load LangChain memory if it exists
        lc_file_path = os.path.join(self.storage_dir, f"{agent_id}_langchain.pkl")
        if os.path.exists(lc_file_path):
            try:
                with open(lc_file_path, 'rb') as f:
                    self._langchain_memories[agent_id] = pickle.load(f)
                logger.debug(f"Loaded LangChain memory from disk for agent {agent_id}")
            except Exception as e:
                logger.error(f"Failed to load LangChain memory from disk for agent {agent_id}: {str(e)}")
                # Will recreate memory when needed
    
    # LangChain Memory Integration
    
    def get_langchain_memory(self, agent_id: str, memory_type: str = "buffer", 
                           memory_key: str = "chat_history") -> BaseMemory:
        """Get a LangChain memory for an agent.
        
        Args:
            agent_id: The ID of the agent
            memory_type: Type of memory to use ('buffer', 'summary', 'entity', or 'combined')
            memory_key: Key for the memory in output context
            
        Returns:
            A LangChain memory instance
        """
        # Check if we already have a memory for this agent
        if agent_id in self._langchain_memories:
            return self._langchain_memories[agent_id]
        
        # If we're using persistence, try to load the memory
        if self.persist_to_disk:
            lc_file_path = os.path.join(self.storage_dir, f"{agent_id}_langchain.pkl")
            if os.path.exists(lc_file_path):
                try:
                    with open(lc_file_path, 'rb') as f:
                        self._langchain_memories[agent_id] = pickle.load(f)
                    logger.debug(f"Loaded LangChain memory from disk for agent {agent_id}")
                    return self._langchain_memories[agent_id]
                except Exception as e:
                    logger.error(f"Failed to load LangChain memory from disk for agent {agent_id}: {str(e)}")
        
        # Create a new memory based on the type
        memory: BaseMemory
        
        if memory_type == "buffer":
            memory = ConversationBufferMemory(memory_key=memory_key, return_messages=True)
        elif memory_type == "summary":
            if not self.llm:
                logger.warning("No LLM provided for summary memory, falling back to buffer memory")
                memory = ConversationBufferMemory(memory_key=memory_key, return_messages=True)
            else:
                memory = ConversationSummaryMemory(
                    llm=self.llm,
                    memory_key=memory_key,
                    return_messages=True
                )
        elif memory_type == "entity":
            if not self.llm:
                logger.warning("No LLM provided for entity memory, falling back to buffer memory")
                memory = ConversationBufferMemory(memory_key=memory_key, return_messages=True)
            else:
                memory = ConversationEntityMemory(
                    llm=self.llm,
                    entity_cache={},
                    memory_key=memory_key,
                    return_messages=True,
                    verbose=True
                )
        elif memory_type == "combined":
            if not self.llm:
                logger.warning("No LLM provided for combined memory, falling back to buffer memory")
                memory = ConversationBufferMemory(memory_key=memory_key, return_messages=True)
            else:
                buffer_memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
                summary_memory = ConversationSummaryMemory(
                    llm=self.llm,
                    memory_key="summary_history",
                    return_messages=True
                )
                memory = CombinedMemory(memories=[buffer_memory, summary_memory])
        else:
            logger.warning(f"Unknown memory type {memory_type}, using buffer memory")
            memory = ConversationBufferMemory(memory_key=memory_key, return_messages=True)
        
        # Store the memory
        self._langchain_memories[agent_id] = memory
        logger.info(f"Created new {memory_type} memory for agent {agent_id}")
        
        # Persist if needed
        if self.persist_to_disk:
            self._save_to_disk(agent_id)
        
        return memory
    
    def save_message_to_memory(self, agent_id: str, message: str, role: str) -> None:
        """Save a message to the agent's LangChain memory.
        
        Args:
            agent_id: The ID of the agent
            message: The message content
            role: The role of the message sender ('user', 'assistant', 'system')
        """
        # Get or create the agent's memory
        memory = self.get_langchain_memory(agent_id)
        
        # Add the message to the memory
        chat_memory = getattr(memory, "chat_memory", None)
        if chat_memory:
            if role == "user":
                chat_memory.add_user_message(message)
            elif role == "assistant":
                chat_memory.add_ai_message(message)
            elif role == "system":
                # Some memory implementations don't support system messages directly
                # Store it as a key in the regular memory
                self.store(agent_id, f"system_message_{datetime.datetime.now().isoformat()}", message)
            
            logger.debug(f"Added {role} message to LangChain memory for agent {agent_id}")
            
            # Persist if needed
            if self.persist_to_disk:
                self._save_to_disk(agent_id)
        else:
            logger.warning(f"Could not add message to LangChain memory for agent {agent_id}: no chat_memory attribute")
    
    def get_conversation_history(self, agent_id: str, as_messages: bool = False) -> Any:
        """Get the conversation history for an agent.
        
        Args:
            agent_id: The ID of the agent
            as_messages: Whether to return as LangChain messages or text
            
        Returns:
            Conversation history as messages or text
        """
        # Get the agent's memory
        memory = self.get_langchain_memory(agent_id)
        
        try:
            # Try to get the variables (different memory implementations have different methods)
            if hasattr(memory, "load_memory_variables"):
                memory_data = memory.load_memory_variables({})
                if as_messages:
                    # Return messages directly if available
                    if isinstance(memory_data.get("chat_history", []), List):
                        return memory_data.get("chat_history", [])
                    # Try to get chat_memory messages
                    chat_memory = getattr(memory, "chat_memory", None)
                    if chat_memory and hasattr(chat_memory, "messages"):
                        return chat_memory.messages
                    
                # Return as string
                if "chat_history" in memory_data:
                    return memory_data["chat_history"]
                # Try alternate keys
                for key in memory_data:
                    if "history" in key or "memory" in key:
                        return memory_data[key]
            
            # Fallback to our stored conversation history
            legacy_history = self.retrieve(agent_id, "conversation_history")
            if legacy_history and isinstance(legacy_history, list):
                if as_messages:
                    # Convert dict format to LangChain messages
                    messages = []
                    for msg in legacy_history:
                        if msg["role"] == "user":
                            messages.append(HumanMessage(content=msg["content"]))
                        elif msg["role"] == "assistant":
                            messages.append(AIMessage(content=msg["content"]))
                        elif msg["role"] == "system":
                            messages.append(SystemMessage(content=msg["content"]))
                    return messages
                else:
                    # Format as text
                    return "\n".join([f"{msg['role']}: {msg['content']}" for msg in legacy_history])
            
            # No history found
            return [] if as_messages else ""
            
        except Exception as e:
            logger.error(f"Error retrieving conversation history for agent {agent_id}: {str(e)}")
            return [] if as_messages else ""