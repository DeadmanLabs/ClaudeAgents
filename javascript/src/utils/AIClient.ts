import Anthropic from 'anthropic';
import OpenAI from 'openai';
import { logger } from './LoggerSetup';

/**
 * Interface for conversation messages
 */
export interface Message {
  role: string;
  content: string;
}

/**
 * Options for generating responses
 */
export interface GenerateOptions {
  systemPrompt?: string;
  messages?: Message[];
  temperature?: number;
  maxTokens?: number;
  stream?: boolean;
}

/**
 * Client for AI services like Anthropic and OpenAI.
 * Provides a unified interface for working with different
 * AI service providers, with support for streaming responses.
 */
export class AIClient {
  private provider: string;
  private client: Anthropic | OpenAI;

  /**
   * Initialize the AI client
   * 
   * @param provider - The AI provider to use ('anthropic' or 'openai')
   */
  constructor(provider: string = 'anthropic') {
    this.provider = provider.toLowerCase();

    // Initialize appropriate client based on provider
    if (this.provider === 'anthropic') {
      const apiKey = process.env.ANTHROPIC_API_KEY;
      if (!apiKey) {
        logger.warn('ANTHROPIC_API_KEY not found in environment variables');
      }
      this.client = new Anthropic({ apiKey });
    } else if (this.provider === 'openai') {
      const apiKey = process.env.OPENAI_API_KEY;
      if (!apiKey) {
        logger.warn('OPENAI_API_KEY not found in environment variables');
      }
      this.client = new OpenAI({ apiKey });
    } else {
      throw new Error(`Unsupported AI provider: ${provider}`);
    }

    logger.info(`Initialized AI client with provider: ${this.provider}`);
  }

  /**
   * Generate a response from the AI model
   * 
   * @param prompt - The prompt to send to the model
   * @param options - Additional options for the generation
   * @returns Either the complete response text or an async generator that yields response chunks
   */
  async generate(prompt: string, options: GenerateOptions = {}): Promise<string | AsyncGenerator<string, void, unknown>> {
    if (this.provider === 'anthropic') {
      return this.generateAnthropic(prompt, options);
    } else if (this.provider === 'openai') {
      return this.generateOpenAI(prompt, options);
    } else {
      throw new Error(`Unsupported AI provider: ${this.provider}`);
    }
  }

  /**
   * Generate a response using Anthropic's Claude
   * 
   * @param prompt - The prompt to send to the model
   * @param options - Additional options for the generation
   * @returns Either the complete response text or an async generator that yields response chunks
   */
  private async generateAnthropic(
    prompt: string,
    { systemPrompt, messages, temperature = 0.7, maxTokens = 1000, stream = false }: GenerateOptions
  ): Promise<string | AsyncGenerator<string, void, unknown>> {
    const anthropicClient = this.client as Anthropic;

    // Prepare the messages
    let formattedMessages: Anthropic.MessageParam[] = [];
    if (messages) {
      formattedMessages = messages
        .filter(msg => msg.role === 'user' || msg.role === 'assistant')
        .map(msg => ({
          role: msg.role as 'user' | 'assistant',
          content: msg.content
        }));
      
      // Extract system message if present
      const systemMessage = messages.find(msg => msg.role === 'system');
      if (systemMessage) {
        systemPrompt = systemMessage.content;
      }
    } else {
      formattedMessages = [{ role: 'user', content: prompt }];
    }

    try {
      if (stream) {
        // Streaming response
        logger.debug('Generating streaming response from Anthropic');
        const response = await anthropicClient.messages.create({
          model: 'claude-3-haiku-20240307',
          max_tokens: maxTokens,
          temperature,
          system: systemPrompt,
          messages: formattedMessages,
          stream: true
        });

        async function* responseGenerator() {
          for await (const chunk of response) {
            if (chunk.delta.text) {
              yield chunk.delta.text;
            }
          }
        }

        return responseGenerator();
      } else {
        // Non-streaming response
        logger.debug('Generating response from Anthropic');
        const response = await anthropicClient.messages.create({
          model: 'claude-3-haiku-20240307',
          max_tokens: maxTokens,
          temperature,
          system: systemPrompt,
          messages: formattedMessages
        });

        return response.content[0].text;
      }
    } catch (error) {
      logger.error(`Error generating response from Anthropic: ${error}`);
      throw error;
    }
  }

  /**
   * Generate a response using OpenAI's models
   * 
   * @param prompt - The prompt to send to the model
   * @param options - Additional options for the generation
   * @returns Either the complete response text or an async generator that yields response chunks
   */
  private async generateOpenAI(
    prompt: string,
    { systemPrompt, messages, temperature = 0.7, maxTokens = 1000, stream = false }: GenerateOptions
  ): Promise<string | AsyncGenerator<string, void, unknown>> {
    const openaiClient = this.client as OpenAI;

    // Prepare the messages
    let formattedMessages: OpenAI.Chat.ChatCompletionMessageParam[] = [];
    if (messages) {
      formattedMessages = messages.map(msg => ({
        role: msg.role as 'system' | 'user' | 'assistant',
        content: msg.content
      }));
    } else {
      if (systemPrompt) {
        formattedMessages.push({
          role: 'system',
          content: systemPrompt
        });
      }
      formattedMessages.push({
        role: 'user',
        content: prompt
      });
    }

    try {
      if (stream) {
        // Streaming response
        logger.debug('Generating streaming response from OpenAI');
        const response = await openaiClient.chat.completions.create({
          model: 'gpt-3.5-turbo',
          max_tokens: maxTokens,
          temperature,
          messages: formattedMessages,
          stream: true
        });

        async function* responseGenerator() {
          for await (const chunk of response) {
            if (chunk.choices[0]?.delta?.content) {
              yield chunk.choices[0].delta.content;
            }
          }
        }

        return responseGenerator();
      } else {
        // Non-streaming response
        logger.debug('Generating response from OpenAI');
        const response = await openaiClient.chat.completions.create({
          model: 'gpt-3.5-turbo',
          max_tokens: maxTokens,
          temperature,
          messages: formattedMessages
        });

        return response.choices[0].message.content || '';
      }
    } catch (error) {
      logger.error(`Error generating response from OpenAI: ${error}`);
      throw error;
    }
  }
}