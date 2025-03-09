import { BaseAgent, ExecuteResult, AgentConfig } from './BaseAgent';
import { logger } from '../utils/LoggerSetup';
import { MemoryManager } from '../utils/MemoryManager';
import { BaseLanguageModel } from '@langchain/core/language_models/base';
import { BaseChatMemory } from 'langchain/memory';
import {
  BaseTool,
  tool
} from '@langchain/core/tools';
import {
  StructuredTool,
  DynamicStructuredTool
} from 'langchain/tools';
import {
  SystemMessagePromptTemplate,
  ChatPromptTemplate,
  HumanMessagePromptTemplate
} from '@langchain/core/prompts';
import { z } from 'zod';
import { zodToJsonSchema } from 'zod-to-json-schema';
import { SystemMessage } from '@langchain/core/messages';
import { JsonOutputParser } from '@langchain/core/output_parsers';

// Define the component schema
const ComponentSchema = z.object({
  name: z.string().describe('Name of the component'),
  technology: z.string().describe('Technology used for the component'),
  responsibility: z.string().describe('Primary responsibility of the component')
});

// Define the architecture design schema
const ArchitectureDesignSchema = z.object({
  summary: z.string().describe('Brief summary of the overall architecture'),
  backend: z.string().describe('Description of backend technologies'),
  frontend: z.string().describe('Description of frontend technologies'),
  database: z.string().describe('Description of data storage technologies'),
  deployment: z.string().describe('Deployment strategy'),
  components: z.array(ComponentSchema).describe('List of key components in the architecture'),
  rationale: z.string().describe('Explanation of why this architecture was chosen'),
  messaging: z.string().optional().describe('Messaging or event systems if applicable')
});

// Type for the architecture design
type ArchitectureDesign = z.infer<typeof ArchitectureDesignSchema>;

/**
 * Architecture Designer Agent
 * 
 * Responsible for generating an infrastructure stack design
 * based on the user's requirements using LangChain components.
 */
export class ArchitectureDesignerAgent extends BaseAgent {
  /**
   * Initialize the Architecture Designer Agent
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
    name: string,
    memoryManager?: MemoryManager,
    config: AgentConfig = {},
    llm?: BaseLanguageModel,
    tools?: BaseTool[],
    memory?: BaseChatMemory,
    verbose?: boolean
  ) {
    super(name, memoryManager, config, llm, tools, memory, verbose);
    
    // Create architecture design tools
    const architectureTools = this.createArchitectureTools();
    this.tools.push(...architectureTools);
    
    // Re-create the agent executor with the new tools
    this.agentExecutor = this.createAgentExecutor();
  }
  
  /**
   * Override system message for the architecture designer agent
   */
  protected getAgentSystemMessage(): string {
    return `You are an expert Architecture Designer Agent specialized in software and infrastructure architecture.

Your task is to analyze requirements and design an optimal architecture stack that meets those requirements.
You should consider:
- Scalability, maintainability, and performance needs
- Technology compatibility and integration points
- Deployment and operational concerns
- Security and compliance requirements
- Cost considerations where specified

Provide clear, structured output including components, technologies, and rationale for your choices.
Be specific about technologies and versions where appropriate.`;
  }
  
  /**
   * Create specialized tools for architecture design tasks
   */
  private createArchitectureTools(): BaseTool[] {
    // Tool to design architecture based on requirements
    const designArchitectureTool = new DynamicStructuredTool({
      name: 'design_architecture',
      description: 'Design a complete software architecture based on the provided requirements',
      schema: z.object({
        requirements: z.string().describe('Detailed requirements for the architecture design')
      }),
      func: async ({ requirements }) => {
        // Create a specialized prompt for architecture design
        const template = `
        You are tasked with designing a complete software architecture based on these requirements:
        
        {requirements}
        
        Analyze these requirements and create a comprehensive architecture design.
        
        Your response must be a valid JSON object with the following structure:
        {
          "summary": "brief description of the architecture",
          "backend": "description of backend technologies",
          "frontend": "description of frontend technologies",
          "database": "description of data storage technologies",
          "deployment": "deployment strategy",
          "components": [
            {
              "name": "component name",
              "technology": "technology used",
              "responsibility": "component responsibility"
            }
          ],
          "rationale": "explanation of why this architecture was chosen",
          "messaging": "messaging or event systems (optional)"
        }
        `;
        
        const prompt = ChatPromptTemplate.fromMessages([
          SystemMessagePromptTemplate.fromTemplate(template)
        ]);
        
        // Generate the architecture using the LLM with structured output
        const outputParser = new JsonOutputParser<ArchitectureDesign>();
        
        const chain = prompt.pipe(this.llm).pipe(outputParser);
        
        try {
          const result = await chain.invoke({
            requirements: requirements
          });
          
          // Validate the result against our schema
          const validatedResult = ArchitectureDesignSchema.parse(result);
          return JSON.stringify(validatedResult);
        } catch (error) {
          logger.error(`Error in architecture design: ${error instanceof Error ? error.message : String(error)}`);
          // Return a basic architecture as fallback
          return JSON.stringify({
            summary: 'Error occurred during architecture design',
            backend: 'Generic backend services',
            frontend: 'Generic frontend',
            database: 'Appropriate database for requirements',
            deployment: 'Standard deployment',
            components: [
              {
                name: 'Core Service',
                technology: 'Recommended technology',
                responsibility: 'Core functionality'
              }
            ],
            rationale: 'Fallback design due to error in processing'
          });
        }
      }
    });
    
    // Tool to evaluate an architecture design
    const evaluateArchitectureTool = new DynamicStructuredTool({
      name: 'evaluate_architecture',
      description: 'Evaluate an architecture design against the provided requirements',
      schema: z.object({
        architecture_json: z.string().describe('JSON string of the architecture to evaluate'),
        requirements: z.string().describe('The requirements to evaluate against')
      }),
      func: async ({ architecture_json, requirements }) => {
        const prompt = ChatPromptTemplate.fromMessages([
          new SystemMessage(`
          You are an architecture evaluation expert. Evaluate the provided architecture against the requirements.
          Identify strengths, weaknesses, and provide suggestions for improvement.
          
          Format your response as:
          
          {
              "strengths": ["list", "of", "strengths"],
              "weaknesses": ["list", "of", "weaknesses"],
              "suggestions": ["list", "of", "improvements"]
          }
          `),
          HumanMessagePromptTemplate.fromTemplate(`
          Requirements:
          {requirements}
          
          Architecture:
          {architecture}
          
          Provide your evaluation:
          `)
        ]);
        
        // Generate the evaluation using the LLM
        const chain = prompt.pipe(this.llm).pipe(new JsonOutputParser());
        
        try {
          const result = await chain.invoke({
            requirements: requirements,
            architecture: architecture_json
          });
          
          return JSON.stringify(result);
        } catch (error) {
          logger.error(`Error in architecture evaluation: ${error instanceof Error ? error.message : String(error)}`);
          return JSON.stringify({
            strengths: ['Unable to evaluate strengths'],
            weaknesses: ['Error during evaluation'],
            suggestions: ['Retry evaluation']
          });
        }
      }
    });
    
    return [designArchitectureTool, evaluateArchitectureTool];
  }
  
  /**
   * Execute the agent's main task - designing an architecture stack
   * 
   * @param prompt - The input prompt describing requirements
   * @param options - Additional parameters for execution
   * @returns Promise resolving to architecture design results
   */
  public async execute(prompt: string, options?: Record<string, unknown>): Promise<ExecuteResult> {
    logger.info(`Architecture Designer Agent ${this.name} executing with prompt: ${prompt.substring(0, 100)}...`);
    
    try {
      // Use the LangChain agent to handle the execution
      const result = await super.execute(prompt, options);
      
      // If successful, try to parse the design from the result
      if (result.success) {
        try {
          // Try to extract structured architecture from the response
          const rawOutput = String(result.data || '');
          
          // Look for JSON in the output
          let architectureJson: string;
          const jsonMatch = rawOutput.match(/```json\n([\s\S]*?)\n```/);
          
          if (jsonMatch) {
            architectureJson = jsonMatch[1];
          } else {
            // Try to find any JSON-like structure
            const jsonObjectMatch = rawOutput.match(/({[\s\S]*})/);
            architectureJson = jsonObjectMatch ? jsonObjectMatch[1] : rawOutput;
          }
          
          // Parse the JSON
          let architecture = JSON.parse(architectureJson);
          
          // If it doesn't have the expected structure, use the tool directly
          if (!architecture.summary || !architecture.backend || !architecture.frontend) {
            logger.info('Using architecture design tool directly');
            
            // Find the design tool
            const designTool = this.tools.find(t => t.name === 'design_architecture');
            if (designTool) {
              const designResult = await designTool.invoke({
                requirements: prompt
              });
              
              architecture = JSON.parse(designResult as string);
            }
          }
          
          // Add the parsed architecture to the result
          result.design = architecture;
          result.message = 'Architecture design completed successfully';
          
        } catch (parseError) {
          logger.warn(`Error parsing architecture design: ${parseError instanceof Error ? parseError.message : String(parseError)}`);
          
          // Try to use the design tool directly
          try {
            // Find the design tool
            const designTool = this.tools.find(t => t.name === 'design_architecture');
            if (designTool) {
              const designResult = await designTool.invoke({
                requirements: prompt
              });
              
              const architecture = JSON.parse(designResult as string);
              result.design = architecture;
              result.message = 'Architecture design completed using fallback';
            }
          } catch (toolError) {
            logger.error(`Design tool error: ${toolError instanceof Error ? toolError.message : String(toolError)}`);
            result.design = {
              summary: 'Error occurred during architecture design',
              backend: 'Generic backend services',
              frontend: 'Generic frontend',
              database: 'Appropriate database for requirements',
              deployment: 'Standard deployment',
              components: [
                {
                  name: 'Core Service',
                  technology: 'Recommended technology',
                  responsibility: 'Core functionality'
                }
              ],
              rationale: 'Fallback design due to error in processing'
            };
            result.message = 'Architecture design fallback used due to errors';
          }
        }
      }
      
      return result;
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      logger.error(`Architecture design failed: ${errorMessage}`);
      
      return {
        success: false,
        error: error instanceof Error ? error : new Error(errorMessage),
        message: 'Architecture design failed'
      };
    }
  }
}