"""
Logging configuration module for the application.
Supports configurable log levels, output formats, and colorful console output.
"""
import logging
import sys
from enum import Enum
from typing import Optional


class LogLevel(str, Enum):
    """Available log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


# ANSI color codes for colorful logging
class LogColors:
    """ANSI color codes for log levels."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    
    # Level colors (bold)
    DEBUG = "\033[1;36m"      # Cyan
    INFO = "\033[1;32m"       # Green
    WARNING = "\033[1;33m"    # Yellow
    ERROR = "\033[1;31m"      # Red
    CRITICAL = "\033[1;35m"   # Magenta
    
    # Component colors
    TIMESTAMP = "\033[2;37m"  # Dim white/gray
    NAME = "\033[1;34m"       # Blue
    MESSAGE = "\033[0m"       # Default


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors to log output."""
    
    LEVEL_COLORS = {
        logging.DEBUG: LogColors.DEBUG,
        logging.INFO: LogColors.INFO,
        logging.WARNING: LogColors.WARNING,
        logging.ERROR: LogColors.ERROR,
        logging.CRITICAL: LogColors.CRITICAL,
    }
    
    def __init__(self, fmt: str, datefmt: str = None, use_colors: bool = True):
        super().__init__(fmt, datefmt)
        self.use_colors = use_colors
    
    def format(self, record: logging.LogRecord) -> str:
        # Save original values
        original_levelname = record.levelname
        original_name = record.name
        original_msg = record.getMessage()
        
        if self.use_colors:
            # Color the timestamp
            record.asctime = f"{LogColors.TIMESTAMP}{self.formatTime(record)}{LogColors.RESET}"
            
            # Color the level name
            level_color = self.LEVEL_COLORS.get(record.levelno, LogColors.RESET)
            record.levelname = f"{level_color}{original_levelname}{LogColors.RESET}"
            
            # Color the logger name
            record.name = f"{LogColors.NAME}{original_name}{LogColors.RESET}"
            
            # Format the message
            formatted = super().format(record)
            
            # Restore original values to prevent side effects
            record.levelname = original_levelname
            record.name = original_name
            
            return formatted
        else:
            record.asctime = self.formatTime(record)
            return super().format(record)


class LoggingConfig:
    """Configuration for application logging."""
    
    # Default log level for the application
    DEFAULT_LOG_LEVEL: LogLevel = LogLevel.INFO
    
    # Log format string (without colors - for file output)
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Colored log format for console output
    COLORED_LOG_FORMAT: str = "%(asctime)s | %(levelname)-8s | %(name)s - %(message)s"
    
    # Date format
    DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"
    
    # Individual module log levels (override DEFAULT_LOG_LEVEL)
    MODULE_LOG_LEVELS: dict[str, LogLevel] = {
        # Examples (uncomment to use):
        # "app.api.auth": LogLevel.DEBUG,
        # "app.services": LogLevel.WARNING,
    }
    
    # Enable/disable console output
    ENABLE_CONSOLE: bool = True
    
    # Enable/disable colors in console output
    ENABLE_COLORS: bool = True
    
    # Enable/disable file output
    ENABLE_FILE: bool = False
    
    # Log file path (used if ENABLE_FILE is True)
    LOG_FILE_PATH: str = "logs/app.log"


def get_log_level(level: LogLevel) -> int:
    """Convert LogLevel enum to logging module level."""
    level_map = {
        LogLevel.DEBUG: logging.DEBUG,
        LogLevel.INFO: logging.INFO,
        LogLevel.WARNING: logging.WARNING,
        LogLevel.ERROR: logging.ERROR,
        LogLevel.CRITICAL: logging.CRITICAL,
    }
    return level_map.get(level, logging.INFO)


def setup_logging(
    default_level: Optional[LogLevel] = None,
    enable_console: Optional[bool] = None,
    enable_file: Optional[bool] = None,
    log_file_path: Optional[str] = None,
    enable_colors: Optional[bool] = None,
) -> None:
    """
    Setup the logging configuration for the application.
    
    Args:
        default_level: Override the default log level
        enable_console: Override console output setting
        enable_file: Override file output setting
        log_file_path: Override log file path
        enable_colors: Override color output setting
    """
    config = LoggingConfig()
    
    # Use overrides or defaults
    level = default_level or config.DEFAULT_LOG_LEVEL
    console = enable_console if enable_console is not None else config.ENABLE_CONSOLE
    file_out = enable_file if enable_file is not None else config.ENABLE_FILE
    file_path = log_file_path or config.LOG_FILE_PATH
    colors = enable_colors if enable_colors is not None else config.ENABLE_COLORS
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(get_log_level(level))
    
    # Remove existing handlers
    root_logger.handlers = []
    
    # Add console handler with colored formatter
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(get_log_level(level))
        
        # Use colored formatter for console
        console_formatter = ColoredFormatter(
            fmt=config.COLORED_LOG_FORMAT,
            datefmt=config.DATE_FORMAT,
            use_colors=colors
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
    
    # Add file handler with plain formatter (no colors in files)
    if file_out:
        import os
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        file_handler = logging.FileHandler(file_path)
        file_handler.setLevel(get_log_level(level))
        
        # Use plain formatter for file (no colors)
        file_formatter = logging.Formatter(
            fmt=config.LOG_FORMAT,
            datefmt=config.DATE_FORMAT
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    # Apply module-specific log levels
    for module_name, module_level in config.MODULE_LOG_LEVELS.items():
        module_logger = logging.getLogger(module_name)
        module_logger.setLevel(get_log_level(module_level))
    
    # Log setup completion (with colors if enabled)
    root_logger.info(f"Logging configured with level: {level}, colors: {colors}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.
    
    Args:
        name: The logger name (typically __name__)
        
    Returns:
        A configured logger instance
    """
    return logging.getLogger(name)
