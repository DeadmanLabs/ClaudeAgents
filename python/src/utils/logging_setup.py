import os
import sys
from datetime import datetime
from loguru import logger
from typing import Optional


def setup_logging(log_file: Optional[str] = None, level: str = "INFO") -> None:
    """Configure logging for the application.
    
    Args:
        log_file: Path to log file. If None, logs will only be sent to stderr.
        level: Minimum log level to display (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Remove default logger
    logger.remove()
    
    # Format for console output (colorized)
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )
    
    # Format for file output (more detailed, not colorized)
    file_format = (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
        "{level: <8} | "
        "{name}:{function}:{line} | "
        "{message}"
    )
    
    # Add stderr handler with color
    logger.add(
        sys.stderr,
        format=console_format,
        level=level,
        colorize=True,
        backtrace=True,
        diagnose=True,
    )
    
    # Add file handler if specified
    if log_file:
        # Create directory if it doesn't exist
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        # Add rotating file handler
        logger.add(
            log_file,
            format=file_format,
            level="DEBUG",  # Always log everything to file
            rotation="20 MB",  # Rotate when the file reaches 20MB
            retention="1 week",  # Keep logs for 1 week
            compression="zip",  # Compress rotated logs
            backtrace=True,
            diagnose=True,
        )
    
    logger.info(f"Logging initialized at level {level}")


def get_log_file_path() -> str:
    """Generate a log file path with timestamp.
    
    Returns:
        Path to log file
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    return os.path.join(log_dir, f"claude_agents_{timestamp}.log")