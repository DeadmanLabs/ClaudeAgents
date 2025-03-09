import os
import re
from pathlib import Path
from typing import Dict, Any, Optional
from loguru import logger

def load_env_file(file_path: Optional[str] = None) -> Dict[str, str]:
    """
    Load environment variables from a .env file.
    Only sets variables that are not already set in the environment.
    
    Args:
        file_path: Path to the .env file. If None, looks in standard locations.
        
    Returns:
        Dictionary of loaded environment variables
    """
    # If no file path is provided, look in standard locations
    if not file_path:
        possible_paths = [
            './.env',                           # Current directory
            './python/.env',                    # Python subdirectory
            '../.env',                          # Parent directory
            os.path.join(Path.home(), '.env'),  # User's home directory
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')  # Project root
        ]
        
        for path in possible_paths:
            if os.path.isfile(path):
                file_path = path
                break
    
    if not file_path or not os.path.isfile(file_path):
        logger.debug("No .env file found.")
        return {}
    
    logger.info(f"Loading environment variables from {file_path}")
    env_vars = {}
    
    try:
        with open(file_path, 'r') as file:
            for line in file:
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Parse key-value pair
                match = re.match(r'^([A-Za-z0-9_]+)=(.*)$', line)
                if match:
                    key, value = match.groups()
                    
                    # Remove quotes if present
                    value = value.strip()
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    
                    # Remove inline comments
                    comment_pos = value.find('#')
                    if comment_pos >= 0:
                        value = value[:comment_pos].strip()
                    
                    # Only set if not already in environment
                    if key not in os.environ:
                        env_vars[key] = value
                        os.environ[key] = value
                        logger.debug(f"Set environment variable: {key}")
    
    except Exception as e:
        logger.error(f"Error loading .env file: {str(e)}")
    
    return env_vars

def get_env(key: str, default: Any = None) -> Any:
    """
    Get an environment variable, with a fallback default value.
    
    Args:
        key: The environment variable key
        default: Default value if not found
        
    Returns:
        The environment variable value or default
    """
    return os.environ.get(key, default)