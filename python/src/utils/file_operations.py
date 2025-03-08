import os
import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from loguru import logger


class FileOperations:
    """File operations utilities for reading and writing files.
    
    This class provides methods for working with files and directories,
    including reading, writing, copying, and deleting files.
    """
    
    @staticmethod
    def read_file(file_path: Union[str, Path], encoding: str = "utf-8") -> str:
        """Read a file and return its contents.
        
        Args:
            file_path: Path to the file to read
            encoding: File encoding
            
        Returns:
            The file contents as a string
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            IOError: If there's an error reading the file
        """
        try:
            path = Path(file_path)
            logger.debug(f"Reading file: {path}")
            with open(path, "r", encoding=encoding) as f:
                content = f.read()
            return content
        except FileNotFoundError:
            logger.error(f"File not found: {path}")
            raise
        except IOError as e:
            logger.error(f"Error reading file {path}: {str(e)}")
            raise
    
    @staticmethod
    def write_file(file_path: Union[str, Path], content: str, encoding: str = "utf-8") -> None:
        """Write content to a file.
        
        Args:
            file_path: Path to the file to write
            content: Content to write to the file
            encoding: File encoding
            
        Raises:
            IOError: If there's an error writing the file
        """
        try:
            path = Path(file_path)
            # Create directory if it doesn't exist
            path.parent.mkdir(parents=True, exist_ok=True)
            
            logger.debug(f"Writing to file: {path}")
            with open(path, "w", encoding=encoding) as f:
                f.write(content)
        except IOError as e:
            logger.error(f"Error writing to file {path}: {str(e)}")
            raise
    
    @staticmethod
    def append_to_file(file_path: Union[str, Path], content: str, encoding: str = "utf-8") -> None:
        """Append content to a file.
        
        Args:
            file_path: Path to the file to append to
            content: Content to append to the file
            encoding: File encoding
            
        Raises:
            IOError: If there's an error appending to the file
        """
        try:
            path = Path(file_path)
            # Create directory if it doesn't exist
            path.parent.mkdir(parents=True, exist_ok=True)
            
            logger.debug(f"Appending to file: {path}")
            with open(path, "a", encoding=encoding) as f:
                f.write(content)
        except IOError as e:
            logger.error(f"Error appending to file {path}: {str(e)}")
            raise
    
    @staticmethod
    def read_json(file_path: Union[str, Path]) -> Dict[str, Any]:
        """Read a JSON file and return its contents.
        
        Args:
            file_path: Path to the JSON file to read
            
        Returns:
            The parsed JSON data
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            json.JSONDecodeError: If the file isn't valid JSON
            IOError: If there's an error reading the file
        """
        try:
            path = Path(file_path)
            logger.debug(f"Reading JSON file: {path}")
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data
        except FileNotFoundError:
            logger.error(f"JSON file not found: {path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in file {path}: {str(e)}")
            raise
        except IOError as e:
            logger.error(f"Error reading JSON file {path}: {str(e)}")
            raise
    
    @staticmethod
    def write_json(file_path: Union[str, Path], data: Dict[str, Any], indent: int = 2) -> None:
        """Write data to a JSON file.
        
        Args:
            file_path: Path to the JSON file to write
            data: Data to write to the file
            indent: Number of spaces for indentation
            
        Raises:
            TypeError: If the data isn't JSON-serializable
            IOError: If there's an error writing the file
        """
        try:
            path = Path(file_path)
            # Create directory if it doesn't exist
            path.parent.mkdir(parents=True, exist_ok=True)
            
            logger.debug(f"Writing JSON to file: {path}")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=indent)
        except TypeError as e:
            logger.error(f"Data is not JSON-serializable: {str(e)}")
            raise
        except IOError as e:
            logger.error(f"Error writing JSON to file {path}: {str(e)}")
            raise
    
    @staticmethod
    def ensure_directory(directory_path: Union[str, Path]) -> None:
        """Ensure a directory exists, creating it if necessary.
        
        Args:
            directory_path: Path to the directory
            
        Raises:
            IOError: If there's an error creating the directory
        """
        try:
            path = Path(directory_path)
            logger.debug(f"Ensuring directory exists: {path}")
            path.mkdir(parents=True, exist_ok=True)
        except IOError as e:
            logger.error(f"Error creating directory {path}: {str(e)}")
            raise
    
    @staticmethod
    def copy_file(source_path: Union[str, Path], dest_path: Union[str, Path]) -> None:
        """Copy a file from source to destination.
        
        Args:
            source_path: Path to the source file
            dest_path: Path to the destination file
            
        Raises:
            FileNotFoundError: If the source file doesn't exist
            IOError: If there's an error copying the file
        """
        try:
            src = Path(source_path)
            dst = Path(dest_path)
            # Create destination directory if it doesn't exist
            dst.parent.mkdir(parents=True, exist_ok=True)
            
            logger.debug(f"Copying file from {src} to {dst}")
            shutil.copy2(src, dst)
        except FileNotFoundError:
            logger.error(f"Source file not found: {src}")
            raise
        except IOError as e:
            logger.error(f"Error copying file from {src} to {dst}: {str(e)}")
            raise
    
    @staticmethod
    def delete_file(file_path: Union[str, Path]) -> None:
        """Delete a file.
        
        Args:
            file_path: Path to the file to delete
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            IOError: If there's an error deleting the file
        """
        try:
            path = Path(file_path)
            logger.debug(f"Deleting file: {path}")
            path.unlink()
        except FileNotFoundError:
            logger.error(f"File not found for deletion: {path}")
            raise
        except IOError as e:
            logger.error(f"Error deleting file {path}: {str(e)}")
            raise
    
    @staticmethod
    def list_files(directory_path: Union[str, Path], pattern: str = "*") -> List[Path]:
        """List files in a directory matching a pattern.
        
        Args:
            directory_path: Path to the directory
            pattern: Glob pattern for matching files
            
        Returns:
            List of file paths
            
        Raises:
            FileNotFoundError: If the directory doesn't exist
            IOError: If there's an error listing files
        """
        try:
            path = Path(directory_path)
            logger.debug(f"Listing files in {path} matching pattern '{pattern}'")
            return list(path.glob(pattern))
        except FileNotFoundError:
            logger.error(f"Directory not found: {path}")
            raise
        except IOError as e:
            logger.error(f"Error listing files in {path}: {str(e)}")
            raise