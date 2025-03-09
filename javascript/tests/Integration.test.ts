import { ManagerAgent } from '../src/agents/ManagerAgent';
import { ArchitectureDesignerAgent } from '../src/agents/ArchitectureDesignerAgent';
import { StackBuilderAgent } from '../src/agents/StackBuilderAgent';
import { LibraryResearcherAgent } from '../src/agents/LibraryResearcherAgent';
import { SoftwarePlannerAgent } from '../src/agents/SoftwarePlannerAgent';
import { SoftwareProgrammerAgent } from '../src/agents/SoftwareProgrammerAgent';
import { ExceptionDebuggerAgent } from '../src/agents/ExceptionDebuggerAgent';
import { DependencyAnalyzerAgent } from '../src/agents/DependencyAnalyzerAgent';
import { MemoryManager } from '../src/utils/MemoryManager';

// Mock dependencies
jest.mock('../src/utils/MemoryManager');
jest.mock('../src/utils/AIClient');
jest.mock('../src/agents/ArchitectureDesignerAgent');
jest.mock('../src/agents/StackBuilderAgent');
jest.mock('../src/agents/LibraryResearcherAgent');
jest.mock('../src/agents/SoftwarePlannerAgent');
jest.mock('../src/agents/SoftwareProgrammerAgent');
jest.mock('../src/agents/ExceptionDebuggerAgent');
jest.mock('../src/agents/DependencyAnalyzerAgent');

describe('Agent Integration', () => {
  let mockMemoryManager: jest.Mocked<MemoryManager>;
  
  beforeEach(() => {
    // Create mocks
    mockMemoryManager = new MemoryManager(false, './memory') as jest.Mocked<MemoryManager>;
    mockMemoryManager.store = jest.fn();
    mockMemoryManager.retrieve = jest.fn();
    
    // Clear mock implementations
    jest.clearAllMocks();
  });
  
  test('should initialize all agent types successfully', () => {
    // Initialize all agent types
    const agents = {
      manager: new ManagerAgent('manager', mockMemoryManager),
      architectureDesigner: new ArchitectureDesignerAgent('architecture_designer', mockMemoryManager),
      stackBuilder: new StackBuilderAgent('stack_builder', mockMemoryManager),
      libraryResearcher: new LibraryResearcherAgent('library_researcher', mockMemoryManager),
      softwarePlanner: new SoftwarePlannerAgent('software_planner', mockMemoryManager),
      softwareProgrammer: new SoftwareProgrammerAgent('software_programmer', mockMemoryManager),
      exceptionDebugger: new ExceptionDebuggerAgent('exception_debugger', mockMemoryManager),
      dependencyAnalyzer: new DependencyAnalyzerAgent('dependency_analyzer', mockMemoryManager)
    };
    
    // Check that all agents were initialized correctly
    for (const [agentName, agent] of Object.entries(agents)) {
      expect(agent).toBeDefined();
      expect(agent.name).toBe(agentName);
      expect(agent.memoryManager).toBe(mockMemoryManager);
      expect(agent.tools.length).toBeGreaterThan(0);
    }
  });
  
  test('should create and coordinate specialized agents', async () => {
    // Create the manager agent
    const manager = new ManagerAgent('manager', mockMemoryManager);
    
    // Mock the _analyzeRequirements method
    manager['_analyzeRequirements'] = jest.fn().mockResolvedValue({
      prompt: 'test prompt',
      extractedRequirements: ['req1'],
      technologies: ['tech1']
    });
    
    // Mock the specialized agent creation
    const mockArchDesigner = new ArchitectureDesignerAgent('architecture_designer', mockMemoryManager);
    mockArchDesigner.execute = jest.fn().mockResolvedValue({ success: true, design: {} });
    
    const mockLibResearcher = new LibraryResearcherAgent('library_researcher', mockMemoryManager);
    mockLibResearcher.execute = jest.fn().mockResolvedValue({ success: true, libraries: {} });
    
    const mockSoftwarePlanner = new SoftwarePlannerAgent('software_planner', mockMemoryManager);
    mockSoftwarePlanner.execute = jest.fn().mockResolvedValue({ success: true, plan: {} });
    
    const mockSoftwareProgrammer = new SoftwareProgrammerAgent('software_programmer', mockMemoryManager);
    mockSoftwareProgrammer.execute = jest.fn().mockResolvedValue({ success: true, code: { files: {} } });
    
    const mockDebugger = new ExceptionDebuggerAgent('exception_debugger', mockMemoryManager);
    mockDebugger.execute = jest.fn().mockResolvedValue({ success: true, debug_result: {} });
    
    const mockDependencyAnalyzer = new DependencyAnalyzerAgent('dependency_analyzer', mockMemoryManager);
    mockDependencyAnalyzer.execute = jest.fn().mockResolvedValue({ success: true, analysis: {} });
    
    // Mock the _getOrCreateAgent method to return our mocks
    manager['_getOrCreateAgent'] = jest.fn().mockImplementation((agentKey) => {
      const mocks = {
        'architecture_designer': mockArchDesigner,
        'library_researcher': mockLibResearcher,
        'software_planner': mockSoftwarePlanner,
        'software_programmer': mockSoftwareProgrammer,
        'exception_debugger': mockDebugger,
        'dependency_analyzer': mockDependencyAnalyzer
      };
      return mocks[agentKey as keyof typeof mocks];
    });
    
    // Mock the createFinalSummary method
    manager['_createFinalSummary'] = jest.fn().mockResolvedValue({ summary: 'Final summary' });
    
    // Execute the manager agent
    const result = await manager.execute('Create a web application');
    
    // Check that the result was successful
    expect(result.success).toBe(true);
    
    // Verify that _getOrCreateAgent was called for each agent type
    expect(manager['_getOrCreateAgent']).toHaveBeenCalledWith('architecture_designer', expect.any(Function));
    expect(manager['_getOrCreateAgent']).toHaveBeenCalledWith('library_researcher', expect.any(Function));
    expect(manager['_getOrCreateAgent']).toHaveBeenCalledWith('software_planner', expect.any(Function));
    expect(manager['_getOrCreateAgent']).toHaveBeenCalledWith('software_programmer', expect.any(Function));
    expect(manager['_getOrCreateAgent']).toHaveBeenCalledWith('exception_debugger', expect.any(Function));
    expect(manager['_getOrCreateAgent']).toHaveBeenCalledWith('dependency_analyzer', expect.any(Function));
    
    // Verify that all specialized agents were executed
    expect(mockArchDesigner.execute).toHaveBeenCalled();
    expect(mockLibResearcher.execute).toHaveBeenCalled();
    expect(mockSoftwarePlanner.execute).toHaveBeenCalled();
    expect(mockSoftwareProgrammer.execute).toHaveBeenCalled();
    expect(mockDebugger.execute).toHaveBeenCalled();
    expect(mockDependencyAnalyzer.execute).toHaveBeenCalled();
  });
  
  test('should share memory between agents', async () => {
    // Create real memory manager
    const realMemoryManager = new MemoryManager(false, './memory');
    realMemoryManager.store = jest.fn();
    realMemoryManager.retrieve = jest.fn();
    
    // Create two agent instances
    const agent1 = new ArchitectureDesignerAgent('agent1', realMemoryManager);
    const agent2 = new SoftwarePlannerAgent('agent2', realMemoryManager);
    
    // Mock store and retrieve methods
    const testData = { key: 'value' };
    realMemoryManager.store.mockImplementation(() => {});
    realMemoryManager.retrieve.mockImplementation(() => testData);
    
    // Agent1 stores data
    agent1.saveToMemory('test_data', testData);
    
    // Agent2 retrieves data
    const retrievedData = agent2.retrieveFromMemory('test_data');
    
    // Check that memory manager methods were called correctly
    expect(realMemoryManager.store).toHaveBeenCalledWith('agent1', 'test_data', testData);
    expect(realMemoryManager.retrieve).toHaveBeenCalledWith('agent2', 'test_data');
    
    // Check that the data was retrieved correctly
    expect(retrievedData).toEqual(testData);
  });
  
  test('should maintain conversation history', () => {
    // Create an agent instance
    const agent = new LibraryResearcherAgent('test_agent', mockMemoryManager);
    
    // Mock memory
    agent.memory = {
      chatMemory: {
        addUserMessage: jest.fn(),
        addAIMessage: jest.fn()
      }
    } as any;
    
    // Add messages to conversation history
    agent.addToConversation('user', 'Can you find a JavaScript library for charts?');
    agent.addToConversation('assistant', 'I recommend Chart.js for JavaScript charting.');
    
    // Check that messages were added to memory
    expect(agent.memory.chatMemory.addUserMessage).toHaveBeenCalledWith('Can you find a JavaScript library for charts?');
    expect(agent.memory.chatMemory.addAIMessage).toHaveBeenCalledWith('I recommend Chart.js for JavaScript charting.');
  });
  
  test('should handle concurrent agent execution', async () => {
    // Create multiple agents
    const agent1 = new ArchitectureDesignerAgent('agent1', mockMemoryManager);
    const agent2 = new LibraryResearcherAgent('agent2', mockMemoryManager);
    const agent3 = new SoftwarePlannerAgent('agent3', mockMemoryManager);
    
    // Mock execute methods
    agent1.execute = jest.fn().mockResolvedValue({ success: true, design: {} });
    agent2.execute = jest.fn().mockResolvedValue({ success: true, libraries: {} });
    agent3.execute = jest.fn().mockResolvedValue({ success: true, plan: {} });
    
    // Execute all agents concurrently
    const results = await Promise.all([
      agent1.execute('Design a web architecture'),
      agent2.execute('Research JavaScript UI libraries'),
      agent3.execute('Plan a software structure')
    ]);
    
    // Check that all agents were executed
    expect(results.length).toBe(3);
    expect(results.every(result => result.success)).toBe(true);
    
    // Check that all execute methods were called
    expect(agent1.execute).toHaveBeenCalled();
    expect(agent2.execute).toHaveBeenCalled();
    expect(agent3.execute).toHaveBeenCalled();
  });
  
  test('should handle errors during multi-agent workflow', async () => {
    // Create the manager agent
    const manager = new ManagerAgent('manager', mockMemoryManager);
    
    // Mock _analyzeRequirements method
    manager['_analyzeRequirements'] = jest.fn().mockResolvedValue({
      prompt: 'test prompt',
      extractedRequirements: ['req1']
    });
    
    // Mock _designArchitecture to throw an error
    manager['_designArchitecture'] = jest.fn().mockRejectedValue(new Error('Design error'));
    
    // Execute the manager agent
    const result = await manager.execute('Create a web application');
    
    // Check that the result indicates failure
    expect(result.success).toBe(false);
    expect(result.error).toBeDefined();
    expect(result.error!.message).toContain('Design error');
    
    // Verify that _analyzeRequirements was called but not later methods
    expect(manager['_analyzeRequirements']).toHaveBeenCalled();
  });
});