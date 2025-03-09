import fs from 'fs';
import path from 'path';
import pino from 'pino';
import {
  BaseChatMemory,
  ConversationBufferMemory,
  ConversationSummaryMemory,
  CombinedMemory,
  EntityMemory
} from 'langchain/memory';
import {
  AIMessage,
  HumanMessage,
  SystemMessage,
  BaseMessage
} from '@langchain/core/messages';
import { BaseLanguageModel } from '@langchain/core/language_models/base';
import { ChatMessageHistory } from 'langchain/stores/message/in_memory';

const logger = pino({
  transport: {
    target: 'pino-pretty',
    options: {
      colorize: true,
    },
  },
});

type MemoryStore = Record<string, Record<string, unknown>>;
type LangChainMemoryStore = Record<string, BaseChatMemory>;
type ConversationMessage = {
  role: string;
  content: string;
};

/**
 * Memory manager for maintaining context across agents and sessions.
 * Provides storage and retrieval of data for agents with support for
 * both in-memory and persistent storage and integration with LangChain.
 */
export class MemoryManager {
  private memoryStore: MemoryStore = {};
  private langchainMemories: LangChainMemoryStore = {};
  
  /**
   * Initialize the memory manager
   * 
   * @param persistToDisk - Whether to persist memory to disk
   * @param storageDir - Directory for persistent storage
   * @param llm - Optional language model for memory operations
   */
  constructor(
    private readonly persistToDisk: boolean = false,
    private readonly storageDir: string = './memory',
    private readonly llm?: BaseLanguageModel
  ) {
    if (persistToDisk) {
      try {
        if (!fs.existsSync(storageDir)) {
          fs.mkdirSync(storageDir, { recursive: true });
        }
        logger.info(`Memory manager initialized with persistence at ${storageDir}`);
      } catch (error) {
        logger.error(`Failed to create storage directory: ${error}`);
        throw new Error(`Failed to create storage directory: ${error}`);
      }
    } else {
      logger.info('Memory manager initialized with in-memory storage only');
    }
  }
  
  /**
   * Store a value in memory
   * 
   * @param agentId - The ID of the agent storing the data
   * @param key - The key to store the value under
   * @param value - The value to store
   */
  public store(agentId: string, key: string, value: unknown): void {
    if (!this.memoryStore[agentId]) {
      this.memoryStore[agentId] = {};
    }
    
    this.memoryStore[agentId][key] = value;
    logger.debug(`Stored value for agent ${agentId} under key '${key}'`);
    
    if (this.persistToDisk) {
      this.saveToDisk(agentId);
    }
  }
  
  /**
   * Retrieve a value from memory
   * 
   * @param agentId - The ID of the agent retrieving the data
   * @param key - The key to retrieve
   * @returns The stored value if found, undefined otherwise
   */
  public retrieve(agentId: string, key: string): unknown {
    // If we're using persistence and don't have this agent's data in memory, try to load it
    if (this.persistToDisk && !this.memoryStore[agentId]) {
      this.loadFromDisk(agentId);
    }
    
    if (this.memoryStore[agentId] && this.memoryStore[agentId][key] !== undefined) {
      logger.debug(`Retrieved value for agent ${agentId} under key '${key}'`);
      return this.memoryStore[agentId][key];
    }
    
    logger.debug(`No value found for agent ${agentId} under key '${key}'`);
    return undefined;
  }
  
  /**
   * Get all stored values for an agent
   * 
   * @param agentId - The ID of the agent
   * @returns Dictionary of all keys and values for the agent
   */
  public getAll(agentId: string): Record<string, unknown> {
    // If we're using persistence and don't have this agent's data in memory, try to load it
    if (this.persistToDisk && !this.memoryStore[agentId]) {
      this.loadFromDisk(agentId);
    }
    
    return this.memoryStore[agentId] || {};
  }
  
  /**
   * Clear stored memory
   * 
   * @param agentId - If provided, clear only this agent's data, otherwise clear all
   */
  public clear(agentId?: string): void {
    if (agentId) {
      if (this.memoryStore[agentId]) {
        delete this.memoryStore[agentId];
        logger.info(`Cleared memory for agent ${agentId}`);
        
        if (this.langchainMemories[agentId]) {
          delete this.langchainMemories[agentId];
          logger.info(`Cleared LangChain memory for agent ${agentId}`);
        }
        
        if (this.persistToDisk) {
          // Clear regular memory file
          const filePath = path.join(this.storageDir, `${agentId}.json`);
          if (fs.existsSync(filePath)) {
            fs.unlinkSync(filePath);
          }
          
          // Clear LangChain memory file
          const lcFilePath = path.join(this.storageDir, `${agentId}_langchain.json`);
          if (fs.existsSync(lcFilePath)) {
            fs.unlinkSync(lcFilePath);
          }
        }
      }
    } else {
      this.memoryStore = {};
      this.langchainMemories = {};
      logger.info('Cleared all memory');
      
      if (this.persistToDisk) {
        try {
          const files = fs.readdirSync(this.storageDir);
          for (const file of files) {
            if (file.endsWith('.json')) {
              fs.unlinkSync(path.join(this.storageDir, file));
            }
          }
        } catch (error) {
          logger.error(`Failed to clear disk storage: ${error}`);
        }
      }
    }
  }
  
  /**
   * Save agent data to disk
   * 
   * @param agentId - The ID of the agent
   */
  private saveToDisk(agentId: string): void {
    try {
      // Save regular memory
      const filePath = path.join(this.storageDir, `${agentId}.json`);
      fs.writeFileSync(filePath, JSON.stringify(this.memoryStore[agentId]));
      logger.debug(`Saved memory to disk for agent ${agentId}`);
      
      // Save LangChain memory if it exists
      if (this.langchainMemories[agentId]) {
        // We need to handle serialization of LangChain memory differently
        // First, extract the messages from the memory's chatHistory
        try {
          const lcFilePath = path.join(this.storageDir, `${agentId}_langchain.json`);
          const chatHistory = this.getSerializableChatHistory(agentId);
          fs.writeFileSync(lcFilePath, JSON.stringify(chatHistory));
          logger.debug(`Saved LangChain memory to disk for agent ${agentId}`);
        } catch (error) {
          logger.error(`Failed to save LangChain memory to disk for agent ${agentId}: ${error}`);
        }
      }
    } catch (error) {
      logger.error(`Failed to save memory to disk for agent ${agentId}: ${error}`);
    }
  }
  
  /**
   * Get serializable chat history from a LangChain memory
   * 
   * @param agentId - The ID of the agent
   * @returns Array of serializable messages
   */
  private getSerializableChatHistory(agentId: string): ConversationMessage[] {
    const memory = this.langchainMemories[agentId];
    if (!memory) return [];
    
    try {
      // Try to access chat_memory
      const chatMemory = (memory as any).chatMemory;
      if (chatMemory && Array.isArray(chatMemory.messages)) {
        return chatMemory.messages.map((msg: BaseMessage) => ({
          role: this.getMessageRole(msg),
          content: msg.content
        }));
      }
      
      // Try getting memory variables
      if (typeof memory.loadMemoryVariables === 'function') {
        const vars = memory.loadMemoryVariables({});
        // Check if it's a Promise and handle accordingly
        if (vars instanceof Promise) {
          // We can't do async here, so we'll have to fall back to a stored history
          const storedHistory = this.retrieve(agentId, 'conversation_history');
          if (Array.isArray(storedHistory)) {
            return storedHistory as ConversationMessage[];
          }
          return [];
        }
        
        // If it's the actual variables, try to extract messages
        if (vars.chat_history && Array.isArray(vars.chat_history)) {
          return vars.chat_history.map((msg: BaseMessage) => ({
            role: this.getMessageRole(msg),
            content: msg.content
          }));
        }
      }
      
      // Fall back to stored history
      const storedHistory = this.retrieve(agentId, 'conversation_history');
      if (Array.isArray(storedHistory)) {
        return storedHistory as ConversationMessage[];
      }
      
      return [];
    } catch (error) {
      logger.error(`Error getting serializable chat history: ${error}`);
      return [];
    }
  }
  
  /**
   * Get the role from a LangChain message
   * 
   * @param message - A LangChain message
   * @returns The message role as a string
   */
  private getMessageRole(message: BaseMessage): string {
    if (message instanceof HumanMessage) {
      return 'user';
    } else if (message instanceof AIMessage) {
      return 'assistant';
    } else if (message instanceof SystemMessage) {
      return 'system';
    } else {
      return 'unknown';
    }
  }
  
  /**
   * Load agent data from disk
   * 
   * @param agentId - The ID of the agent
   */
  private loadFromDisk(agentId: string): void {
    // Load regular memory
    const filePath = path.join(this.storageDir, `${agentId}.json`);
    if (fs.existsSync(filePath)) {
      try {
        const fileContent = fs.readFileSync(filePath, 'utf8');
        this.memoryStore[agentId] = JSON.parse(fileContent);
        logger.debug(`Loaded memory from disk for agent ${agentId}`);
      } catch (error) {
        logger.error(`Failed to load memory from disk for agent ${agentId}: ${error}`);
        // Initialize empty object if load fails
        this.memoryStore[agentId] = {};
      }
    }
    
    // Load LangChain memory if it exists
    const lcFilePath = path.join(this.storageDir, `${agentId}_langchain.json`);
    if (fs.existsSync(lcFilePath)) {
      try {
        const fileContent = fs.readFileSync(lcFilePath, 'utf8');
        const chatHistory = JSON.parse(fileContent) as ConversationMessage[];
        
        // We'll store this in the regular memory for now
        // and create a proper LangChain memory when getLangChainMemory is called
        this.store(agentId, 'conversation_history', chatHistory);
        logger.debug(`Loaded serialized LangChain memory for agent ${agentId}`);
      } catch (error) {
        logger.error(`Failed to load LangChain memory from disk for agent ${agentId}: ${error}`);
      }
    }
  }
  
  // LangChain Memory Integration
  
  /**
   * Get a LangChain memory for an agent
   * 
   * @param agentId - The ID of the agent
   * @param memoryType - Type of memory to use ('buffer', 'summary', 'entity', or 'combined')
   * @param memoryKey - Key for the memory in output context
   * @returns A LangChain memory instance
   */
  public getLangChainMemory(
    agentId: string, 
    memoryType: 'buffer' | 'summary' | 'entity' | 'combined' = 'buffer',
    memoryKey: string = 'chat_history'
  ): BaseChatMemory {
    // Check if we already have a memory for this agent
    if (this.langchainMemories[agentId]) {
      return this.langchainMemories[agentId];
    }
    
    // Create a new memory based on the type
    let memory: BaseChatMemory;
    
    if (memoryType === 'buffer') {
      memory = new ConversationBufferMemory({
        memoryKey: memoryKey,
        returnMessages: true
      });
    } else if (memoryType === 'summary') {
      if (!this.llm) {
        logger.warning('No LLM provided for summary memory, falling back to buffer memory');
        memory = new ConversationBufferMemory({
          memoryKey: memoryKey,
          returnMessages: true
        });
      } else {
        memory = new ConversationSummaryMemory({
          llm: this.llm,
          memoryKey: memoryKey,
          returnMessages: true
        });
      }
    } else if (memoryType === 'entity') {
      if (!this.llm) {
        logger.warning('No LLM provided for entity memory, falling back to buffer memory');
        memory = new ConversationBufferMemory({
          memoryKey: memoryKey,
          returnMessages: true
        });
      } else {
        memory = new EntityMemory({
          llm: this.llm,
          entityCache: {},
          entitiesKey: 'entities',
          chatHistoryKey: memoryKey
        });
      }
    } else if (memoryType === 'combined') {
      if (!this.llm) {
        logger.warning('No LLM provided for combined memory, falling back to buffer memory');
        memory = new ConversationBufferMemory({
          memoryKey: memoryKey,
          returnMessages: true
        });
      } else {
        const bufferMemory = new ConversationBufferMemory({
          memoryKey: 'chat_history',
          returnMessages: true
        });
        const summaryMemory = new ConversationSummaryMemory({
          llm: this.llm,
          memoryKey: 'summary_history',
          returnMessages: true
        });
        memory = new CombinedMemory({
          memories: [bufferMemory, summaryMemory],
          chatHistory: new ChatMessageHistory()
        });
      }
    } else {
      // Default to buffer memory
      memory = new ConversationBufferMemory({
        memoryKey: memoryKey,
        returnMessages: true
      });
    }
    
    // Load any existing chat history from regular memory
    const existingHistory = this.retrieve(agentId, 'conversation_history');
    if (existingHistory && Array.isArray(existingHistory)) {
      try {
        // Initialize the chat history with stored messages
        const chatHistory = existingHistory as ConversationMessage[];
        for (const msg of chatHistory) {
          if (msg.role === 'user') {
            memory.chatHistory.addUserMessage(msg.content);
          } else if (msg.role === 'assistant') {
            memory.chatHistory.addAIMessage(msg.content);
          }
          // System messages typically aren't stored in chat history
        }
        logger.debug(`Loaded ${chatHistory.length} messages into LangChain memory for agent ${agentId}`);
      } catch (error) {
        logger.error(`Error loading chat history into LangChain memory: ${error}`);
      }
    }
    
    // Store the memory
    this.langchainMemories[agentId] = memory;
    logger.info(`Created new ${memoryType} memory for agent ${agentId}`);
    
    // Persist if needed
    if (this.persistToDisk) {
      this.saveToDisk(agentId);
    }
    
    return memory;
  }
  
  /**
   * Save a message to the agent's LangChain memory
   * 
   * @param agentId - The ID of the agent
   * @param message - The message content
   * @param role - The role of the message sender ('user', 'assistant', 'system')
   */
  public saveMessageToMemory(agentId: string, message: string, role: string): void {
    // Get or create the agent's memory
    const memory = this.getLangChainMemory(agentId);
    
    // Add message to regular memory store too
    let conversationHistory = this.retrieve(agentId, 'conversation_history') as ConversationMessage[];
    if (!conversationHistory || !Array.isArray(conversationHistory)) {
      conversationHistory = [];
    }
    
    conversationHistory.push({ role, content: message });
    this.store(agentId, 'conversation_history', conversationHistory);
    
    // Add the message to the LangChain memory
    try {
      if (role === 'user') {
        memory.chatHistory.addUserMessage(message);
      } else if (role === 'assistant') {
        memory.chatHistory.addAIMessage(message);
      } else if (role === 'system') {
        // Some memory implementations don't support system messages directly
        // Store system messages in a separate key
        const timestamp = new Date().toISOString();
        this.store(agentId, `system_message_${timestamp}`, message);
      }
      
      logger.debug(`Added ${role} message to LangChain memory for agent ${agentId}`);
      
      // Persist if needed
      if (this.persistToDisk) {
        this.saveToDisk(agentId);
      }
    } catch (error) {
      logger.error(`Error saving message to LangChain memory: ${error}`);
    }
  }
  
  /**
   * Get the conversation history for an agent
   * 
   * @param agentId - The ID of the agent
   * @param asMessages - Whether to return as LangChain messages or serialized
   * @returns Conversation history as messages or serialized objects
   */
  public async getConversationHistory(
    agentId: string, 
    asMessages: boolean = false
  ): Promise<BaseMessage[] | ConversationMessage[]> {
    try {
      // First try to get from LangChain memory
      if (this.langchainMemories[agentId]) {
        const memory = this.langchainMemories[agentId];
        
        if (memory.chatHistory) {
          const messages = memory.chatHistory.getMessages();
          
          if (asMessages) {
            return messages;
          } else {
            // Convert to serializable format
            return messages.map(msg => ({
              role: this.getMessageRole(msg),
              content: msg.content
            }));
          }
        }
        
        // Try to load from memory variables
        if (typeof memory.loadMemoryVariables === 'function') {
          try {
            const vars = await memory.loadMemoryVariables({});
            if (vars.chat_history && Array.isArray(vars.chat_history)) {
              if (asMessages) {
                return vars.chat_history;
              } else {
                return vars.chat_history.map(msg => ({
                  role: this.getMessageRole(msg),
                  content: msg.content
                }));
              }
            }
          } catch (error) {
            logger.error(`Error loading memory variables: ${error}`);
          }
        }
      }
      
      // Fall back to regular memory
      const history = this.retrieve(agentId, 'conversation_history') as ConversationMessage[];
      if (history && Array.isArray(history)) {
        if (asMessages) {
          // Convert to LangChain message format
          return history.map(msg => {
            if (msg.role === 'user') {
              return new HumanMessage(msg.content);
            } else if (msg.role === 'assistant') {
              return new AIMessage(msg.content);
            } else if (msg.role === 'system') {
              return new SystemMessage(msg.content);
            } else {
              // Default to human message for unknown roles
              return new HumanMessage(msg.content);
            }
          });
        } else {
          return history;
        }
      }
      
      // Return empty history if nothing found
      return [];
    } catch (error) {
      logger.error(`Error getting conversation history: ${error}`);
      return [];
    }
  }
}