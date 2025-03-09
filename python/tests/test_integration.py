import pytest
import asyncio
import json
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Dict, Any, List

from src.utils.memory_manager import MemoryManager
from src.agents.manager_agent import ManagerAgent
from src.agents.architecture_designer_agent import ArchitectureDesignerAgent
from src.agents.stack_builder_agent import StackBuilderAgent
from src.agents.library_researcher_agent import LibraryResearcherAgent
from src.agents.software_planner_agent import SoftwarePlannerAgent
from src.agents.software_programmer_agent import SoftwareProgrammerAgent
from src.agents.exception_debugger_agent import ExceptionDebuggerAgent
from src.agents.dependency_analyzer_agent import DependencyAnalyzerAgent
from conftest import MockLLM, MockMemoryManager


class TestAgentIntegration:
    """Integration tests for the agent system."""
    
    @pytest.mark.asyncio
    async def test_all_agents_initialization(self, mock_llm, mock_memory_manager):
        """Test that all agents can be initialized."""
        # Initialize all agent types
        agents = {
            "manager": ManagerAgent(name="manager", memory_manager=mock_memory_manager, llm=mock_llm),
            "architecture_designer": ArchitectureDesignerAgent(name="architecture_designer", memory_manager=mock_memory_manager, llm=mock_llm),
            "stack_builder": StackBuilderAgent(name="stack_builder", memory_manager=mock_memory_manager, llm=mock_llm),
            "library_researcher": LibraryResearcherAgent(name="library_researcher", memory_manager=mock_memory_manager, llm=mock_llm),
            "software_planner": SoftwarePlannerAgent(name="software_planner", memory_manager=mock_memory_manager, llm=mock_llm),
            "software_programmer": SoftwareProgrammerAgent(name="software_programmer", memory_manager=mock_memory_manager, llm=mock_llm),
            "exception_debugger": ExceptionDebuggerAgent(name="exception_debugger", memory_manager=mock_memory_manager, llm=mock_llm),
            "dependency_analyzer": DependencyAnalyzerAgent(name="dependency_analyzer", memory_manager=mock_memory_manager, llm=mock_llm)
        }
        
        # Check that all agents were initialized correctly
        for agent_name, agent in agents.items():
            assert agent.name == agent_name
            assert agent.memory_manager == mock_memory_manager
            assert agent.llm == mock_llm
            assert len(agent.tools) > 0
            
    @pytest.mark.asyncio
    async def test_manager_agent_creates_specialized_agents(self, mock_llm, mock_memory_manager):
        """Test that the manager agent creates and uses specialized agents."""
        manager = ManagerAgent(name="manager", memory_manager=mock_memory_manager, llm=mock_llm)
        
        # Mock execute methods for all specialized agents
        with patch.object(ArchitectureDesignerAgent, '__new__') as mock_arch_designer, \
             patch.object(LibraryResearcherAgent, '__new__') as mock_lib_researcher, \
             patch.object(SoftwarePlannerAgent, '__new__') as mock_sw_planner, \
             patch.object(SoftwareProgrammerAgent, '__new__') as mock_sw_programmer, \
             patch.object(ExceptionDebuggerAgent, '__new__') as mock_debugger, \
             patch.object(DependencyAnalyzerAgent, '__new__') as mock_dep_analyzer:
            
            # Set up mock returns for each agent type
            mock_arch_designer.return_value = MagicMock()
            mock_arch_designer.return_value.execute = AsyncMock(return_value={"success": True, "design": {}})
            
            mock_lib_researcher.return_value = MagicMock()
            mock_lib_researcher.return_value.execute = AsyncMock(return_value={"success": True, "libraries": {}})
            
            mock_sw_planner.return_value = MagicMock()
            mock_sw_planner.return_value.execute = AsyncMock(return_value={"success": True, "plan": {}})
            
            mock_sw_programmer.return_value = MagicMock()
            mock_sw_programmer.return_value.execute = AsyncMock(return_value={"success": True, "code": {"files": {}}})
            
            mock_debugger.return_value = MagicMock()
            mock_debugger.return_value.execute = AsyncMock(return_value={"success": True, "debug_result": {}})
            
            mock_dep_analyzer.return_value = MagicMock()
            mock_dep_analyzer.return_value.execute = AsyncMock(return_value={"success": True, "analysis": {}})
            
            # Mock analyze_requirements to avoid LLM calls
            with patch.object(manager, '_analyze_requirements') as mock_analyze:
                mock_analyze.return_value = {
                    "prompt": "test prompt", 
                    "extracted_requirements": ["req1"]
                }
                
                # Mock create_final_summary
                with patch.object(manager, '_create_final_summary') as mock_summary:
                    mock_summary.return_value = {"summary": "Final summary"}
                    
                    # Execute the manager agent
                    result = await manager.execute("Create a web application")
                    
                    # Check that the result was successful
                    assert result["success"] == True
                    
                    # Verify that all specialized agents were created and executed
                    mock_arch_designer.assert_called_once()
                    mock_lib_researcher.assert_called_once()
                    mock_sw_planner.assert_called_once()
                    mock_sw_programmer.assert_called_once()
                    mock_debugger.assert_called_once()
                    mock_dep_analyzer.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_memory_sharing_between_agents(self, mock_llm):
        """Test that agents can share data through the memory manager."""
        # Create a real memory manager for this test
        memory_manager = MemoryManager(persist_to_disk=False)
        
        # Create two agent instances
        agent1 = ArchitectureDesignerAgent(name="agent1", memory_manager=memory_manager, llm=mock_llm)
        agent2 = SoftwarePlannerAgent(name="agent2", memory_manager=memory_manager, llm=mock_llm)
        
        # Mock the agent executors
        with patch.object(agent1, 'agent_executor') as mock_executor1, \
             patch.object(agent2, 'agent_executor') as mock_executor2:
            
            # Agent 1 will store data in memory
            mock_executor1.invoke = AsyncMock(return_value={"output": "result1"})
            
            # Execute agent1 to store data
            test_data = {"key": "value"}
            agent1.save_to_memory("test_data", test_data)
            
            # Now have agent2 retrieve data that agent1 stored
            retrieved_data = agent2.retrieve_from_memory("test_data")
            
            # Check that agent2 could retrieve agent1's data
            assert retrieved_data == test_data
    
    @pytest.mark.asyncio
    async def test_agent_conversation_history(self, mock_llm, mock_memory_manager):
        """Test that agents properly maintain conversation history."""
        agent = LibraryResearcherAgent(name="test_agent", memory_manager=mock_memory_manager, llm=mock_llm)
        
        # Add messages to conversation history
        agent.add_to_conversation("user", "Can you find a JavaScript library for charts?")
        agent.add_to_conversation("assistant", "I recommend Chart.js for JavaScript charting.")
        
        # Check the conversation history
        assert len(agent.conversation_history) == 2
        assert agent.conversation_history[0]["role"] == "user"
        assert "JavaScript" in agent.conversation_history[0]["content"]
        assert agent.conversation_history[1]["role"] == "assistant"
        assert "Chart.js" in agent.conversation_history[1]["content"]
        
        # Check that messages were added to memory
        mock_memory_manager.save_message_to_memory.assert_called()
        
    @pytest.mark.asyncio
    async def test_concurrent_agent_execution(self, mock_llm, mock_memory_manager):
        """Test that multiple agents can be executed concurrently."""
        # Create multiple agents
        agent1 = ArchitectureDesignerAgent(name="agent1", memory_manager=mock_memory_manager, llm=mock_llm)
        agent2 = LibraryResearcherAgent(name="agent2", memory_manager=mock_memory_manager, llm=mock_llm)
        agent3 = SoftwarePlannerAgent(name="agent3", memory_manager=mock_memory_manager, llm=mock_llm)
        
        # Mock the agents' execute methods
        with patch.object(agent1, 'agent_executor') as mock_executor1, \
             patch.object(agent2, 'agent_executor') as mock_executor2, \
             patch.object(agent3, 'agent_executor') as mock_executor3:
            
            mock_executor1.invoke = AsyncMock(return_value={"output": "result1"})
            mock_executor2.invoke = AsyncMock(return_value={"output": "result2"})
            mock_executor3.invoke = AsyncMock(return_value={"output": "result3"})
            
            # Execute all agents concurrently
            tasks = [
                agent1.execute("Design a web architecture"),
                agent2.execute("Research JavaScript UI libraries"),
                agent3.execute("Plan a software structure")
            ]
            
            results = await asyncio.gather(*tasks)
            
            # Check that all agents were executed
            assert len(results) == 3
            assert all(result["success"] for result in results)
            
            # Check that all executors were called
            assert mock_executor1.invoke.called
            assert mock_executor2.invoke.called
            assert mock_executor3.invoke.called