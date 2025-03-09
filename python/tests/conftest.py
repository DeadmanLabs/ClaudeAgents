import os
import sys
import pytest
from typing import Dict, Any, List

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import modules to be mocked
from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.outputs import LLMResult

# Mock classes for testing
class MockLLM(BaseLanguageModel):
    """Mock LLM for testing that returns predefined responses."""
    
    def __init__(self, responses: Dict[str, str] = None):
        """Initialize the mock LLM with predefined responses."""
        self.responses = responses or {}
        self.invocation_params = {}
        self.invoke_count = 0
        self.invoke_inputs = []
    
    def invoke(self, prompt: str, **kwargs) -> str:
        """Mock the invoke method to return predefined responses."""
        self.invoke_count += 1
        self.invoke_inputs.append(prompt)
        
        # Check for exact matches in responses
        if prompt in self.responses:
            return self.responses[prompt]
        
        # Check for substring matches
        for key, response in self.responses.items():
            if key in prompt:
                return response
        
        # Default response
        return "Mock LLM response for: " + prompt[:30] + "..."
    
    async def ainvoke(self, prompt: str, **kwargs) -> str:
        """Mock the async invoke method."""
        return self.invoke(prompt, **kwargs)
    
    def predict(self, prompt: str, **kwargs) -> str:
        """Mock the predict method."""
        return self.invoke(prompt, **kwargs)
    
    def generate(self, prompts: List[str], **kwargs) -> LLMResult:
        """Mock the generate method."""
        return LLMResult(generations=[[{"text": self.invoke(prompt)}] for prompt in prompts])
    
    def get_num_tokens(self, text: str) -> int:
        """Mock the get_num_tokens method."""
        return len(text.split())


class MockMemoryManager:
    """Mock memory manager for testing."""
    
    def __init__(self):
        """Initialize the mock memory manager."""
        self.memory = {}
        self.langchain_memories = {}
    
    def store(self, agent_id: str, key: str, value: Any) -> None:
        """Store a value in memory."""
        if agent_id not in self.memory:
            self.memory[agent_id] = {}
        self.memory[agent_id][key] = value
    
    def retrieve(self, agent_id: str, key: str) -> Any:
        """Retrieve a value from memory."""
        if agent_id in self.memory and key in self.memory[agent_id]:
            return self.memory[agent_id][key]
        return None
    
    def get_all(self, agent_id: str) -> Dict[str, Any]:
        """Get all stored values for an agent."""
        return self.memory.get(agent_id, {})
    
    def clear(self, agent_id: str = None) -> None:
        """Clear stored memory."""
        if agent_id:
            if agent_id in self.memory:
                del self.memory[agent_id]
        else:
            self.memory = {}
    
    def get_langchain_memory(self, agent_id: str, memory_type: str = "buffer",
                           memory_key: str = "chat_history"):
        """Mock get_langchain_memory."""
        if agent_id not in self.langchain_memories:
            self.langchain_memories[agent_id] = MockLangChainMemory()
        return self.langchain_memories[agent_id]
    
    def save_message_to_memory(self, agent_id: str, message: str, role: str) -> None:
        """Mock save_message_to_memory."""
        key = f"message_{len(self.get_all(agent_id))}"
        self.store(agent_id, key, {"role": role, "content": message})


class MockLangChainMemory:
    """Mock LangChain memory for testing."""
    
    def __init__(self):
        """Initialize the mock LangChain memory."""
        self.messages = []
        self.variables = {"chat_history": []}
        self.chat_memory = self
    
    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Mock load_memory_variables method."""
        return self.variables
    
    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, str]) -> None:
        """Mock save_context method."""
        self.variables["inputs"] = inputs
        self.variables["outputs"] = outputs
    
    def clear(self) -> None:
        """Mock clear method."""
        self.messages = []
        self.variables = {"chat_history": []}
    
    def add_user_message(self, message: str) -> None:
        """Add a user message to the memory."""
        self.messages.append(HumanMessage(content=message))
        self.variables["chat_history"] = self.messages
    
    def add_ai_message(self, message: str) -> None:
        """Add an AI message to the memory."""
        self.messages.append(AIMessage(content=message))
        self.variables["chat_history"] = self.messages
    
    def get_messages(self) -> List[BaseMessage]:
        """Get all messages."""
        return self.messages


# Fixtures
@pytest.fixture
def mock_llm():
    """Fixture that returns a mock LLM."""
    return MockLLM({
        "Design an architecture": """{"summary": "Microservices architecture", "backend": "Node.js and Python", "frontend": "React", 
                                     "database": "PostgreSQL", "deployment": "Docker", "components": [
                                     {"name": "API Gateway", "technology": "Express", "responsibility": "Routing"},
                                     {"name": "User Service", "technology": "Python", "responsibility": "User management"}],
                                     "rationale": "Scalable and modular design"}""",
        "Research libraries": """{"selected_libraries": ["React", "Express", "FastAPI", "SQLAlchemy"]}""",
        "Create a software plan": """{"summary": "Implementation plan", "tasks": ["Set up project", "Implement API"], 
                                    "timeline": "2 weeks", "files": ["app.py", "index.js"]}""",
        "Implement": """{"code": {"app.py": "print('Hello')", "index.js": "console.log('Hello')"}}""",
        "Debug": """{"status": "Passed", "issues": [], "fixes": []}""",
        "Analyze dependencies": """{"status": "Compatible", "dependencies": ["react", "express"], 
                                  "versions": {"react": "18.2.0", "express": "4.18.2"}}"""
    })

@pytest.fixture
def mock_memory_manager():
    """Fixture that returns a mock memory manager."""
    return MockMemoryManager()