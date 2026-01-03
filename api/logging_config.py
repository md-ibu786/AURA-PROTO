"""
Structured logging configuration for AURA-PROTO.
Provides JSON-style structured logs for production environments.
"""
import logging
import sys
import json
from datetime import datetime
from typing import Optional


class StructuredFormatter(logging.Formatter):
    """JSON-style structured log formatter for production."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "module": record.module,
            "message": record.getMessage(),
        }
        
        # Add function name if available
        if record.funcName:
            log_data["function"] = record.funcName
            
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
            
        # Add extra fields if provided
        if hasattr(record, 'extra_data'):
            log_data.update(record.extra_data)
            
        return json.dumps(log_data)


class DevelopmentFormatter(logging.Formatter):
    """Human-readable log formatter for development."""
    
    FORMAT = "%(asctime)s [%(levelname)s] %(module)s: %(message)s"
    
    def __init__(self):
        super().__init__(self.FORMAT, datefmt="%H:%M:%S")


def setup_logging(
    level: str = "INFO",
    production: bool = False,
    logger_name: str = "aura"
) -> logging.Logger:
    """
    Configure application logging.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        production: Use JSON format if True, human-readable if False
        logger_name: Name of the logger instance
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    
    # Choose formatter based on environment
    if production:
        handler.setFormatter(StructuredFormatter())
    else:
        handler.setFormatter(DevelopmentFormatter())
    
    logger.addHandler(handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a child logger with the given name."""
    base_logger = logging.getLogger("aura")
    if name:
        return base_logger.getChild(name)
    return base_logger


# Create default logger (development mode by default)
logger = setup_logging(level="INFO", production=False)
