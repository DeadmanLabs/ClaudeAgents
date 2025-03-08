import fs from 'fs';
import path from 'path';
import { logger } from './LoggerSetup';

/**
 * File operations utilities for reading and writing files.
 * Provides methods for working with files and directories,
 * including reading, writing, copying, and deleting files.
 */
export class FileOperations {
  /**
   * Read a file and return its contents
   * 
   * @param filePath - Path to the file to read
   * @param encoding - File encoding (default: utf-8)
   * @returns The file contents as a string
   * @throws Error if the file doesn't exist or can't be read
   */
  public static readFile(filePath: string, encoding: BufferEncoding = 'utf-8'): string {
    try {
      logger.debug(`Reading file: ${filePath}`);
      return fs.readFileSync(filePath, { encoding });
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code === 'ENOENT') {
        const errorMessage = `File not found: ${filePath}`;
        logger.error(errorMessage);
        throw new Error(errorMessage);
      } else {
        const errorMessage = `Error reading file ${filePath}: ${error}`;
        logger.error(errorMessage);
        throw new Error(errorMessage);
      }
    }
  }

  /**
   * Write content to a file
   * 
   * @param filePath - Path to the file to write
   * @param content - Content to write to the file
   * @param encoding - File encoding (default: utf-8)
   * @throws Error if there's an error writing the file
   */
  public static writeFile(filePath: string, content: string, encoding: BufferEncoding = 'utf-8'): void {
    try {
      // Create directory if it doesn't exist
      const dirname = path.dirname(filePath);
      if (!fs.existsSync(dirname)) {
        fs.mkdirSync(dirname, { recursive: true });
      }

      logger.debug(`Writing to file: ${filePath}`);
      fs.writeFileSync(filePath, content, { encoding });
    } catch (error) {
      const errorMessage = `Error writing to file ${filePath}: ${error}`;
      logger.error(errorMessage);
      throw new Error(errorMessage);
    }
  }

  /**
   * Append content to a file
   * 
   * @param filePath - Path to the file to append to
   * @param content - Content to append to the file
   * @param encoding - File encoding (default: utf-8)
   * @throws Error if there's an error appending to the file
   */
  public static appendToFile(filePath: string, content: string, encoding: BufferEncoding = 'utf-8'): void {
    try {
      // Create directory if it doesn't exist
      const dirname = path.dirname(filePath);
      if (!fs.existsSync(dirname)) {
        fs.mkdirSync(dirname, { recursive: true });
      }

      logger.debug(`Appending to file: ${filePath}`);
      fs.appendFileSync(filePath, content, { encoding });
    } catch (error) {
      const errorMessage = `Error appending to file ${filePath}: ${error}`;
      logger.error(errorMessage);
      throw new Error(errorMessage);
    }
  }

  /**
   * Read a JSON file and return its contents
   * 
   * @param filePath - Path to the JSON file to read
   * @returns The parsed JSON data
   * @throws Error if the file doesn't exist, isn't valid JSON, or can't be read
   */
  public static readJson<T = Record<string, unknown>>(filePath: string): T {
    try {
      logger.debug(`Reading JSON file: ${filePath}`);
      const content = fs.readFileSync(filePath, { encoding: 'utf-8' });
      return JSON.parse(content) as T;
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code === 'ENOENT') {
        const errorMessage = `JSON file not found: ${filePath}`;
        logger.error(errorMessage);
        throw new Error(errorMessage);
      } else if (error instanceof SyntaxError) {
        const errorMessage = `Invalid JSON in file ${filePath}: ${error.message}`;
        logger.error(errorMessage);
        throw new Error(errorMessage);
      } else {
        const errorMessage = `Error reading JSON file ${filePath}: ${error}`;
        logger.error(errorMessage);
        throw new Error(errorMessage);
      }
    }
  }

  /**
   * Write data to a JSON file
   * 
   * @param filePath - Path to the JSON file to write
   * @param data - Data to write to the file
   * @param indent - Number of spaces for indentation (default: 2)
   * @throws Error if the data isn't JSON-serializable or there's an error writing the file
   */
  public static writeJson(filePath: string, data: unknown, indent = 2): void {
    try {
      // Create directory if it doesn't exist
      const dirname = path.dirname(filePath);
      if (!fs.existsSync(dirname)) {
        fs.mkdirSync(dirname, { recursive: true });
      }

      logger.debug(`Writing JSON to file: ${filePath}`);
      fs.writeFileSync(filePath, JSON.stringify(data, null, indent), 'utf-8');
    } catch (error) {
      const errorMessage = `Error writing JSON to file ${filePath}: ${error}`;
      logger.error(errorMessage);
      throw new Error(errorMessage);
    }
  }

  /**
   * Ensure a directory exists, creating it if necessary
   * 
   * @param directoryPath - Path to the directory
   * @throws Error if there's an error creating the directory
   */
  public static ensureDirectory(directoryPath: string): void {
    try {
      logger.debug(`Ensuring directory exists: ${directoryPath}`);
      if (!fs.existsSync(directoryPath)) {
        fs.mkdirSync(directoryPath, { recursive: true });
      }
    } catch (error) {
      const errorMessage = `Error creating directory ${directoryPath}: ${error}`;
      logger.error(errorMessage);
      throw new Error(errorMessage);
    }
  }

  /**
   * Copy a file from source to destination
   * 
   * @param sourcePath - Path to the source file
   * @param destPath - Path to the destination file
   * @throws Error if the source file doesn't exist or there's an error copying the file
   */
  public static copyFile(sourcePath: string, destPath: string): void {
    try {
      // Create destination directory if it doesn't exist
      const dirname = path.dirname(destPath);
      if (!fs.existsSync(dirname)) {
        fs.mkdirSync(dirname, { recursive: true });
      }

      logger.debug(`Copying file from ${sourcePath} to ${destPath}`);
      fs.copyFileSync(sourcePath, destPath);
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code === 'ENOENT') {
        const errorMessage = `Source file not found: ${sourcePath}`;
        logger.error(errorMessage);
        throw new Error(errorMessage);
      } else {
        const errorMessage = `Error copying file from ${sourcePath} to ${destPath}: ${error}`;
        logger.error(errorMessage);
        throw new Error(errorMessage);
      }
    }
  }

  /**
   * Delete a file
   * 
   * @param filePath - Path to the file to delete
   * @throws Error if the file doesn't exist or there's an error deleting the file
   */
  public static deleteFile(filePath: string): void {
    try {
      logger.debug(`Deleting file: ${filePath}`);
      fs.unlinkSync(filePath);
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code === 'ENOENT') {
        const errorMessage = `File not found for deletion: ${filePath}`;
        logger.error(errorMessage);
        throw new Error(errorMessage);
      } else {
        const errorMessage = `Error deleting file ${filePath}: ${error}`;
        logger.error(errorMessage);
        throw new Error(errorMessage);
      }
    }
  }

  /**
   * List files in a directory matching a pattern
   * 
   * @param directoryPath - Path to the directory
   * @param pattern - Regular expression pattern for matching files (default: all files)
   * @returns List of file paths
   * @throws Error if the directory doesn't exist or there's an error listing files
   */
  public static listFiles(directoryPath: string, pattern?: RegExp): string[] {
    try {
      logger.debug(`Listing files in ${directoryPath}${pattern ? ` matching pattern '${pattern}'` : ''}`);
      
      if (!fs.existsSync(directoryPath)) {
        const errorMessage = `Directory not found: ${directoryPath}`;
        logger.error(errorMessage);
        throw new Error(errorMessage);
      }
      
      const files = fs.readdirSync(directoryPath);
      
      if (pattern) {
        return files
          .filter(file => pattern.test(file))
          .map(file => path.join(directoryPath, file));
      } else {
        return files.map(file => path.join(directoryPath, file));
      }
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code === 'ENOENT') {
        const errorMessage = `Directory not found: ${directoryPath}`;
        logger.error(errorMessage);
        throw new Error(errorMessage);
      } else if ((error as Error).message.includes('Directory not found')) {
        throw error;
      } else {
        const errorMessage = `Error listing files in ${directoryPath}: ${error}`;
        logger.error(errorMessage);
        throw new Error(errorMessage);
      }
    }
  }
}