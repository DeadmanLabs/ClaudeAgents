import fs from 'fs';
import path from 'path';
import os from 'os';
import { getLogger } from './LoggerSetup';

const logger = getLogger('EnvLoader');

/**
 * Load environment variables from a .env file.
 * Only sets variables that are not already set in the environment.
 * 
 * @param filePath Optional path to the .env file. If not provided, looks in standard locations.
 * @returns Object containing the loaded environment variables
 */
export function loadEnvFile(filePath?: string): Record<string, string> {
  // If no file path is provided, look in standard locations
  if (!filePath) {
    const possiblePaths = [
      './.env',                                     // Current directory
      './javascript/.env',                          // JavaScript subdirectory
      '../.env',                                    // Parent directory
      path.join(os.homedir(), '.env'),              // User's home directory
      path.join(path.dirname(path.dirname(path.dirname(__dirname))), '.env')  // Project root
    ];
    
    for (const possiblePath of possiblePaths) {
      if (fs.existsSync(possiblePath)) {
        filePath = possiblePath;
        break;
      }
    }
  }
  
  if (!filePath || !fs.existsSync(filePath)) {
    logger.debug('No .env file found.');
    return {};
  }
  
  logger.info(`Loading environment variables from ${filePath}`);
  const envVars: Record<string, string> = {};
  
  try {
    const content = fs.readFileSync(filePath, 'utf8');
    const lines = content.split('\n');
    
    for (const line of lines) {
      const trimmedLine = line.trim();
      
      // Skip empty lines and comments
      if (!trimmedLine || trimmedLine.startsWith('#')) {
        continue;
      }
      
      // Parse key-value pair
      const match = trimmedLine.match(/^([A-Za-z0-9_]+)=(.*)$/);
      if (match) {
        const [, key, rawValue] = match;
        let value = rawValue.trim();
        
        // Remove quotes if present
        if ((value.startsWith('"') && value.endsWith('"')) || 
            (value.startsWith("'") && value.endsWith("'"))) {
          value = value.substring(1, value.length - 1);
        }
        
        // Remove inline comments
        const commentPos = value.indexOf('#');
        if (commentPos >= 0) {
          value = value.substring(0, commentPos).trim();
        }
        
        // Only set if not already in environment
        if (process.env[key] === undefined) {
          envVars[key] = value;
          process.env[key] = value;
          logger.debug(`Set environment variable: ${key}`);
        }
      }
    }
  } catch (error) {
    logger.error(`Error loading .env file: ${error}`);
  }
  
  return envVars;
}

/**
 * Get an environment variable, with a fallback default value.
 * 
 * @param key The environment variable key
 * @param defaultValue Default value if not found
 * @returns The environment variable value or default
 */
export function getEnv(key: string, defaultValue?: any): any {
  return process.env[key] !== undefined ? process.env[key] : defaultValue;
}