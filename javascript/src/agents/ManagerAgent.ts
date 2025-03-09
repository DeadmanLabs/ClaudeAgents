import { BaseAgent, ExecuteResult, AgentConfig } from './BaseAgent';
import { MemoryManager } from '../utils/MemoryManager';
import { logger } from '../utils/LoggerSetup';
import { ArchitectureDesignerAgent } from './ArchitectureDesignerAgent';
import { StackBuilderAgent } from './StackBuilderAgent';
import { LibraryResearcherAgent } from './LibraryResearcherAgent';
import { SoftwarePlannerAgent } from './SoftwarePlannerAgent';
import { SoftwareProgrammerAgent } from './SoftwareProgrammerAgent';
import { ExceptionDebuggerAgent } from './ExceptionDebuggerAgent';
import { DependencyAnalyzerAgent } from './DependencyAnalyzerAgent';
import { z } from 'zod';
import { BaseLanguageModel } from '@langchain/core/language_models/base';
import { BaseChatMemory } from 'langchain/memory';
import { 
  BaseTool,
  DynamicStructuredTool
} from 'langchain/tools';
import {
  ChatPromptTemplate,
  SystemMessagePromptTemplate,
  HumanMessagePromptTemplate
} from '@langchain/core/prompts';
import {
  SystemMessage
} from '@langchain/core/messages';
import { JsonOutputParser } from '@langchain/core/output_parsers';

// Define the requirements schema
const RequirementsSchema = z.object({
  prompt: z.string().describe('The original prompt'),
  extracted_requirements: z.array(z.string()).describe('List of extracted requirements'),
  primary_language: z.string().optional().describe('Primary programming language (if specified)'),
  technologies: z.array(z.string()).optional().describe('List of technologies mentioned in requirements'),
  constraints: z.array(z.string()).optional().describe('List of constraints or limitations')
});

// Type for the requirements
type RequirementsOutput = z.infer<typeof RequirementsSchema>;

/**
 * Final Manager Agent that coordinates all specialized agents.
 * Orchestrates the collaborative workflow between specialized agents using LangChain,
 * delegating tasks and integrating results to produce a complete software solution.
 */
export class ManagerAgent extends BaseAgent {
  private specializedAgents: Record<string, BaseAgent> = {};

  /**
   * Initialize the Manager Agent with LangChain components
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
    
    // Create specialized tools for the manager agent
    const managerTools = this.createManagerTools();
    this.tools.push(...managerTools);
    
    // Re-create the agent executor with the new tools
    this.agentExecutor = this.createAgentExecutor();
  }
  
  /**
   * Override system message for the manager agent
   */
  protected getAgentSystemMessage(): string {
    return `You are a Manager Agent, responsible for coordinating a team of specialized AI agents to deliver complete software solutions.
    
Your primary responsibilities are:
1. Analyze user requirements to determine the needs and constraints
2. Delegate specialized tasks to the appropriate sub-agents
3. Coordinate the workflow between these agents
4. Integrate results into a cohesive solution
5. Ensure all components work together properly
6. Produce comprehensive documentation and summaries

You have access to the following specialized agents:
- Architecture Designer: Creates overall system architecture
- Stack Builder: Defines technology stacks and configurations
- Library Researcher: Identifies optimal libraries and frameworks
- Software Planner: Creates detailed development plans and roadmaps
- Software Programmer: Implements actual code
- Exception Debugger: Detects and fixes potential issues
- Dependency Analyzer: Manages dependencies between components

Work methodically through each step of the software development process, delegating to specialized agents as needed.`;
  }
  
  /**
   * Create specialized tools for the manager agent
   */
  private createManagerTools(): BaseTool[] {
    // Tool for analyzing requirements
    const analyzeRequirementsTool = new DynamicStructuredTool({
      name: 'analyze_requirements',
      description: 'Analyze a user prompt to extract key requirements, constraints, and preferences',
      schema: z.object({
        prompt: z.string().describe('The user input prompt to analyze')
      }),
      func: async ({ prompt }) => {
        const template = `
        Analyze the following user request to extract software requirements:
        
        {prompt}
        
        Extract the key requirements, desired technologies, constraints, and other relevant details.
        
        Your response must be a valid JSON object with the following structure:
        {
          "prompt": "original prompt",
          "extracted_requirements": ["list", "of", "requirements"],
          "primary_language": "language if specified (optional)",
          "technologies": ["tech1", "tech2", "..."],
          "constraints": ["constraint1", "constraint2", "..."]
        }
        `;
        
        const promptTemplate = ChatPromptTemplate.fromMessages([
          SystemMessagePromptTemplate.fromTemplate(template)
        ]);
        
        // Generate the requirements using the LLM with structured output
        const outputParser = new JsonOutputParser<RequirementsOutput>();
        const chain = promptTemplate.pipe(this.llm).pipe(outputParser);
        
        try {
          const result = await chain.invoke({ prompt });
          return JSON.stringify(result);
        } catch (error) {
          logger.error(`Error in requirements analysis: ${error instanceof Error ? error.message : String(error)}`);
          // Return a basic requirements structure as fallback
          return JSON.stringify({
            prompt,
            extracted_requirements: ['Software development', 'Multi-agent system'],
            primary_language: null,
            technologies: [],
            constraints: []
          });
        }
      }
    });
    
    // Tool for processing agent results
    const processAgentResultTool = new DynamicStructuredTool({
      name: 'process_agent_result',
      description: 'Process and validate the result from a specialized agent',
      schema: z.object({
        agent_result: z.string().describe('The JSON string result from an agent'),
        agent_type: z.string().describe('The type of agent that produced the result')
      }),
      func: async ({ agent_result, agent_type }) => {
        const promptTemplate = ChatPromptTemplate.fromMessages([
          new SystemMessage(`
          You are analyzing the output from a ${agent_type} agent.
          Verify that the result is complete, well-structured, and meets expectations.
          
          Extract the key information and return a processed version with any issues noted.
          `),
          HumanMessagePromptTemplate.fromTemplate(`
          Agent result:
          {agent_result}
          
          Process this result and provide a structured analysis in JSON format.
          `)
        ]);
        
        const chain = promptTemplate.pipe(this.llm).pipe(new JsonOutputParser());
        
        try {
          const result = await chain.invoke({
            agent_result
          });
          
          return JSON.stringify(result);
        } catch (error) {
          logger.error(`Error processing agent result: ${error instanceof Error ? error.message : String(error)}`);
          return JSON.stringify({
            status: 'error',
            message: `Failed to process ${agent_type} result: ${error instanceof Error ? error.message : String(error)}`,
            original_data: agent_result
          });
        }
      }
    });
    
    // Tool for creating final summaries
    const createFinalSummaryTool = new DynamicStructuredTool({
      name: 'create_final_summary',
      description: 'Create a comprehensive summary of the complete solution',
      schema: z.object({
        architecture: z.string().describe('The architecture design JSON'),
        libraries: z.string().describe('The library research JSON'),
        software_plan: z.string().describe('The software plan JSON'),
        code_result: z.string().describe('The code generation result JSON'),
        debug_result: z.string().describe('The debugging result JSON'),
        dependency_analysis: z.string().describe('The dependency analysis JSON')
      }),
      func: async ({ 
        architecture, 
        libraries, 
        software_plan, 
        code_result, 
        debug_result, 
        dependency_analysis 
      }) => {
        const promptTemplate = ChatPromptTemplate.fromMessages([
          new SystemMessage(`
          Create a comprehensive summary of the entire software solution based on the provided components.
          
          The summary should integrate all aspects of the project, highlight key decisions, and explain how
          components work together. Structure the response as a JSON object with the following keys:
          - summary: A detailed executive summary of the solution
          - architecture_overview: Key architectural decisions and patterns
          - technology_stack: Summary of technologies, libraries and frameworks
          - implementation_details: How the code implements the requirements
          - testing_validation: Results of debugging and validation
          - next_steps: Recommended future improvements or considerations
          `),
          HumanMessagePromptTemplate.fromTemplate(`
          Architecture Design:
          {architecture}
          
          Library Research:
          {libraries}
          
          Software Plan:
          {software_plan}
          
          Code Result:
          {code_result}
          
          Debug Result:
          {debug_result}
          
          Dependency Analysis:
          {dependency_analysis}
          
          Create a comprehensive summary of this solution:
          `)
        ]);
        
        const chain = promptTemplate.pipe(this.llm).pipe(new JsonOutputParser());
        
        try {
          const result = await chain.invoke({
            architecture,
            libraries,
            software_plan,
            code_result,
            debug_result,
            dependency_analysis
          });
          
          return JSON.stringify(result);
        } catch (error) {
          logger.error(`Error creating final summary: ${error instanceof Error ? error.message : String(error)}`);
          return JSON.stringify({
            summary: 'Multi-agent software development process completed with errors in summary generation.',
            architecture_overview: 'See architecture details in separate section.',
            technology_stack: 'See libraries section for details.',
            implementation_details: 'Implementation completed. See code result for details.',
            testing_validation: 'Testing completed. See debug result for details.',
            next_steps: 'Review the solution components individually.'
          });
        }
      }
    });
    
    return [analyzeRequirementsTool, processAgentResultTool, createFinalSummaryTool];
  }

  /**
   * Execute the manager agent's task, orchestrating all specialized agents
   * 
   * @param prompt - The user input prompt describing the software solution needed
   * @param options - Additional parameters for execution
   * @returns Promise resolving to results of the execution
   */
  public async execute(prompt: string, options?: Record<string, unknown>): Promise<ExecuteResult> {
    logger.info(`Manager Agent ${this.name} starting execution`);
    console.log(`📋 Received prompt: ${prompt.substring(0, 100)}...`);
    console.log('🔄 Starting multi-agent collaboration process...');

    try {
      // Save the original prompt to memory
      this.saveToMemory('original_prompt', prompt);
      this.addToConversation('user', prompt);

      // Step 1: Analyze the prompt to identify requirements
      logger.info('Analyzing prompt to identify requirements');
      console.log('🔍 Analyzing requirements...');
      const requirements = await this.analyzeRequirements(prompt);
      this.saveToMemory('requirements', requirements);

      // Step 2: Design the architecture
      logger.info('Delegating architecture design task');
      console.log('🏗️ Designing architecture...');
      const architecture = await this.designArchitecture(requirements);
      this.saveToMemory('architecture', architecture);

      // Step 3: Research necessary libraries
      logger.info('Researching necessary libraries');
      console.log('📚 Researching libraries...');
      const libraries = await this.researchLibraries(requirements, architecture);
      this.saveToMemory('libraries', libraries);

      // Step 4: Plan the software structure
      logger.info('Planning software structure');
      console.log('📝 Planning software structure...');
      const softwarePlan = await this.planSoftware(requirements, architecture, libraries);
      this.saveToMemory('software_plan', softwarePlan);

      // Step 5: Generate the code
      logger.info('Generating code according to plan');
      console.log('💻 Generating code...');
      const codeResult = await this.generateCode(softwarePlan);
      this.saveToMemory('code_result', codeResult);

      // Step 6: Debug and handle exceptions
      logger.info('Debugging code and handling exceptions');
      console.log('🔧 Debugging code...');
      const debugResult = await this.debugCode(codeResult);
      this.saveToMemory('debug_result', debugResult);

      // Step 7: Analyze dependencies for the final solution
      logger.info('Analyzing dependencies for final solution');
      console.log('🔄 Analyzing dependencies...');
      const dependencyAnalysis = await this.analyzeDependencies();
      this.saveToMemory('dependency_analysis', dependencyAnalysis);

      // Step 8: Produce final summary and integration
      logger.info('Creating final integration and summary');
      console.log('✅ Finalizing solution...');
      const finalResult = await this.createFinalSummary();

      console.log('\n✨ Multi-agent process completed successfully!');
      console.log(`📋 Final solution summary: ${finalResult.summary.substring(0, 100)}...`);

      return {
        success: true,
        result: finalResult,
        message: 'Multi-agent process completed successfully'
      };

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      logger.error(`Manager Agent execution failed: ${errorMessage}`);
      
      return {
        success: false,
        error: error instanceof Error ? error : new Error(errorMessage),
        message: 'Multi-agent process failed'
      };
    }
  }

  /**
   * Analyze the prompt to extract key requirements using LangChain tools
   * 
   * @param prompt - The user input prompt
   * @returns Dictionary of extracted requirements
   */
  private async analyzeRequirements(prompt: string): Promise<Record<string, unknown>> {
    try {
      // Find the analyze_requirements tool
      const analyzeTool = this.tools.find(t => t.name === 'analyze_requirements');
      
      if (!analyzeTool) {
        logger.warn('Analyze requirements tool not found, using basic analysis');
        // Fallback to basic analysis
        return {
          prompt,
          extracted_requirements: [
            'Implement multi-agent system',
            'Support Python and JavaScript',
            'Handle real-time output',
            'Coordinate multiple agents'
          ]
        };
      }
      
      // Use the tool to analyze requirements
      const result = await analyzeTool.invoke({
        prompt
      });
      
      // Parse the JSON result
      return JSON.parse(result as string);
      
    } catch (error) {
      logger.error(`Error analyzing requirements: ${error instanceof Error ? error.message : String(error)}`);
      // Return a basic analysis as fallback
      return {
        prompt,
        extracted_requirements: [
          'Implement multi-agent system',
          'Support Python and JavaScript'
        ],
        primary_language: null,
        technologies: [],
        constraints: []
      };
    }
  }

  /**
   * Delegate architecture design to the ArchitectureDesignerAgent using LangChain
   * 
   * @param requirements - The extracted requirements
   * @returns Architecture design result
   */
  private async designArchitecture(
    requirements: Record<string, unknown>
  ): Promise<Record<string, unknown>> {
    const designer = this.getOrCreateAgent('architecture_designer', ArchitectureDesignerAgent);
    
    // Create a detailed prompt for the architecture designer
    const reqList = (requirements.extracted_requirements as string[])?.join(', ') ?? '';
    const techList = (requirements.technologies as string[])?.join(', ') ?? '';
    const constraints = (requirements.constraints as string[])?.join(', ') ?? '';
    
    const archPrompt = 
      `Design an architecture for the following requirements: ${reqList}. ` +
      `Technologies mentioned: ${techList}. ` +
      `Constraints to consider: ${constraints}. ` +
      `Original request: ${(requirements.prompt as string)?.substring(0, 300) ?? ''}`;
    
    const result = await designer.execute(archPrompt);

    if (!result.success) {
      const errorMsg = result.error?.message || 'Unknown error';
      logger.error(`Architecture design failed: ${errorMsg}`);
      throw new Error(`Architecture design failed: ${errorMsg}`);
    }

    return (result.design as Record<string, unknown>) || {};
  }

  /**
   * Research necessary libraries using the LibraryResearcherAgent with LangChain
   * 
   * @param requirements - The extracted requirements
   * @param architecture - The architecture design
   * @returns Library research result
   */
  private async researchLibraries(
    requirements: Record<string, unknown>,
    architecture: Record<string, unknown>
  ): Promise<Record<string, unknown>> {
    const researcher = this.getOrCreateAgent('library_researcher', LibraryResearcherAgent);

    // Create a prompt for the library researcher
    const reqList = (requirements.extracted_requirements as string[]) || [];
    const primaryLang = requirements.primary_language || 'No specific language';
    
    const libPrompt = 
      `Research libraries for the following architecture: ` +
      `${architecture.summary || 'Not specified'}. ` +
      `Backend: ${architecture.backend || 'Not specified'}. ` +
      `Frontend: ${architecture.frontend || 'Not specified'}. ` +
      `Requirements: ${reqList.join(', ')}. ` +
      `Primary language: ${primaryLang}.`;

    const result = await researcher.execute(libPrompt);

    if (!result.success) {
      const errorMsg = result.error?.message || 'Unknown error';
      logger.error(`Library research failed: ${errorMsg}`);
      throw new Error(`Library research failed: ${errorMsg}`);
    }

    // Process the result using our tool if available
    const processTool = this.tools.find(t => t.name === 'process_agent_result');
    
    if (processTool) {
      try {
        const processedResult = await processTool.invoke({
          agent_result: JSON.stringify(result.libraries || {}),
          agent_type: 'Library Researcher'
        });
        // Try to parse the processed result
        const libraries = JSON.parse(processedResult as string);
        return libraries;
      } catch (error) {
        logger.warn(`Error processing library result: ${error instanceof Error ? error.message : String(error)}`);
      }
    }

    return (result.libraries as Record<string, unknown>) || {};
  }

  /**
   * Plan the software structure using the SoftwarePlannerAgent with LangChain
   * 
   * @param requirements - The extracted requirements
   * @param architecture - The architecture design
   * @param libraries - The researched libraries
   * @returns Software plan result
   */
  private async planSoftware(
    requirements: Record<string, unknown>,
    architecture: Record<string, unknown>,
    libraries: Record<string, unknown>
  ): Promise<Record<string, unknown>> {
    const planner = this.getOrCreateAgent('software_planner', SoftwarePlannerAgent);
    
    // Create a prompt for the software planner
    const reqList = (requirements.extracted_requirements as string[]) || [];
    
    // Extract libraries if they're in a nested format
    let libList: string[] = [];
    if (libraries.selected_libraries && Array.isArray(libraries.selected_libraries)) {
      libList = libraries.selected_libraries as string[];
    } else if (libraries.libraries && Array.isArray(libraries.libraries)) {
      libList = (libraries.libraries as Record<string, unknown>[])
        .map(lib => (lib.name as string) || '')
        .filter(name => name !== '');
    }
    
    const components = (architecture.components as Record<string, unknown>[]) || [];
    const componentNames = components.map(comp => comp.name || 'Unknown').join(', ');
    
    const planPrompt = 
      `Create a software development plan for: ${reqList.join(', ')}. ` +
      `Architecture: ${architecture.summary || 'Not specified'}. ` +
      `Components: ${componentNames}. ` +
      `Using libraries: ${libList.join(', ') || 'No specific libraries'}. ` +
      `Original request: ${(requirements.prompt as string)?.substring(0, 300) ?? ''}`;

    const result = await planner.execute(planPrompt);

    if (!result.success) {
      const errorMsg = result.error?.message || 'Unknown error';
      logger.error(`Software planning failed: ${errorMsg}`);
      throw new Error(`Software planning failed: ${errorMsg}`);
    }

    return (result.plan as Record<string, unknown>) || {};
  }

  /**
   * Generate code using the SoftwareProgrammerAgent with LangChain
   * 
   * @param softwarePlan - The software plan
   * @returns Code generation result
   */
  private async generateCode(
    softwarePlan: Record<string, unknown>
  ): Promise<Record<string, unknown>> {
    const programmer = this.getOrCreateAgent('software_programmer', SoftwareProgrammerAgent);
    
    // Create a prompt for the code generator
    const files = softwarePlan.files;
    let filesStr = '';
    
    if (Array.isArray(files)) {
      filesStr = files.join(', ');
    } else if (files && typeof files === 'object') {
      filesStr = Object.keys(files as Record<string, unknown>).join(', ');
    } else {
      filesStr = 'as needed based on the plan';
    }
    
    const tasks = (softwarePlan.tasks as string[]) || [];
    
    const codePrompt = 
      `Implement the following software plan: ` +
      `${softwarePlan.summary || 'Not specified'}. ` +
      `Files to create: ${filesStr}. ` +
      `Tasks: ${tasks.join(', ') || 'According to plan'}`;

    const result = await programmer.execute(codePrompt);

    if (!result.success) {
      const errorMsg = result.error?.message || 'Unknown error';
      logger.error(`Code generation failed: ${errorMsg}`);
      throw new Error(`Code generation failed: ${errorMsg}`);
    }

    return (result.code as Record<string, unknown>) || {};
  }

  /**
   * Debug code using the ExceptionDebuggerAgent with LangChain
   * 
   * @param codeResult - The generated code
   * @returns Debugging result
   */
  private async debugCode(
    codeResult: Record<string, unknown>
  ): Promise<Record<string, unknown>> {
    const debugger_ = this.getOrCreateAgent('exception_debugger', ExceptionDebuggerAgent);
    
    // Create a prompt for the debugger with code details
    const files = codeResult.files;
    let fileList = '';
    
    if (files && typeof files === 'object') {
      fileList = Object.keys(files as Record<string, unknown>)
        .map(filename => `- ${filename}`)
        .join('\n');
    } else {
      fileList = 'Generated code files';
    }
    
    const debugPrompt = 
      `Debug and validate the following code implementation:\n` +
      `Files generated:\n${fileList}\n` +
      `Check for potential exceptions, bugs, and inconsistencies.`;

    const result = await debugger_.execute(debugPrompt, { code: codeResult });

    if (!result.success) {
      const errorMsg = result.error?.message || 'Unknown error';
      logger.error(`Debugging failed: ${errorMsg}`);
      throw new Error(`Debugging failed: ${errorMsg}`);
    }

    return (result.debug_result as Record<string, unknown>) || {};
  }

  /**
   * Analyze dependencies using the DependencyAnalyzerAgent with LangChain
   * 
   * @returns Dependency analysis result
   */
  private async analyzeDependencies(): Promise<Record<string, unknown>> {
    const analyzer = this.getOrCreateAgent('dependency_analyzer', DependencyAnalyzerAgent);
    
    // Gather all the context for dependency analysis
    const architecture = this.retrieveFromMemory('architecture') as Record<string, unknown> || {};
    const components = (architecture.components as Record<string, unknown>[]) || [];
    const componentNames = components.map(comp => comp.name || 'Unknown').join(', ');
    
    // Create a prompt for the dependency analyzer
    const analyzePrompt = 
      `Analyze dependencies for a project with: ` +
      `Architecture: ${architecture.summary || 'Not specified'}. ` +
      `Components: ${componentNames}. ` +
      `Check version compatibility and dependency conflicts.`;

    const result = await analyzer.execute(analyzePrompt);

    if (!result.success) {
      const errorMsg = result.error?.message || 'Unknown error';
      logger.error(`Dependency analysis failed: ${errorMsg}`);
      throw new Error(`Dependency analysis failed: ${errorMsg}`);
    }

    return (result.analysis as Record<string, unknown>) || {};
  }

  /**
   * Create a final summary of the complete solution using LangChain
   * 
   * @returns Final solution summary
   */
  private async createFinalSummary(): Promise<Record<string, unknown>> {
    // Retrieve all stored data from memory
    const architecture = this.retrieveFromMemory('architecture') as Record<string, unknown> || {};
    const libraries = this.retrieveFromMemory('libraries') as Record<string, unknown> || {};
    const softwarePlan = this.retrieveFromMemory('software_plan') as Record<string, unknown> || {};
    const codeResult = this.retrieveFromMemory('code_result') as Record<string, unknown> || {};
    const debugResult = this.retrieveFromMemory('debug_result') as Record<string, unknown> || {};
    const dependencyAnalysis = this.retrieveFromMemory('dependency_analysis') as Record<string, unknown> || {};
    
    // Use the summary creation tool if available
    const summaryTool = this.tools.find(t => t.name === 'create_final_summary');
    
    if (summaryTool) {
      try {
        const summaryResult = await summaryTool.invoke({
          architecture: JSON.stringify(architecture),
          libraries: JSON.stringify(libraries),
          software_plan: JSON.stringify(softwarePlan),
          code_result: JSON.stringify(codeResult),
          debug_result: JSON.stringify(debugResult),
          dependency_analysis: JSON.stringify(dependencyAnalysis)
        });
        
        // Try to parse the result as JSON
        try {
          const finalResult = JSON.parse(summaryResult as string);
          return finalResult;
        } catch (jsonError) {
          // If it's not valid JSON, create a basic structure with the text
          const summaryText = summaryResult as string;
          return {
            summary: summaryText.length > 500 ? summaryText.substring(0, 500) + '...' : summaryText,
            architecture,
            libraries,
            plan: softwarePlan,
            files: codeResult.files || {},
            debug_info: debugResult,
            dependencies: dependencyAnalysis
          };
        }
        
      } catch (error) {
        logger.error(`Error creating final summary with tool: ${error instanceof Error ? error.message : String(error)}`);
      }
    }
    
    // Fallback to basic summary creation
    // Extract libraries list
    let librariesList: string[] = [];
    if (libraries.selected_libraries && Array.isArray(libraries.selected_libraries)) {
      librariesList = libraries.selected_libraries as string[];
    } else if (libraries.libraries && Array.isArray(libraries.libraries)) {
      librariesList = (libraries.libraries as Record<string, unknown>[])
        .map(lib => (lib.name as string) || '')
        .filter(name => name !== '');
    }
    
    const summary = 
      'Multi-agent software development process completed. ' +
      `Architecture: ${architecture.summary || 'Not specified'}. ` +
      `Libraries used: ${librariesList.join(', ')}. ` +
      `Implementation: ${softwarePlan.summary || 'Not specified'}. ` +
      `Code status: ${debugResult.status || 'Unknown'}. ` +
      `Dependency status: ${dependencyAnalysis.status || 'Unknown'}.`;
    
    // Compile all files and resources
    const files = (codeResult.files as Record<string, unknown>) || {};
    
    return {
      summary,
      architecture,
      libraries,
      plan: softwarePlan,
      files,
      debug_info: debugResult,
      dependencies: dependencyAnalysis
    };
  }

  /**
   * Get an existing agent instance or create a new one with LangChain components
   * 
   * @param agentKey - Key to store/retrieve the agent under
   * @param AgentClass - Class of the agent to create
   * @returns An instance of the requested agent
   */
  private getOrCreateAgent<T extends BaseAgent>(
    agentKey: string, 
    AgentClass: new (
      name: string, 
      memoryManager?: MemoryManager, 
      config?: AgentConfig,
      llm?: BaseLanguageModel,
      tools?: BaseTool[],
      memory?: BaseChatMemory,
      verbose?: boolean
    ) => T
  ): T {
    if (!this.specializedAgents[agentKey]) {
      logger.debug(`Creating new agent instance: ${AgentClass.name}`);
      
      // Create new agent with LangChain components and our memory manager for storage
      this.specializedAgents[agentKey] = new AgentClass(
        `${agentKey}_${this.id.substring(0, 8)}`,
        this.memoryManager,
        this.config,
        this.llm,  // Share the same LLM for consistency
        undefined,  // Let each agent define its own tools
        undefined,  // Let each agent define its own memory
        this.verbose
      );
    }
    
    return this.specializedAgents[agentKey] as T;
  }
}