import fs from 'fs';
import path from 'path';
import pino from 'pino';

const logger = pino({
  transport: {
    target: 'pino-pretty',
    options: {
      colorize: true,
    },
  },
});

type MemoryStore = Record<string, Record<string, unknown>>;

/**
 * Memory manager for maintaining context across agents and sessions.
 * Provides storage and retrieval of data for agents with support for
 * both in-memory and persistent storage.
 */
export class MemoryManager {
  private memoryStore: MemoryStore = {};
  
  /**
   * Initialize the memory manager
   * 
   * @param persistToDisk - Whether to persist memory to disk
   * @param storageDir - Directory for persistent storage
   */
  constructor(
    private readonly persistToDisk: boolean = false,
    private readonly storageDir: string = './memory'
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
        
        if (this.persistToDisk) {
          const filePath = path.join(this.storageDir, `${agentId}.json`);
          if (fs.existsSync(filePath)) {
            fs.unlinkSync(filePath);
          }
        }
      }
    } else {
      this.memoryStore = {};
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
      const filePath = path.join(this.storageDir, `${agentId}.json`);
      fs.writeFileSync(filePath, JSON.stringify(this.memoryStore[agentId]));
      logger.debug(`Saved memory to disk for agent ${agentId}`);
    } catch (error) {
      logger.error(`Failed to save memory to disk for agent ${agentId}: ${error}`);
    }
  }
  
  /**
   * Load agent data from disk
   * 
   * @param agentId - The ID of the agent
   */
  private loadFromDisk(agentId: string): void {
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
  }
}