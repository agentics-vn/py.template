"""Unified logging configuration.

This module sets up a consistent logging format across all loggers in the application,
including loguru, uvicorn, FastAPI, and asyncio.
"""

import logging
import sys

from loguru import logger


def format_record(record):
    """Custom formatter that handles both loguru and intercepted standard logging.

    Args:
        record: The log record from loguru

    Returns:
        str: Formatted log string with consistent format
    """
    logger_name = record["extra"].get("name", record["name"])
    format_string = (
        f"{{time:YYYY-MM-DD HH:mm:ss.SSS}} | {{level: <8}} | {logger_name}:{{function}}:{{line}} - {{message}}\n"
    )
    return format_string


class InterceptHandler(logging.Handler):
    """Intercept standard logging messages and redirect them to loguru."""

    def emit(self, record):
        """Emit a log record by redirecting it to loguru.

        Args:
            record: The standard logging record to process
        """
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        logger_instance = logger.bind(name=record.name)
        logger_instance.opt(exception=record.exc_info).log(level, record.getMessage())


def setup_logging(level: str = "DEBUG"):
    """Set up unified logging configuration for all loggers in the application.

    This function:
    1. Configures loguru with a custom format and specified level
    2. Sets up an interceptor to capture standard Python logging
    3. Configures specific loggers (uvicorn, SQLAlchemy, etc.) to use the unified format

    Args:
        level: The logging level to use (DEBUG, INFO, WARNING, ERROR)
    """
    logger.remove()
    logger.add(sys.stdout, format=format_record, level=level, colorize=True, backtrace=True, diagnose=True)
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    logging.getLogger().handlers = [InterceptHandler()]

    # Configure non-SQLAlchemy loggers with the specified level
    logger_names = [
        "uvicorn",
        "uvicorn.access",
        "uvicorn.error",
        "fastapi",
        "asyncio",
    ]

    for logger_name in logger_names:
        std_logger = logging.getLogger(logger_name)
        std_logger.handlers.clear()
        std_logger.addHandler(InterceptHandler())
        std_logger.setLevel(getattr(logging, level))
        std_logger.propagate = False

    # Suppress verbose third-party library logging
    # These libraries log too much at DEBUG level and clutter application logs
    noisy_logger_names = [
        # HTTP clients
        "httpx",
        "httpcore",
        "httpcore.connection",
        "httpcore.http11",
        "httpcore.http2",
        "urllib3",
        "urllib3.connectionpool",
    ]

    for logger_name in noisy_logger_names:
        std_logger = logging.getLogger(logger_name)
        std_logger.handlers.clear()
        std_logger.setLevel(logging.WARNING)  # Only show warnings and errors
        std_logger.propagate = False


def get_logger():
    """Get the configured loguru logger instance.

    Returns:
        The loguru logger instance
    """
    return logger
