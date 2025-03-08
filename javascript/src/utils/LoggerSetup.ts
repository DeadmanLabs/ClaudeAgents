import pino from 'pino';
import fs from 'fs';
import path from 'path';

type LogLevel = 'debug' | 'info' | 'warn' | 'error' | 'fatal';

/**
 * Configuration for the logging system
 */
export interface LoggerConfig {
  logToFile: boolean;
  logFileDir: string;
  logLevel: LogLevel;
  prettyPrint: boolean;
}

/**
 * Create a timestamp-based log file path
 * 
 * @returns Path to a log file with timestamp
 */
export function getLogFilePath(): string {
  const timestamp = new Date().toISOString().replace(/:/g, '-').replace(/\..+/, '');
  const logDir = 'logs';
  
  if (!fs.existsSync(logDir)) {
    fs.mkdirSync(logDir, { recursive: true });
  }
  
  return path.join(logDir, `claude_agents_${timestamp}.log`);
}

/**
 * Configure logging for the application
 * 
 * @param config - Logger configuration options
 * @returns A configured Pino logger instance
 */
export function setupLogger(config: Partial<LoggerConfig> = {}): pino.Logger {
  // Default configuration
  const fullConfig: LoggerConfig = {
    logToFile: false,
    logFileDir: 'logs',
    logLevel: 'info',
    prettyPrint: true,
    ...config
  };
  
  // Create base transport configuration
  const transport: pino.TransportMultiOptions = {
    targets: []
  };
  
  // Add console transport with pretty printing if enabled
  if (fullConfig.prettyPrint) {
    transport.targets.push({
      target: 'pino-pretty',
      level: fullConfig.logLevel,
      options: {
        colorize: true,
        translateTime: 'yyyy-mm-dd HH:MM:ss.l',
        ignore: 'pid,hostname',
      }
    });
  } else {
    transport.targets.push({
      target: 'pino/file',
      level: fullConfig.logLevel,
      options: { destination: 1 } // stdout
    });
  }
  
  // Add file transport if enabled
  if (fullConfig.logToFile) {
    // Create directory if it doesn't exist
    if (!fs.existsSync(fullConfig.logFileDir)) {
      fs.mkdirSync(fullConfig.logFileDir, { recursive: true });
    }
    
    const logFilePath = getLogFilePath();
    
    transport.targets.push({
      target: 'pino/file',
      level: 'debug', // Always log everything to file
      options: { destination: logFilePath }
    });
  }
  
  // Create and return the logger
  const logger = pino({
    level: fullConfig.logLevel,
    transport
  });
  
  logger.info(`Logging initialized at level ${fullConfig.logLevel}`);
  
  if (fullConfig.logToFile) {
    logger.info(`Logging to file in directory: ${fullConfig.logFileDir}`);
  }
  
  return logger;
}

// Export a default logger instance
export const logger = setupLogger();