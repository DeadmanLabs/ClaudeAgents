import { exec, execSync } from 'child_process';
import { promisify } from 'util';
import { Tool } from 'langchain/tools';
import { BaseTool } from '@langchain/core/tools';
import { CallbackManagerForToolRun } from '@langchain/core/callbacks/manager';
import { getLogger } from './LoggerSetup';

const execAsync = promisify(exec);
const logger = getLogger('ShellExecutor');

/**
 * Result interface for shell command execution
 */
export interface ShellCommandResult {
  success: boolean;
  returnCode: number | null;
  stdout: string;
  stderr: string;
  duration?: number;
  command: string;
  error?: string;
}

/**
 * Class for executing shell commands
 */
export class ShellExecutor {
  /**
   * Run a shell command asynchronously
   * 
   * @param command - The command to execute
   * @param timeout - Optional timeout in milliseconds
   * @param cwd - Optional working directory for the command
   * @param env - Optional environment variables
   * @returns Result of the command execution
   */
  static async runAsync(
    command: string,
    timeout?: number,
    cwd?: string,
    env?: NodeJS.ProcessEnv
  ): Promise<ShellCommandResult> {
    logger.info(`Executing command: ${command}`);
    const startTime = Date.now();
    
    try {
      // Create options object
      const options: any = {
        shell: true,
        maxBuffer: 10 * 1024 * 1024 // 10MB buffer
      };
      
      if (cwd) options.cwd = cwd;
      if (env) options.env = { ...process.env, ...env };
      if (timeout) options.timeout = timeout;
      
      // Execute the command
      const { stdout, stderr } = await execAsync(command, options);
      const duration = (Date.now() - startTime) / 1000;
      
      logger.debug(`Command completed in ${duration.toFixed(2)}s`);
      
      return {
        success: true,
        returnCode: 0,
        stdout: stdout,
        stderr: stderr,
        duration: duration,
        command: command
      };
    } catch (error: any) {
      const duration = (Date.now() - startTime) / 1000;
      logger.error(`Error executing command: ${error.message}`);
      
      // Determine error type
      let errorType = 'execution_error';
      if (error.signal === 'SIGTERM' && error.killed) {
        errorType = 'timeout';
      }
      
      return {
        success: false,
        returnCode: error.code || null,
        stdout: error.stdout || '',
        stderr: error.stderr || error.message,
        duration: duration,
        command: command,
        error: errorType
      };
    }
  }
  
  /**
   * Run a shell command synchronously
   * 
   * @param command - The command to execute
   * @param timeout - Optional timeout in milliseconds
   * @param cwd - Optional working directory for the command
   * @param env - Optional environment variables
   * @returns Result of the command execution
   */
  static run(
    command: string,
    timeout?: number,
    cwd?: string,
    env?: NodeJS.ProcessEnv
  ): ShellCommandResult {
    logger.info(`Executing command synchronously: ${command}`);
    
    try {
      // Create options object
      const options: any = {
        shell: true,
        maxBuffer: 10 * 1024 * 1024, // 10MB buffer
        encoding: 'utf8'
      };
      
      if (cwd) options.cwd = cwd;
      if (env) options.env = { ...process.env, ...env };
      if (timeout) options.timeout = timeout;
      
      // Execute the command
      const stdout = execSync(command, options).toString();
      
      logger.debug(`Command completed successfully`);
      
      return {
        success: true,
        returnCode: 0,
        stdout: stdout,
        stderr: '',
        command: command
      };
    } catch (error: any) {
      logger.error(`Error executing command synchronously: ${error.message}`);
      
      return {
        success: false,
        returnCode: error.status || null,
        stdout: error.stdout ? error.stdout.toString() : '',
        stderr: error.stderr ? error.stderr.toString() : error.message,
        command: command,
        error: 'execution_error'
      };
    }
  }
}

/**
 * LangChain tool for executing shell commands
 */
export class ShellExecutorTool extends BaseTool {
  name = 'shell_executor';
  description = 'Execute shell commands on the local system';
  
  constructor() {
    super();
  }
  
  /** @ignore */
  async _call(
    args: { command: string; timeout?: number; cwd?: string },
    runManager?: CallbackManagerForToolRun
  ): Promise<string> {
    const { command, timeout, cwd } = args;
    
    if (runManager) {
      await runManager.handleText(`Executing shell command: ${command}`);
    }
    
    const result = await ShellExecutor.runAsync(command, timeout, cwd);
    
    // Format the result for easier readability by the LLM
    const output = [
      `Command: ${command}`,
      `Success: ${result.success}`,
      `Return Code: ${result.returnCode}`,
      '',
      'STDOUT:',
      result.stdout,
      '',
      'STDERR:',
      result.stderr
    ].join('\n');
    
    return output;
  }
}

/**
 * Factory function to create a shell executor tool
 * @returns A configured ShellExecutorTool instance
 */
export function createShellExecutorTool(): ShellExecutorTool {
  return new ShellExecutorTool();
}