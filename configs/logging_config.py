"""
Logging configuration for the CareCloud AI system.
"""

import logging
import logging.handlers
import os
import sys
from typing import Optional

import structlog


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    max_file_size: int = 10485760,  # 10MB
    backup_count: int = 5,
    format_string: Optional[str] = None,
    use_structlog: bool = True,
) -> None:
    """
    Setup comprehensive logging configuration.

    Args:
        level: Logging level
        log_file: Optional log file path
        max_file_size: Maximum log file size in bytes
        backup_count: Number of backup files to keep
        format_string: Optional custom format string
        use_structlog: Whether to use structured logging
    """
    # Default format
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Create formatter
    formatter = logging.Formatter(format_string)

    # Setup handlers
    handlers = []

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    handlers.append(console_handler)

    # File handler with rotation
    if log_file:
        # Ensure log directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=max_file_size, backupCount=backup_count
        )
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, level.upper()), handlers=handlers, force=True
    )

    # Setup structured logging if requested
    if use_structlog:
        setup_structlog()

    # Log initial message
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured with level: {level}")
    if log_file:
        logger.info(f"Log file: {log_file}")


def setup_structlog() -> None:
    """Setup structured logging with structlog."""
    try:
        # Configure structlog
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer(),
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

        # Get a logger to test
        logger = structlog.get_logger(__name__)
        logger.info("Structured logging configured successfully")

    except ImportError:
        # Fallback if structlog is not available
        logger = logging.getLogger(__name__)
        logger.warning("structlog not available, using standard logging")


def get_logger(name: str, use_structlog: bool = True):
    """
    Get a logger instance.

    Args:
        name: Logger name
        use_structlog: Whether to use structured logging

    Returns:
        Logger instance
    """
    if use_structlog:
        try:
            return structlog.get_logger(name)
        except:
            # Fallback to standard logging
            pass

    return logging.getLogger(name)


class LoggerMixin:
    """Mixin class to add logging capabilities to any class."""

    @property
    def logger(self):
        """Get logger for this class."""
        if not hasattr(self, "_logger"):
            self._logger = get_logger(self.__class__.__name__)
        return self._logger


def configure_uvicorn_logging(log_level: str = "info") -> dict:
    """
    Configure uvicorn logging settings.

    Args:
        log_level: Log level for uvicorn

    Returns:
        Uvicorn logging configuration
    """
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "()": "uvicorn.logging.DefaultFormatter",
                "fmt": "%(levelprefix)s %(asctime)s - %(name)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "access": {
                "()": "uvicorn.logging.AccessFormatter",
                "fmt": '%(levelprefix)s %(asctime)s - %(client_addr)s - "%(request_line)s" %(status_code)s',
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
            "access": {
                "formatter": "access",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "uvicorn": {"handlers": ["default"], "level": log_level.upper()},
            "uvicorn.error": {"level": log_level.upper()},
            "uvicorn.access": {
                "handlers": ["access"],
                "level": log_level.upper(),
                "propagate": False,
            },
        },
    }


def setup_agent_logging() -> None:
    """Setup logging specifically for the agent application."""
    # Setup main logging
    setup_logging(level="INFO", log_file="logs/agent.log", use_structlog=True)

    # Reduce noise from some libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    # Set specific levels for our modules
    logging.getLogger("agents").setLevel(logging.INFO)
    logging.getLogger("retrievers").setLevel(logging.INFO)
    logging.getLogger("services").setLevel(logging.INFO)

    logger = get_logger(__name__)
    logger.info("Agent logging configured")


# Performance logging utilities
class PerformanceLogger:
    """Logger for performance metrics."""

    def __init__(self, name: str = "performance"):
        self.logger = get_logger(name)

    def log_execution_time(self, operation: str, duration: float, **kwargs):
        """Log execution time for an operation."""
        self.logger.info(
            "Operation completed",
            operation=operation,
            duration_seconds=duration,
            **kwargs,
        )

    def log_memory_usage(self, operation: str, memory_mb: float, **kwargs):
        """Log memory usage for an operation."""
        self.logger.info(
            "Memory usage recorded", operation=operation, memory_mb=memory_mb, **kwargs
        )

    def log_database_query(self, query: str, duration: float, rows_affected: int = 0):
        """Log database query performance."""
        self.logger.info(
            "Database query executed",
            query_type=query.split()[0].upper() if query else "UNKNOWN",
            duration_seconds=duration,
            rows_affected=rows_affected,
        )


# Error logging utilities
class ErrorLogger:
    """Logger for error tracking and analysis."""

    def __init__(self, name: str = "errors"):
        self.logger = get_logger(name)

    def log_error(self, error: Exception, context: dict = None, **kwargs):
        """Log an error with context."""
        self.logger.error(
            "Error occurred",
            error_type=type(error).__name__,
            error_message=str(error),
            context=context or {},
            **kwargs,
            exc_info=True,
        )

    def log_validation_error(self, field: str, value: str, expected: str, **kwargs):
        """Log a validation error."""
        self.logger.warning(
            "Validation error", field=field, value=value, expected=expected, **kwargs
        )

    def log_api_error(
        self, endpoint: str, status_code: int, error_message: str, **kwargs
    ):
        """Log an API error."""
        self.logger.error(
            "API error",
            endpoint=endpoint,
            status_code=status_code,
            error_message=error_message,
            **kwargs,
        )
