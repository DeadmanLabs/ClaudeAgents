import { AIMessage, HumanMessage, SystemMessage, BaseMessage } from '@langchain/core/messages';
import { BaseChatMemory } from 'langchain/memory';

/**
 * Mock LangChain memory for testing
 */
export class MockLangChainMemory implements BaseChatMemory {
  messages: BaseMessage[] = [];
  variables: Record<string, any> = { chat_history: [] };
  chatHistory: {
    addUserMessage: (message: string) => void;
    addAIMessage: (message: string) => void;
    getMessages: () => BaseMessage[];
  };
  memory_variables?: string[];
  input_key?: string;
  output_key?: string;
  return_messages?: boolean;
  chat_memory?: any;
  
  /**
   * Initialize the mock LangChain memory
   */
  constructor() {
    this.chatHistory = this;
  }
  
  /**
   * Load memory variables
   * 
   * @param inputs - Input variables
   * @returns Memory variables
   */
  async loadMemoryVariables(inputs: Record<string, any>): Promise<Record<string, any>> {
    return this.variables;
  }
  
  /**
   * Save context
   * 
   * @param inputs - Input variables
   * @param outputs - Output variables
   */
  async saveContext(inputs: Record<string, any>, outputs: Record<string, any>): Promise<void> {
    this.variables.inputs = inputs;
    this.variables.outputs = outputs;
  }
  
  /**
   * Clear memory
   */
  async clear(): Promise<void> {
    this.messages = [];
    this.variables = { chat_history: [] };
  }
  
  /**
   * Add a user message
   * 
   * @param message - Message content
   */
  addUserMessage(message: string): void {
    const msg = new HumanMessage(message);
    this.messages.push(msg);
    this.variables.chat_history = this.messages;
  }
  
  /**
   * Add an AI message
   * 
   * @param message - Message content
   */
  addAIMessage(message: string): void {
    const msg = new AIMessage(message);
    this.messages.push(msg);
    this.variables.chat_history = this.messages;
  }
  
  /**
   * Get all messages
   * 
   * @returns List of messages
   */
  getMessages(): BaseMessage[] {
    return this.messages;
  }
}

/**
 * Mock memory manager for testing
 */
export class MockMemoryManager {
  memory: Record<string, Record<string, any>> = {};
  langchainMemories: Record<string, BaseChatMemory> = {};
  
  /**
   * Store a value in memory
   * 
   * @param agentId - The ID of the agent
   * @param key - The key to store the value under
   * @param value - The value to store
   */
  store(agentId: string, key: string, value: any): void {
    if (!this.memory[agentId]) {
      this.memory[agentId] = {};
    }
    this.memory[agentId][key] = value;
  }
  
  /**
   * Retrieve a value from memory
   * 
   * @param agentId - The ID of the agent
   * @param key - The key to retrieve
   * @returns The stored value if found, undefined otherwise
   */
  retrieve(agentId: string, key: string): any {
    if (this.memory[agentId] && this.memory[agentId][key] !== undefined) {
      return this.memory[agentId][key];
    }
    return undefined;
  }
  
  /**
   * Get all stored values for an agent
   * 
   * @param agentId - The ID of the agent
   * @returns Dictionary of all keys and values for the agent
   */
  getAll(agentId: string): Record<string, any> {
    return this.memory[agentId] || {};
  }
  
  /**
   * Clear stored memory
   * 
   * @param agentId - If provided, clear only this agent's data, otherwise clear all
   */
  clear(agentId?: string): void {
    if (agentId) {
      if (this.memory[agentId]) {
        delete this.memory[agentId];
      }
      if (this.langchainMemories[agentId]) {
        delete this.langchainMemories[agentId];
      }
    } else {
      this.memory = {};
      this.langchainMemories = {};
    }
  }
  
  /**
   * Get a LangChain memory for an agent
   * 
   * @param agentId - The ID of the agent
   * @param memoryType - Type of memory to use
   * @param memoryKey - Key for the memory
   * @returns A mock LangChain memory
   */
  getLangChainMemory(
    agentId: string,
    memoryType: string = "buffer",
    memoryKey: string = "chat_history"
  ): BaseChatMemory {
    if (!this.langchainMemories[agentId]) {
      this.langchainMemories[agentId] = new MockLangChainMemory();
    }
    return this.langchainMemories[agentId];
  }
  
  /**
   * Save a message to the agent's LangChain memory
   * 
   * @param agentId - The ID of the agent
   * @param message - The message content
   * @param role - The role of the message sender
   */
  saveMessageToMemory(agentId: string, message: string, role: string): void {
    const key = `message_${Object.keys(this.getAll(agentId)).length}`;
    this.store(agentId, key, { role, content: message });
  }
}