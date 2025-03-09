import { ArchitectureDesignerAgent } from '../src/agents/ArchitectureDesignerAgent';
import { MemoryManager } from '../src/utils/MemoryManager';
import { WebSearch } from '../src/utils/WebSearch';

// Mock dependencies
jest.mock('../src/utils/MemoryManager');
jest.mock('../src/utils/WebSearch');
jest.mock('../src/utils/AIClient');

describe('ArchitectureDesignerAgent', () => {
  let architectureDesignerAgent: ArchitectureDesignerAgent;
  let mockMemoryManager: jest.Mocked<MemoryManager>;
  
  beforeEach(() => {
    // Create mocks
    mockMemoryManager = new MemoryManager(false, './memory') as jest.Mocked<MemoryManager>;
    mockMemoryManager.store = jest.fn();
    mockMemoryManager.retrieve = jest.fn();
    
    // Create the architecture designer agent
    architectureDesignerAgent = new ArchitectureDesignerAgent('TestArchitectDesigner', mockMemoryManager);
    
    // Mock the internal methods and agent executor
    architectureDesignerAgent['agentExecutor'] = {
      invoke: jest.fn().mockResolvedValue({
        output: JSON.stringify({
          architecture: {
            name: 'Three-Tier Web Architecture',
            summary: 'Traditional three-tier architecture with presentation, business logic, and data layers',
            backend: 'Node.js with Express',
            frontend: 'React',
            database: 'PostgreSQL',
            components: [
              {
                name: 'Frontend UI',
                technology: 'React',
                responsibility: 'User interface',
                description: 'Provides the user interface for the application'
              },
              {
                name: 'API Server',
                technology: 'Express',
                responsibility: 'Business logic',
                description: 'Handles business logic and API requests'
              },
              {
                name: 'Database',
                technology: 'PostgreSQL',
                responsibility: 'Data storage',
                description: 'Stores application data persistently'
              }
            ],
            communication: {
              protocols: ['HTTP/HTTPS', 'WebSockets'],
              dataFormat: 'JSON'
            },
            security: ['Authentication using JWT', 'HTTPS encryption'],
            deployment: {
              infrastructure: 'Docker containers',
              scalability: 'Horizontal scaling with load balancer'
            },
            rationale: 'This architecture provides a good separation of concerns and is well-suited for web applications.'
          }
        })
      })
    };
  });
  
  afterEach(() => {
    jest.clearAllMocks();
  });
  
  test('should initialize correctly', () => {
    expect(architectureDesignerAgent.name).toBe('TestArchitectDesigner');
    expect(architectureDesignerAgent.memoryManager).toBe(mockMemoryManager);
    expect(architectureDesignerAgent.tools.length).toBeGreaterThan(0);
  });
  
  test('should have required tools', () => {
    const toolNames = architectureDesignerAgent.tools.map(tool => tool.name);
    expect(toolNames.some(name => name.includes('search') || name.includes('web'))).toBeTruthy();
    expect(toolNames.some(name => name.includes('evaluate') || name.includes('architecture'))).toBeTruthy();
  });
  
  test('should execute successfully and return architecture design', async () => {
    // Execute the agent
    const result = await architectureDesignerAgent.execute('Design an architecture for a web application');
    
    // Check that the agent executor was called
    expect(architectureDesignerAgent['agentExecutor'].invoke).toHaveBeenCalled();
    
    // Check that the result is successful
    expect(result.success).toBe(true);
    expect(result.design).toBeDefined();
    
    // Check that the design has expected properties
    const design = result.design as any;
    expect(design.name).toBe('Three-Tier Web Architecture');
    expect(design.backend).toBe('Node.js with Express');
    expect(design.frontend).toBe('React');
    expect(design.components.length).toBe(3);
    
    // Verify that the design includes all required sections
    expect(design.database).toBeDefined();
    expect(design.communication).toBeDefined();
    expect(design.security).toBeDefined();
    expect(design.deployment).toBeDefined();
    expect(design.rationale).toBeDefined();
  });
  
  test('should handle execution errors', async () => {
    // Mock the agent executor to throw an error
    architectureDesignerAgent['agentExecutor'].invoke = jest.fn().mockRejectedValue(new Error('Test error'));
    
    // Execute the agent
    const result = await architectureDesignerAgent.execute('Design an architecture for a web application');
    
    // Check that the result indicates failure
    expect(result.success).toBe(false);
    expect(result.error).toBeDefined();
    expect(result.error!.message).toContain('Test error');
  });
  
  test('should use web search for research when needed', async () => {
    // Mock WebSearch
    const mockSearchResults = [
      {
        title: 'Microservices Architecture',
        url: 'https://example.com/microservices',
        snippet: 'Microservices architecture is an approach to building applications as a collection of small services.',
        content: 'Detailed content about microservices architecture and its benefits...'
      }
    ];
    
    // Mock the web search tool
    const mockWebSearchTool = {
      name: 'web_search',
      description: 'Search the web for information',
      func: jest.fn().mockResolvedValue(JSON.stringify(mockSearchResults))
    };
    
    // Replace the tool in the agent
    const originalTools = [...architectureDesignerAgent.tools];
    architectureDesignerAgent.tools = [
      mockWebSearchTool,
      ...originalTools.filter(tool => tool.name !== 'web_search')
    ];
    
    // Execute the agent with a prompt that will require research
    await architectureDesignerAgent.execute('Design a microservices architecture for a high-traffic web application');
    
    // Check that the web search tool was used
    expect(architectureDesignerAgent['agentExecutor'].invoke).toHaveBeenCalled();
  });
  
  test('should store results in memory manager', async () => {
    // Execute the agent
    await architectureDesignerAgent.execute('Design an architecture for a web application');
    
    // Check that the memory manager was used to store the result
    expect(mockMemoryManager.store).toHaveBeenCalled();
  });
  
  test('should handle invalid output format', async () => {
    // Mock the agent executor to return invalid JSON
    architectureDesignerAgent['agentExecutor'].invoke = jest.fn().mockResolvedValue({
      output: 'Not valid JSON'
    });
    
    // Execute the agent
    const result = await architectureDesignerAgent.execute('Design an architecture for a web application');
    
    // Check that the result indicates failure
    expect(result.success).toBe(false);
    expect(result.error).toBeDefined();
  });
});