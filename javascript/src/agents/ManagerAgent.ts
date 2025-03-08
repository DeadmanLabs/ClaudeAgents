import { BaseAgent, ExecuteResult } from './BaseAgent';
import { MemoryManager } from '../utils/MemoryManager';
import { logger } from '../utils/LoggerSetup';
import { ArchitectureDesignerAgent } from './ArchitectureDesignerAgent';
import { StackBuilderAgent } from './StackBuilderAgent';
import { LibraryResearcherAgent } from './LibraryResearcherAgent';
import { SoftwarePlannerAgent } from './SoftwarePlannerAgent';
import { SoftwareProgrammerAgent } from './SoftwareProgrammerAgent';
import { ExceptionDebuggerAgent } from './ExceptionDebuggerAgent';
import { DependencyAnalyzerAgent } from './DependencyAnalyzerAgent';

/**
 * Final Manager Agent that coordinates all specialized agents.
 * Orchestrates the collaborative workflow between specialized agents,
 * delegating tasks and integrating results to produce a complete software solution.
 */
export class ManagerAgent extends BaseAgent {
  private specializedAgents: Record<string, BaseAgent> = {};

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
      const finalResult = this.createFinalSummary();

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
   * Analyze the prompt to extract key requirements
   * 
   * @param prompt - The user input prompt
   * @returns Dictionary of extracted requirements
   */
  private async analyzeRequirements(prompt: string): Promise<Record<string, unknown>> {
    // This would typically involve NLP processing or a specialized agent
    // For now, we'll use a simple placeholder
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

  /**
   * Delegate architecture design to the ArchitectureDesignerAgent
   * 
   * @param requirements - The extracted requirements
   * @returns Architecture design result
   */
  private async designArchitecture(
    requirements: Record<string, unknown>
  ): Promise<Record<string, unknown>> {
    const designer = this.getOrCreateAgent('architecture_designer', ArchitectureDesignerAgent);
    const prompt = requirements.prompt as string;
    const archPrompt = `Design an architecture for: ${prompt.substring(0, 500)}`;
    
    const result = await designer.execute(archPrompt);

    if (!result.success) {
      const errorMsg = result.error?.message || 'Unknown error';
      logger.error(`Architecture design failed: ${errorMsg}`);
      throw new Error(`Architecture design failed: ${errorMsg}`);
    }

    return (result.design as Record<string, unknown>) || {};
  }

  /**
   * Research necessary libraries using the LibraryResearcherAgent
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
    const reqList = requirements.extracted_requirements as string[];
    const libPrompt = 
      `Research libraries for the following architecture: ` +
      `${architecture.summary || 'Not specified'}. ` +
      `Requirements: ${reqList.join(', ')}`;

    const result = await researcher.execute(libPrompt);

    if (!result.success) {
      const errorMsg = result.error?.message || 'Unknown error';
      logger.error(`Library research failed: ${errorMsg}`);
      throw new Error(`Library research failed: ${errorMsg}`);
    }

    return (result.libraries as Record<string, unknown>) || {};
  }

  /**
   * Plan the software structure using the SoftwarePlannerAgent
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
    const prompt = requirements.prompt as string;
    const libList = (libraries.selected_libraries as string[]) || [];
    
    const planPrompt = 
      `Create a software plan for: ${prompt.substring(0, 500)}. ` +
      `Architecture: ${architecture.summary || 'Not specified'}. ` +
      `Using libraries: ${libList.join(', ')}`;

    const result = await planner.execute(planPrompt);

    if (!result.success) {
      const errorMsg = result.error?.message || 'Unknown error';
      logger.error(`Software planning failed: ${errorMsg}`);
      throw new Error(`Software planning failed: ${errorMsg}`);
    }

    return (result.plan as Record<string, unknown>) || {};
  }

  /**
   * Generate code using the SoftwareProgrammerAgent
   * 
   * @param softwarePlan - The software plan
   * @returns Code generation result
   */
  private async generateCode(
    softwarePlan: Record<string, unknown>
  ): Promise<Record<string, unknown>> {
    const programmer = this.getOrCreateAgent('software_programmer', SoftwareProgrammerAgent);
    
    // Create a prompt for the code generator
    const fileList = (softwarePlan.files as string[]) || [];
    
    const codePrompt = 
      `Implement the following software plan: ` +
      `${softwarePlan.summary || 'Not specified'}. ` +
      `Files to create: ${fileList.join(', ')}`;

    const result = await programmer.execute(codePrompt);

    if (!result.success) {
      const errorMsg = result.error?.message || 'Unknown error';
      logger.error(`Code generation failed: ${errorMsg}`);
      throw new Error(`Code generation failed: ${errorMsg}`);
    }

    return (result.code as Record<string, unknown>) || {};
  }

  /**
   * Debug code using the ExceptionDebuggerAgent
   * 
   * @param codeResult - The generated code
   * @returns Debugging result
   */
  private async debugCode(
    codeResult: Record<string, unknown>
  ): Promise<Record<string, unknown>> {
    const debugger_ = this.getOrCreateAgent('exception_debugger', ExceptionDebuggerAgent);
    
    // Create a prompt for the debugger
    const debugPrompt = 'Debug the following code implementation';

    const result = await debugger_.execute(debugPrompt, { code: codeResult });

    if (!result.success) {
      const errorMsg = result.error?.message || 'Unknown error';
      logger.error(`Debugging failed: ${errorMsg}`);
      throw new Error(`Debugging failed: ${errorMsg}`);
    }

    return (result.debug_result as Record<string, unknown>) || {};
  }

  /**
   * Analyze dependencies using the DependencyAnalyzerAgent
   * 
   * @returns Dependency analysis result
   */
  private async analyzeDependencies(): Promise<Record<string, unknown>> {
    const analyzer = this.getOrCreateAgent('dependency_analyzer', DependencyAnalyzerAgent);
    
    // Create a prompt for the dependency analyzer
    const analyzePrompt = 'Analyze dependencies in the current codebase';

    const result = await analyzer.execute(analyzePrompt);

    if (!result.success) {
      const errorMsg = result.error?.message || 'Unknown error';
      logger.error(`Dependency analysis failed: ${errorMsg}`);
      throw new Error(`Dependency analysis failed: ${errorMsg}`);
    }

    return (result.analysis as Record<string, unknown>) || {};
  }

  /**
   * Create a final summary of the complete solution
   * 
   * @returns Final solution summary
   */
  private createFinalSummary(): Record<string, unknown> {
    // Retrieve all stored data from memory
    const architecture = this.retrieveFromMemory('architecture') as Record<string, unknown> || {};
    const libraries = this.retrieveFromMemory('libraries') as Record<string, unknown> || {};
    const softwarePlan = this.retrieveFromMemory('software_plan') as Record<string, unknown> || {};
    const codeResult = this.retrieveFromMemory('code_result') as Record<string, unknown> || {};
    const debugResult = this.retrieveFromMemory('debug_result') as Record<string, unknown> || {};
    const dependencyAnalysis = this.retrieveFromMemory('dependency_analysis') as Record<string, unknown> || {};
    
    // Create a comprehensive summary
    const libList = (libraries.selected_libraries as string[]) || [];
    
    const summary = 
      'Multi-agent software development process completed. ' +
      `Architecture: ${architecture.summary || 'Not specified'}. ` +
      `Libraries used: ${libList.join(', ')}. ` +
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
   * Get an existing agent instance or create a new one
   * 
   * @param agentKey - Key to store/retrieve the agent under
   * @param AgentClass - Class of the agent to create
   * @returns An instance of the requested agent
   */
  private getOrCreateAgent<T extends BaseAgent>(
    agentKey: string, 
    AgentClass: new (name: string, memoryManager?: MemoryManager) => T
  ): T {
    if (!this.specializedAgents[agentKey]) {
      logger.debug(`Creating new agent instance: ${AgentClass.name}`);
      this.specializedAgents[agentKey] = new AgentClass(
        `${agentKey}_${this.id.substring(0, 8)}`,
        this.memoryManager
      );
    }
    
    return this.specializedAgents[agentKey] as T;
  }
}