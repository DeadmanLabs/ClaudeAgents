import { MemoryManager } from '../src/utils/MemoryManager';
import fs from 'fs';
import path from 'path';

// Mock dependencies
jest.mock('fs');
jest.mock('path');

describe('MemoryManager', () => {
  let memoryManager: MemoryManager;
  const testStorageDir = './test-memory';
  
  beforeEach(() => {
    // Reset mocks
    jest.clearAllMocks();
    
    // Mock path.join to return predictable paths
    (path.join as jest.Mock).mockImplementation((...args) => {
      return args.join('/');
    });
    
    // Mock existsSync and mkdirSync for directory checks/creation
    (fs.existsSync as jest.Mock).mockReturnValue(true);
    (fs.mkdirSync as jest.Mock).mockImplementation(() => {});
  });
  
  describe('In-memory storage (no persistence)', () => {
    beforeEach(() => {
      memoryManager = new MemoryManager(false);
    });
    
    test('should store and retrieve values', () => {
      const agentId = 'test-agent';
      const key = 'test-key';
      const value = { data: 'test-value' };
      
      memoryManager.store(agentId, key, value);
      const retrievedValue = memoryManager.retrieve(agentId, key);
      
      expect(retrievedValue).toEqual(value);
    });
    
    test('should return null for non-existent keys', () => {
      const agentId = 'test-agent';
      const key = 'non-existent-key';
      
      const retrievedValue = memoryManager.retrieve(agentId, key);
      expect(retrievedValue).toBeNull();
    });
    
    test('should clear specific agent memory', () => {
      const agentId1 = 'agent-1';
      const agentId2 = 'agent-2';
      const key = 'test-key';
      const value = 'test-value';
      
      memoryManager.store(agentId1, key, value);
      memoryManager.store(agentId2, key, value);
      
      memoryManager.clear(agentId1);
      
      expect(memoryManager.retrieve(agentId1, key)).toBeNull();
      expect(memoryManager.retrieve(agentId2, key)).toEqual(value);
    });
    
    test('should clear all memory', () => {
      const agentId1 = 'agent-1';
      const agentId2 = 'agent-2';
      const key = 'test-key';
      const value = 'test-value';
      
      memoryManager.store(agentId1, key, value);
      memoryManager.store(agentId2, key, value);
      
      memoryManager.clear();
      
      expect(memoryManager.retrieve(agentId1, key)).toBeNull();
      expect(memoryManager.retrieve(agentId2, key)).toBeNull();
    });
    
    test('should get all memory for an agent', () => {
      const agentId = 'test-agent';
      const key1 = 'key-1';
      const key2 = 'key-2';
      const value1 = 'value-1';
      const value2 = 'value-2';
      
      memoryManager.store(agentId, key1, value1);
      memoryManager.store(agentId, key2, value2);
      
      const allMemory = memoryManager.getAll(agentId);
      
      expect(allMemory).toEqual({
        [key1]: value1,
        [key2]: value2
      });
    });
    
    test('should return empty object for non-existent agent', () => {
      const agentId = 'non-existent-agent';
      
      const allMemory = memoryManager.getAll(agentId);
      
      expect(allMemory).toEqual({});
    });
  });
  
  describe('Persistent storage', () => {
    beforeEach(() => {
      memoryManager = new MemoryManager(true, testStorageDir);
      
      // Mock file read/write operations
      (fs.writeFileSync as jest.Mock).mockImplementation(() => {});
      (fs.readFileSync as jest.Mock).mockImplementation((filePath) => {
        if (filePath.includes('agent-1.json')) {
          return JSON.stringify({ 'key-1': 'value-1' });
        }
        throw new Error('File not found');
      });
    });
    
    test('should create storage directory if it does not exist', () => {
      // Mock directory not existing
      (fs.existsSync as jest.Mock).mockReturnValue(false);
      
      // Re-initialize the memory manager
      memoryManager = new MemoryManager(true, testStorageDir);
      
      expect(fs.mkdirSync).toHaveBeenCalledWith(testStorageDir, { recursive: true });
    });
    
    test('should save to disk when storing a value', () => {
      const agentId = 'test-agent';
      const key = 'test-key';
      const value = { data: 'test-value' };
      
      memoryManager.store(agentId, key, value);
      
      expect(fs.writeFileSync).toHaveBeenCalled();
      const callArgs = (fs.writeFileSync as jest.Mock).mock.calls[0];
      expect(callArgs[0]).toContain(`${agentId}.json`);
      expect(JSON.parse(callArgs[1])).toEqual({ [key]: value });
    });
    
    test('should load from disk when retrieving a value', () => {
      const agentId = 'agent-1';
      const key = 'key-1';
      
      const value = memoryManager.retrieve(agentId, key);
      
      expect(fs.readFileSync).toHaveBeenCalled();
      expect(value).toEqual('value-1');
    });
    
    test('should handle disk read errors gracefully', () => {
      const agentId = 'agent-error';
      const key = 'key';
      
      // Mock readFileSync to throw an error
      (fs.readFileSync as jest.Mock).mockImplementation(() => {
        throw new Error('Test error');
      });
      
      const value = memoryManager.retrieve(agentId, key);
      
      expect(value).toBeNull();
    });
    
    test('should delete files when clearing memory', () => {
      // Mock fs.readdirSync to return file list
      (fs.readdirSync as jest.Mock).mockReturnValue(['agent-1.json', 'agent-2.json']);
      
      memoryManager.clear();
      
      // Check that unlinkSync was called for each file
      expect(fs.unlinkSync).toHaveBeenCalledTimes(2);
    });
    
    test('should delete specific agent file when clearing agent memory', () => {
      const agentId = 'agent-1';
      
      memoryManager.clear(agentId);
      
      // Check that unlinkSync was called once for the agent file
      expect(fs.unlinkSync).toHaveBeenCalledTimes(1);
      expect((fs.unlinkSync as jest.Mock).mock.calls[0][0]).toContain(`${agentId}.json`);
    });
  });
  
  describe('LangChain memory integration', () => {
    beforeEach(() => {
      memoryManager = new MemoryManager(false);
    });
    
    test('should create and retrieve LangChain memory', () => {
      const agentId = 'test-agent';
      
      const memory = memoryManager.getLangChainMemory(agentId);
      
      expect(memory).toBeDefined();
      expect(memory.memoryKey).toBe('chat_history');
      
      // Get the same memory again to test caching
      const memory2 = memoryManager.getLangChainMemory(agentId);
      expect(memory2).toBe(memory);
    });
    
    test('should support different memory types', () => {
      const agentId = 'test-agent';
      
      const bufferMemory = memoryManager.getLangChainMemory(agentId, 'buffer');
      expect(bufferMemory).toBeDefined();
      expect(bufferMemory.memoryKey).toBe('chat_history');
      
      // Get a different memory type for the same agent
      const summaryMemory = memoryManager.getLangChainMemory(agentId, 'summary');
      expect(summaryMemory).toBeDefined();
      expect(summaryMemory).not.toBe(bufferMemory);
    });
    
    test('should save messages to LangChain memory', () => {
      const agentId = 'test-agent';
      const message = 'Hello, world!';
      
      // Create a new memory instance
      const memory = memoryManager.getLangChainMemory(agentId);
      
      // Mock the memory's chat_memory.addUserMessage method
      memory.chatMemory = {
        addUserMessage: jest.fn(),
        addAIMessage: jest.fn()
      };
      
      // Save a user message
      memoryManager.saveMessageToMemory(agentId, message, 'user');
      expect(memory.chatMemory.addUserMessage).toHaveBeenCalledWith(message);
      
      // Save an assistant message
      memoryManager.saveMessageToMemory(agentId, message, 'assistant');
      expect(memory.chatMemory.addAIMessage).toHaveBeenCalledWith(message);
    });
    
    test('should get conversation history', () => {
      const agentId = 'test-agent';
      
      // Create a memory instance with mock conversation history
      const memory = memoryManager.getLangChainMemory(agentId);
      memory.chatMemory = {
        messages: [
          { type: 'human', content: 'Hello' },
          { type: 'ai', content: 'Hi there' }
        ]
      };
      
      // Get conversation history as messages
      const history = memoryManager.getConversationHistory(agentId, true);
      expect(history).toEqual([
        { type: 'human', content: 'Hello' },
        { type: 'ai', content: 'Hi there' }
      ]);
      
      // Get conversation history as text
      const historyText = memoryManager.getConversationHistory(agentId, false);
      expect(typeof historyText).toBe('string');
      expect(historyText).toContain('Hello');
      expect(historyText).toContain('Hi there');
    });
  });
});