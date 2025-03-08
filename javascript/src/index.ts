#!/usr/bin/env node
import { program } from 'commander';
import fs from 'fs';
import { setupLogger } from './utils/LoggerSetup';
import { MemoryManager } from './utils/MemoryManager';
import { ManagerAgent } from './agents/ManagerAgent';

// Define the CLI program
program
  .name('claude-agents')
  .description('Multi-agent Collaborative Development System')
  .version('0.1.0');

program
  .argument('[prompt]', 'The task prompt')
  .option('-f, --prompt-file <file>', 'File containing the task prompt')
  .option('-l, --log-level <level>', 'Set the logging level', 'info')
  .option('-p, --persist-memory', 'Persist memory to disk')
  .option('-m, --memory-dir <dir>', 'Directory for persistent memory storage', './memory')
  .option('-o, --log-to-file', 'Log to file')
  .action(async (promptArg: string | undefined, options: {
    promptFile?: string;
    logLevel: string;
    persistMemory: boolean;
    memoryDir: string;
    logToFile: boolean;
  }) => {
    // Set up logger
    const logger = setupLogger({
      logLevel: options.logLevel as any,
      logToFile: options.logToFile,
      logFileDir: 'logs',
    });

    // Print banner
    console.log('\n' + '='.repeat(60));
    console.log(' ClaudeAgents - Multi-agent Collaborative Development System ');
    console.log('='.repeat(60) + '\n');

    // Get prompt from arguments or file
    let prompt: string;
    if (promptArg) {
      prompt = promptArg;
    } else if (options.promptFile) {
      try {
        prompt = fs.readFileSync(options.promptFile, 'utf8').trim();
      } catch (error) {
        console.error(`Error reading prompt file: ${error}`);
        process.exit(1);
      }
    } else {
      program.help();
      return;
    }

    // Initialize memory manager
    const memoryManager = new MemoryManager(options.persistMemory, options.memoryDir);

    try {
      // Initialize the manager agent
      const manager = new ManagerAgent('Manager', memoryManager);

      // Execute the manager agent with the prompt
      logger.info(`Starting execution with prompt: ${prompt.substring(0, 100)}...`);
      const result = await manager.execute(prompt);

      if (result.success) {
        logger.info('Execution completed successfully');
      } else {
        logger.error(`Execution failed: ${result.error?.message || 'Unknown error'}`);
      }
    } catch (error) {
      logger.error(`Unhandled exception: ${error}`);
      console.error(`\nError: ${error}`);
    }
  });

// Parse command-line arguments
program.parse();

// If no arguments were passed, show help
if (process.argv.length <= 2) {
  program.help();
}