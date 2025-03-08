import { randomUUID } from 'crypto';
import pino from 'pino';

const logger = pino({
  transport: {
    target: 'pino-pretty',
    options: {
      colorize: true,
    },
  },
});

export interface ConversationMessage {
  role: string;
  content: string;
}

export interface MemoryManager {
  store(agentId: string, key: string, value: unknown): void;
  retrieve(agentId: string, key: string): unknown;
}

export interface AgentConfig {
  [key: string]: unknown;
}

export interface ExecuteResult {
  success: boolean;
  data?: unknown;
  error?: Error;
  [key: string]: unknown;
}

/**
 * Base abstract class for all agents in the system.
 * Defines the common interface and functionality that all specialized agents must implement.
 */
export abstract class BaseAgent {
  public readonly id: string;
  protected conversationHistory: ConversationMessage[] = [];
  
  /**
   * Initialize a new agent
   * 
   * @param name - A unique name for this agent instance
   * @param memoryManager - The memory manager for storing context
   * @param config - Configuration parameters for the agent
   */
  constructor(
    public readonly name: string,
    protected readonly memoryManager?: MemoryManager,
    protected readonly config: AgentConfig = {}
  ) {
    this.id = randomUUID();
    logger.info(`Initialized ${this.constructor.name} - ${this.name} (${this.id})`);
  }
  
  /**
   * Execute the agent's main task based on a prompt
   * 
   * @param prompt - The input prompt or task description
   * @param options - Additional parameters for execution
   * @returns Promise resolving to results of the agent's execution
   */
  abstract execute(prompt: string, options?: Record<string, unknown>): Promise<ExecuteResult>;
  
  /**
   * Save data to the agent's memory manager
   * 
   * @param key - Key to store the value under
   * @param value - Data to store
   */
  protected saveToMemory(key: string, value: unknown): void {
    if (this.memoryManager) {
      this.memoryManager.store(this.id, key, value);
      logger.debug(`Agent ${this.name} stored data under key '${key}'`);
    }
  }
  
  /**
   * Retrieve data from the agent's memory manager
   * 
   * @param key - Key to retrieve data for
   * @returns The stored data if found, undefined otherwise
   */
  protected retrieveFromMemory(key: string): unknown {
    if (this.memoryManager) {
      const data = this.memoryManager.retrieve(this.id, key);
      logger.debug(`Agent ${this.name} retrieved data for key '${key}'`);
      return data;
    }
    return undefined;
  }
  
  /**
   * Add a message to the conversation history
   * 
   * @param role - The role of the message sender (e.g., "user", "agent", "system")
   * @param content - The message content
   */
  protected addToConversation(role: string, content: string): void {
    this.conversationHistory.push({ role, content });
  }
}