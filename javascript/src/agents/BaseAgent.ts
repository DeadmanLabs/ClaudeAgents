import { randomUUID } from 'crypto';
import pino from 'pino';
import { 
  AgentExecutor, 
  createConversationalAgent, 
  AgentStep
} from "langchain/agents";
import { 
  ChatPromptTemplate,
  MessagesPlaceholder,
  HumanMessagePromptTemplate,
  SystemMessagePromptTemplate
} from "@langchain/core/prompts";
import { 
  BaseLanguageModel 
} from "@langchain/core/language_models/base";
import { 
  ChatAnthropic 
} from "@langchain/anthropic";
import { 
  ChatOpenAI 
} from "@langchain/openai";
import {
  BaseChatMemory,
  ChatMessageHistory,
  ConversationSummaryMemory
} from "langchain/memory";
import {
  HumanMessage,
  SystemMessage,
  AIMessage,
  BaseMessage
} from "@langchain/core/messages";
import { 
  BaseTool,
  ToolParams,
  Tool
} from "@langchain/core/tools";
import { RunnableConfig } from "@langchain/core/runnables";
import { getEnv } from '../utils/EnvLoader';

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
 * Uses LangChain components to power the agent's functionality.
 */
export abstract class BaseAgent {
  public readonly id: string;
  protected conversationHistory: ConversationMessage[] = [];
  
  // LangChain components
  protected llm: BaseLanguageModel;
  protected tools: BaseTool[];
  protected memory: BaseChatMemory;
  protected agentExecutor: AgentExecutor;
  protected verbose: boolean;
  
  /**
   * Initialize a new agent
   * 
   * @param name - A unique name for this agent instance
   * @param memoryManager - The memory manager for storing context
   * @param config - Configuration parameters for the agent
   * @param llm - The language model to use for this agent
   * @param tools - List of tools the agent can use
   * @param memory - LangChain memory instance for conversation history
   * @param verbose - Whether to output verbose logging
   */
  constructor(
    public readonly name: string,
    protected readonly memoryManager?: MemoryManager,
    protected readonly config: AgentConfig = {},
    llm?: BaseLanguageModel,
    tools?: BaseTool[],
    memory?: BaseChatMemory,
    verbose?: boolean
  ) {
    this.id = randomUUID();
    this.verbose = verbose ?? false;
    
    // Initialize LangChain components
    this.llm = llm ?? this.getDefaultLLM();
    this.tools = tools ?? [];
    this.memory = memory ?? new ConversationSummaryMemory({
      memoryKey: "chat_history",
      llm: this.llm,
      returnMessages: true,
    });
    
    // Create the agent executor
    this.agentExecutor = this.createAgentExecutor();
    
    logger.info(`Initialized ${this.constructor.name} - ${this.name} (${this.id})`);
  }
  
  /**
   * Get the default language model based on config or environment variables
   */
  protected getDefaultLLM(): BaseLanguageModel {
    // Get provider from config or .env or default to anthropic
    const provider = (this.config.provider as string || getEnv("DEFAULT_PROVIDER", "anthropic")).toLowerCase();
    
    if (provider === "anthropic") {
      let apiKey = getEnv("ANTHROPIC_API_KEY");
      if (!apiKey) {
        logger.warn("ANTHROPIC_API_KEY not found in environment variables or .env file");
        // For demo purposes only - use OpenAI as fallback if ANTHROPIC_API_KEY not found
        const openaiApiKey = getEnv("OPENAI_API_KEY");
        if (openaiApiKey) {
          logger.info("Falling back to OpenAI since ANTHROPIC_API_KEY is not set");
          const model = getEnv("DEFAULT_MODEL", "gpt-3.5-turbo");
          const temp = parseFloat(getEnv("DEFAULT_TEMPERATURE", "0.7"));
          return new ChatOpenAI({
            modelName: this.config.model as string || model,
            temperature: this.config.temperature as number || temp,
            openAIApiKey: openaiApiKey,
          });
        } else {
          // Use a dummy API key for testing - this will not make actual API calls
          // but allows the code to initialize for demonstration purposes
          logger.warn("Using dummy API key for demo purposes - no actual API calls will work");
          apiKey = "dummy_sk_ant_for_initialization";
        }
      }
      
      const model = getEnv("DEFAULT_MODEL", "claude-3-haiku-20240307");
      const temp = parseFloat(getEnv("DEFAULT_TEMPERATURE", "0.7"));
      return new ChatAnthropic({
        modelName: this.config.model as string || model,
        temperature: this.config.temperature as number || temp,
        anthropicApiKey: apiKey,
      });
    } else if (provider === "openai") {
      let apiKey = getEnv("OPENAI_API_KEY");
      if (!apiKey) {
        logger.warn("OPENAI_API_KEY not found in environment variables or .env file");
        // For demo purposes only - use Anthropic as fallback if OPENAI_API_KEY not found
        const anthropicApiKey = getEnv("ANTHROPIC_API_KEY");
        if (anthropicApiKey) {
          logger.info("Falling back to Anthropic since OPENAI_API_KEY is not set");
          const model = getEnv("DEFAULT_MODEL", "claude-3-haiku-20240307");
          const temp = parseFloat(getEnv("DEFAULT_TEMPERATURE", "0.7"));
          return new ChatAnthropic({
            modelName: this.config.model as string || model,
            temperature: this.config.temperature as number || temp,
            anthropicApiKey: anthropicApiKey,
          });
        } else {
          // Use a dummy API key for testing - this will not make actual API calls
          // but allows the code to initialize for demonstration purposes
          logger.warn("Using dummy API key for demo purposes - no actual API calls will work");
          apiKey = "dummy_sk_openai_for_initialization";
        }
      }
      
      const model = getEnv("DEFAULT_MODEL", "gpt-3.5-turbo");
      const temp = parseFloat(getEnv("DEFAULT_TEMPERATURE", "0.7"));
      return new ChatOpenAI({
        modelName: this.config.model as string || model,
        temperature: this.config.temperature as number || temp,
        openAIApiKey: apiKey,
      });
    } else {
      throw new Error(`Unsupported AI provider: ${provider}`);
    }
  }
  
  /**
   * Get the system message for this agent type.
   * Override this in subclasses to provide specialized instructions.
   */
  protected getAgentSystemMessage(): string {
    return `You are ${this.name}, an AI assistant specialized for software development tasks.
    Answer the human's questions to the best of your ability.`;
  }
  
  /**
   * Create the LangChain agent executor for this agent
   */
  protected createAgentExecutor(): AgentExecutor {
    // Create prompt template with system message and tools
    const systemMessage = this.getAgentSystemMessage();
    
    const prompt = ChatPromptTemplate.fromMessages([
      SystemMessagePromptTemplate.fromTemplate(systemMessage),
      new MessagesPlaceholder("chat_history"),
      HumanMessagePromptTemplate.fromTemplate("{input}"),
      new MessagesPlaceholder("agent_scratchpad"),
    ]);
    
    // Create the agent
    const agent = createConversationalAgent({
      llm: this.llm,
      tools: this.tools,
      prompt: prompt
    });
    
    return new AgentExecutor({
      agent,
      tools: this.tools,
      memory: this.memory,
      verbose: this.verbose,
      handleParsingErrors: true
    });
  }
  
  /**
   * Execute the agent's main task based on a prompt
   * 
   * @param prompt - The input prompt or task description
   * @param options - Additional parameters for execution
   * @returns Promise resolving to results of the agent's execution
   */
  async execute(prompt: string, options?: Record<string, unknown>): Promise<ExecuteResult> {
    try {
      // Default implementation using LangChain agent executor
      const result = await this.agentExecutor.invoke({
        input: prompt,
      });
      
      // Add the interaction to the conversation history (for backward compatibility)
      this.addToConversation("user", prompt);
      this.addToConversation("assistant", String(result.output || ""));
      
      return {
        success: true,
        data: result.output,
        raw_result: result
      };
    } catch (error) {
      logger.error(`Error in agent execution: ${(error as Error).message}`);
      return {
        success: false,
        error: error as Error
      };
    }
  }
  
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
    // Add to old-style conversation history for backward compatibility
    this.conversationHistory.push({ role, content });
    
    // Convert to LangChain message format and add to memory
    if (role === "user") {
      this.memory.chatHistory.addUserMessage(content);
    } else if (role === "assistant") {
      this.memory.chatHistory.addAIMessage(content);
    }
    // LangChain memory doesn't typically store system messages in chat history
  }
}