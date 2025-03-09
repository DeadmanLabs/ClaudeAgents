import { BaseLanguageModel } from '@langchain/core/language_models/base';

/**
 * Mock LLM for testing that returns predefined responses
 */
export class MockLLM implements BaseLanguageModel {
  responses: Record<string, string>;
  invokeCount: number;
  invokeInputs: string[];
  invocation_params: any;
  
  /**
   * Initialize the mock LLM with predefined responses
   * 
   * @param responses - Map of prompts to responses
   */
  constructor(responses: Record<string, string> = {}) {
    this.responses = responses;
    this.invokeCount = 0;
    this.invokeInputs = [];
    this.invocation_params = {};
  }
  
  /**
   * Mock the invoke method to return predefined responses
   * 
   * @param prompt - Input prompt
   * @param options - Additional options
   * @returns Predefined response or default response
   */
  async invoke(prompt: string, options?: any): Promise<string> {
    this.invokeCount += 1;
    this.invokeInputs.push(prompt);
    
    // Check for exact matches in responses
    if (this.responses[prompt]) {
      return this.responses[prompt];
    }
    
    // Check for substring matches
    for (const [key, response] of Object.entries(this.responses)) {
      if (prompt.includes(key)) {
        return response;
      }
    }
    
    // Default response
    return `Mock LLM response for: ${prompt.substring(0, 30)}...`;
  }
  
  /**
   * Mock the predict method
   * 
   * @param text - Input text
   * @param options - Additional options
   * @returns Predefined response
   */
  async predict(text: string, options?: any): Promise<string> {
    return this.invoke(text, options);
  }
  
  /**
   * Get the token count for input text
   * 
   * @param text - Input text
   * @returns Number of tokens (simplified to word count)
   */
  getNumTokens(text: string): number {
    return text.split(/\s+/).length;
  }
  
  /**
   * Generate LLM result from multiple prompts
   * 
   * @param prompts - Array of prompts
   * @param options - Additional options
   * @returns Generation results
   */
  async generate(prompts: string[], options?: any): Promise<any> {
    const generations = [];
    for (const prompt of prompts) {
      const result = await this.invoke(prompt, options);
      generations.push([{ text: result }]);
    }
    return { generations };
  }
  
  /**
   * Get the type of the model
   */
  _llmType(): string {
    return 'mock-llm';
  }
  
  /**
   * Get the identifying parameters
   */
  _identifyingParams(): Record<string, any> {
    return { responses: Object.keys(this.responses) };
  }
}