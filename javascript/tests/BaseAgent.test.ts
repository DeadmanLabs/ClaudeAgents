import { describe, expect, test, jest, beforeEach } from '@jest/globals';
import { BaseAgent } from '../src/agents/BaseAgent';
import { MockLLM } from './helpers/mockLLM';
import { MockMemoryManager } from './helpers/mockMemoryManager';

// Concrete implementation of BaseAgent for testing
class TestAgent extends BaseAgent {
  constructor(
    name: string,
    memoryManager?: any,
    config: Record<string, unknown> = {},
    llm?: any,
    tools?: any[],
    memory?: any,
    verbose?: boolean
  ) {
    super(name, memoryManager, config, llm, tools, memory, verbose);
  }

  // Execute is already implemented in the BaseAgent class
}

describe('BaseAgent', () => {
  let mockLLM: MockLLM;
  let mockMemoryManager: MockMemoryManager;
  
  beforeEach(() => {
    mockLLM = new MockLLM({
      'Test prompt': 'This is a test response',
      'Design an architecture': '{"summary": "Microservices architecture", "components": [{"name": "API Gateway"}]}'
    });
    
    mockMemoryManager = new MockMemoryManager();
  });
  
  test('initialization', () => {
    const agent = new TestAgent(
      'test_agent',
      mockMemoryManager,
      { testKey: 'test_value' },
      mockLLM
    );
    
    // Check that the agent was initialized correctly
    expect(agent.name).toBe('test_agent');
    expect(agent.id).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/);
    expect(mockLLM).toBeDefined();
    expect(agent.tools).toEqual([]);
  });
  
  test('save and retrieve from memory', () => {
    const agent = new TestAgent('test_agent', mockMemoryManager);
    
    // Save data to memory
    agent.saveToMemory('test_key', 'test_value');
    
    // Retrieve data from memory
    const value = agent.retrieveFromMemory('test_key');
    
    // Check that the data was saved and retrieved correctly
    expect(value).toBe('test_value');
  });
  
  test('add to conversation', () => {
    const agent = new TestAgent('test_agent', mockMemoryManager);
    
    // Add messages to the conversation
    agent.addToConversation('user', 'Hello');
    agent.addToConversation('assistant', 'Hi there');
    agent.addToConversation('system', 'Test system message');
    
    // Check that the messages were added correctly
    expect(agent['conversationHistory'].length).toBe(3);
    expect(agent['conversationHistory'][0]).toEqual({ role: 'user', content: 'Hello' });
    expect(agent['conversationHistory'][1]).toEqual({ role: 'assistant', content: 'Hi there' });
    expect(agent['conversationHistory'][2]).toEqual({ role: 'system', content: 'Test system message' });
  });
  
  test('get agent system message', () => {
    const agent = new TestAgent('test_agent');
    
    // Get the system message
    const systemMessage = agent['getAgentSystemMessage']();
    
    // Check that the system message contains the agent's name
    expect(systemMessage).toContain('test_agent');
  });
  
  test('create agent executor', () => {
    const agent = new TestAgent(
      'test_agent',
      mockMemoryManager,
      {},
      mockLLM,
      []
    );
    
    // Create the agent executor
    const executor = agent['createAgentExecutor']();
    
    // Check that the executor was created correctly
    expect(executor).toBeDefined();
    expect(executor.agent).toBeDefined();
    expect(executor.tools).toBeDefined();
  });
  
  test('execute successfully', async () => {
    const agent = new TestAgent(
      'test_agent',
      mockMemoryManager,
      {},
      mockLLM
    );
    
    // Mock the agent executor's invoke method
    const mockInvoke = jest.fn().mockResolvedValue({
      output: 'Test response',
      intermediateSteps: []
    });
    
    agent['agentExecutor'] = {
      invoke: mockInvoke
    } as any;
    
    // Execute the agent
    const result = await agent.execute('Test prompt');
    
    // Check that the agent executor was called
    expect(mockInvoke).toHaveBeenCalledWith({ input: 'Test prompt' });
    
    // Check that the result has the expected format
    expect(result.success).toBe(true);
    expect(result.data).toBe('Test response');
    
    // Check that the conversation history was updated
    expect(agent['conversationHistory'].length).toBe(2);
    expect(agent['conversationHistory'][0].role).toBe('user');
    expect(agent['conversationHistory'][0].content).toBe('Test prompt');
    expect(agent['conversationHistory'][1].role).toBe('assistant');
    expect(agent['conversationHistory'][1].content).toBe('Test response');
  });
  
  test('execute with error', async () => {
    const agent = new TestAgent(
      'test_agent',
      mockMemoryManager,
      {},
      mockLLM
    );
    
    // Mock the agent executor's invoke method to throw an error
    const mockError = new Error('Test error');
    const mockInvoke = jest.fn().mockRejectedValue(mockError);
    
    agent['agentExecutor'] = {
      invoke: mockInvoke
    } as any;
    
    // Execute the agent
    const result = await agent.execute('Test prompt');
    
    // Check that the agent executor was called
    expect(mockInvoke).toHaveBeenCalledWith({ input: 'Test prompt' });
    
    // Check that the result indicates failure
    expect(result.success).toBe(false);
    expect(result.error).toBe(mockError);
  });
});