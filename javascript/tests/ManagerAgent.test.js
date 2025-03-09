const { ManagerAgent } = require('../src/agents/ManagerAgent');
const { MemoryManager } = require('../src/utils/MemoryManager');

// Mock dependencies
jest.mock('../src/utils/MemoryManager');
jest.mock('../src/agents/ArchitectureDesignerAgent');
jest.mock('../src/agents/StackBuilderAgent');
jest.mock('../src/agents/LibraryResearcherAgent');
jest.mock('../src/agents/SoftwarePlannerAgent');
jest.mock('../src/agents/SoftwareProgrammerAgent');
jest.mock('../src/agents/ExceptionDebuggerAgent');
jest.mock('../src/agents/DependencyAnalyzerAgent');

describe('ManagerAgent', () => {
  let managerAgent;
  let mockMemoryManager;
  
  beforeEach(() => {
    // Create mocks
    mockMemoryManager = new MemoryManager();
    mockMemoryManager.store = jest.fn();
    mockMemoryManager.retrieve = jest.fn();
    
    // Create the manager agent
    managerAgent = new ManagerAgent('TestManager', mockMemoryManager);
    
    // Mock the internal methods
    managerAgent._analyzeRequirements = jest.fn().mockResolvedValue({
      prompt: 'test prompt',
      extractedRequirements: ['requirement1', 'requirement2'],
      technologies: ['tech1', 'tech2']
    });
    
    managerAgent._designArchitecture = jest.fn().mockResolvedValue({
      summary: 'Architecture design summary'
    });
    
    managerAgent._researchLibraries = jest.fn().mockResolvedValue({
      libraries: [{ name: 'lib1', description: 'Library 1' }]
    });
    
    managerAgent._planSoftware = jest.fn().mockResolvedValue({
      summary: 'Software plan summary',
      tasks: ['task1', 'task2']
    });
    
    managerAgent._generateCode = jest.fn().mockResolvedValue({
      files: { 'file1.js': 'code content' }
    });
    
    managerAgent._debugCode = jest.fn().mockResolvedValue({
      status: 'success',
      issues: []
    });
    
    managerAgent._analyzeDependencies = jest.fn().mockResolvedValue({
      status: 'success',
      dependencies: []
    });
    
    managerAgent._createFinalSummary = jest.fn().mockResolvedValue({
      summary: 'Final summary'
    });
  });
  
  afterEach(() => {
    jest.clearAllMocks();
  });
  
  test('should initialize correctly', () => {
    expect(managerAgent.name).toBe('TestManager');
    expect(managerAgent.memoryManager).toBe(mockMemoryManager);
    expect(managerAgent.specializedAgents).toEqual({});
    expect(managerAgent.tools.length).toBeGreaterThan(0);
  });
  
  test('should have required manager tools', () => {
    const toolNames = managerAgent.tools.map(tool => tool.name);
    expect(toolNames).toContain('analyze_requirements');
    expect(toolNames).toContain('process_agent_result');
    expect(toolNames).toContain('create_final_summary');
  });
  
  test('should execute the full workflow', async () => {
    // Execute the manager agent
    const result = await managerAgent.execute('test prompt');
    
    // Check that the result is successful
    expect(result.success).toBe(true);
    expect(result.result.summary).toBe('Final summary');
    
    // Check that all methods were called in the correct order
    expect(managerAgent._analyzeRequirements).toHaveBeenCalledWith('test prompt');
    expect(managerAgent._designArchitecture).toHaveBeenCalled();
    expect(managerAgent._researchLibraries).toHaveBeenCalled();
    expect(managerAgent._planSoftware).toHaveBeenCalled();
    expect(managerAgent._generateCode).toHaveBeenCalled();
    expect(managerAgent._debugCode).toHaveBeenCalled();
    expect(managerAgent._analyzeDependencies).toHaveBeenCalled();
    expect(managerAgent._createFinalSummary).toHaveBeenCalled();
    
    // Check that data was saved to memory
    expect(mockMemoryManager.store).toHaveBeenCalledTimes(8);
  });
  
  test('should handle errors during execution', async () => {
    // Make a method throw an error
    managerAgent._designArchitecture.mockRejectedValue(new Error('Test error'));
    
    // Execute the manager agent
    const result = await managerAgent.execute('test prompt');
    
    // Check that the result indicates failure
    expect(result.success).toBe(false);
    expect(result.error).toContain('Test error');
    
    // Check that only methods before the error were called
    expect(managerAgent._analyzeRequirements).toHaveBeenCalled();
    expect(managerAgent._designArchitecture).toHaveBeenCalled();
    expect(managerAgent._researchLibraries).not.toHaveBeenCalled();
  });
  
  test('should create specialized agents when needed', () => {
    // Mock the getOrCreateAgent method
    const mockArchitectAgent = { name: 'MockArchitectAgent' };
    managerAgent._getOrCreateAgent = jest.fn().mockReturnValue(mockArchitectAgent);
    
    // Call a method that uses _getOrCreateAgent
    managerAgent._designArchitecture({});
    
    // Check that _getOrCreateAgent was called with the correct parameters
    expect(managerAgent._getOrCreateAgent).toHaveBeenCalledWith('architecture_designer', expect.any(Function));
  });
});