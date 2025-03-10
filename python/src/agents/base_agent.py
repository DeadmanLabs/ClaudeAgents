from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, Type, Sequence, Callable, cast
from loguru import logger
import uuid
import asyncio
import os

from langchain.agents import AgentExecutor
from langchain.agents.agent import AgentOutputParser
from langchain.agents.conversational.base import ConversationalAgent
from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.callbacks import AsyncCallbackManager
from langchain_core.language_models import BaseLanguageModel
from langchain_core.memory import BaseMemory
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, PromptTemplate
from langchain_core.runnables import Runnable, RunnableConfig
from langchain_core.tools import BaseTool
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory

# Tool has been moved in newer versions of langchain
try:
    from langchain.agents.tools import Tool
except ImportError:
    try:
        from langchain.tools import Tool
    except ImportError:
        from langchain_core.tools import Tool


class BaseAgent(ABC):
    """Base class for all agents in the system.
    
    This abstract class defines the common interface and functionality
    that all specialized agents must implement. It uses LangChain components
    to power the agent's functionality.
    """
    
    def __init__(
        self, 
        name: str, 
        memory_manager: Any = None, 
        config: Optional[Dict[str, Any]] = None,
        llm: Optional[BaseLanguageModel] = None,
        tools: Optional[List[BaseTool]] = None,
        memory: Optional[BaseMemory] = None,
        verbose: bool = False
    ):
        """Initialize a new agent.
        
        Args:
            name: A unique name for this agent instance
            memory_manager: The memory manager for storing context
            config: Configuration parameters for the agent
            llm: The language model to use for this agent
            tools: List of tools the agent can use
            memory: LangChain memory instance for conversation history
            verbose: Whether to output verbose logging
        """
        self.id = str(uuid.uuid4())
        self.name = name
        self.memory_manager = memory_manager
        self.config = config or {}
        self.verbose = verbose
        
        # Initialize LangChain components
        self.llm = llm or self._get_default_llm()
        self.tools = tools or []
        self.memory = memory or ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        # For backward compatibility
        self.conversation_history: List[Dict[str, Any]] = []
        
        # Initialize agent executor
        self.agent_executor = self._create_agent_executor()
        
        logger.info(f"Initialized {self.__class__.__name__} - {self.name} ({self.id})")
    
    def _get_default_llm(self) -> BaseLanguageModel:
        """Get the default language model based on config or environment variables."""
        # Import here to avoid circular imports
        from utils.env_loader import get_env
        
        # Get provider from config or .env or default to anthropic
        provider = self.config.get("provider", get_env("DEFAULT_PROVIDER", "anthropic")).lower()
        
        if provider == "anthropic":
            api_key = get_env("ANTHROPIC_API_KEY")
            if not api_key:
                logger.warning("ANTHROPIC_API_KEY not found in environment variables or .env file")
                # For demo purposes only - use OpenAI as fallback if ANTHROPIC_API_KEY not found
                openai_api_key = get_env("OPENAI_API_KEY")
                if openai_api_key:
                    logger.info("Falling back to OpenAI since ANTHROPIC_API_KEY is not set")
                    model = get_env("DEFAULT_MODEL", "gpt-3.5-turbo")
                    temp = float(get_env("DEFAULT_TEMPERATURE", 0.7))
                    return ChatOpenAI(
                        model=self.config.get("model", model),
                        temperature=self.config.get("temperature", temp),
                        openai_api_key=openai_api_key
                    )
                else:
                    # Use a dummy API key for testing - this will not make actual API calls
                    # but allows the code to initialize for demonstration purposes
                    logger.warning("Using dummy API key for demo purposes - no actual API calls will work")
                    api_key = "dummy_sk_ant_for_initialization"
            
            model = get_env("DEFAULT_MODEL", "claude-3-haiku-20240307")
            temp = float(get_env("DEFAULT_TEMPERATURE", 0.7))
            return ChatAnthropic(
                model=self.config.get("model", model),
                temperature=self.config.get("temperature", temp),
                anthropic_api_key=api_key
            )
        elif provider == "openai":
            api_key = get_env("OPENAI_API_KEY")
            if not api_key:
                logger.warning("OPENAI_API_KEY not found in environment variables or .env file")
                # For demo purposes only - use Anthropic as fallback if OPENAI_API_KEY not found
                anthropic_api_key = get_env("ANTHROPIC_API_KEY")
                if anthropic_api_key:
                    logger.info("Falling back to Anthropic since OPENAI_API_KEY is not set")
                    model = get_env("DEFAULT_MODEL", "claude-3-haiku-20240307")
                    temp = float(get_env("DEFAULT_TEMPERATURE", 0.7))
                    return ChatAnthropic(
                        model=self.config.get("model", model),
                        temperature=self.config.get("temperature", temp),
                        anthropic_api_key=anthropic_api_key
                    )
                else:
                    # Use a dummy API key for testing - this will not make actual API calls
                    # but allows the code to initialize for demonstration purposes
                    logger.warning("Using dummy API key for demo purposes - no actual API calls will work")
                    api_key = "dummy_sk_openai_for_initialization"
            
            model = get_env("DEFAULT_MODEL", "gpt-3.5-turbo")
            temp = float(get_env("DEFAULT_TEMPERATURE", 0.7))
            return ChatOpenAI(
                model=self.config.get("model", model),
                temperature=self.config.get("temperature", temp),
                openai_api_key=api_key
            )
        else:
            raise ValueError(f"Unsupported AI provider: {provider}")
    
    def _get_agent_system_message(self) -> str:
        """Get the system message for this agent type.
        
        Override this in subclasses to provide specialized instructions.
        """
        return f"""You are {self.name}, an AI assistant specialized for software development tasks.
        Answer the human's questions to the best of your ability."""
    
    def _create_agent_executor(self) -> AgentExecutor:
        """Create the LangChain agent executor for this agent."""
        # Import the necessary modules
        from langchain.agents import initialize_agent, AgentType
        
        # Create a simple agent using the initialize_agent function
        # This avoids the issues with agent_scratchpad formatting
        executor = initialize_agent(
            tools=self.tools,
            llm=self.llm,
            agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
            verbose=self.verbose,
            memory=self.memory,
            handle_parsing_errors=True
        )
        
        return executor
    
    @abstractmethod
    async def execute(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        """Execute the agent's main task based on a prompt.
        
        Args:
            prompt: The input prompt or task description
            **kwargs: Additional parameters for execution
            
        Returns:
            Dictionary containing the results of the agent's execution
        """
        try:
            # Default implementation using LangChain agent executor
            result = await asyncio.to_thread(
                self.agent_executor.invoke,
                {"input": prompt}
            )
            
            # Add the interaction to the conversation history (for backward compatibility)
            self.add_to_conversation("user", prompt)
            self.add_to_conversation("assistant", str(result.get("output", "")))
            
            return {
                "success": True,
                "data": result.get("output", ""),
                "raw_result": result
            }
        except Exception as e:
            logger.error(f"Error in agent execution: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
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
        # Add to old-style conversation history for backward compatibility
        self.conversation_history.append({"role": role, "content": content})
        
        # Convert to LangChain message format and add to memory
        if role == "user":
            self.memory.chat_memory.add_user_message(content)
        elif role == "assistant":
            self.memory.chat_memory.add_ai_message(content)
        elif role == "system":
            # LangChain memory doesn't typically store system messages in chat history
            # but we'll keep it in the conversation_history list
            pass
