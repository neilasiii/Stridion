"""
Logging configuration for the running coach service.
"""

import logging
import sys
import re
from pathlib import Path


class SensitiveDataFilter(logging.Filter):
    """Filter to redact sensitive data from log messages."""

    # Patterns to redact
    PATTERNS = [
        # API keys and tokens
        (re.compile(r'(api[_-]?key|token|password|secret)[:=]\s*["\']?([^\s"\',}]+)', re.IGNORECASE), r'\1: [REDACTED]'),
        # Bearer tokens
        (re.compile(r'Bearer\s+[A-Za-z0-9\-._~+/]+=*', re.IGNORECASE), 'Bearer [REDACTED]'),
        # Email addresses (partial redaction)
        (re.compile(r'([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'), r'***@\2'),
    ]

    def filter(self, record):
        """
        Filter log record to redact sensitive data.

        Args:
            record: LogRecord instance

        Returns:
            True (always process the record)
        """
        if isinstance(record.msg, str):
            for pattern, replacement in self.PATTERNS:
                record.msg = pattern.sub(replacement, record.msg)

        # Also sanitize args if present
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: self._sanitize_value(v) for k, v in record.args.items()
                }
            elif isinstance(record.args, tuple):
                record.args = tuple(self._sanitize_value(arg) for arg in record.args)

        return True

    def _sanitize_value(self, value):
        """Sanitize a single value."""
        if isinstance(value, str):
            for pattern, replacement in self.PATTERNS:
                value = pattern.sub(replacement, value)
        return value


def setup_logging(log_level: str = "INFO", log_file: str = None):
    """
    Configure structured logging for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file. If None, logs to stdout only.
    """
    # Create formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Get root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    logger.handlers = []

    # Create sensitive data filter
    sensitive_filter = SensitiveDataFilter()

    # Console handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(sensitive_filter)
    logger.addHandler(console_handler)

    # File handler (optional)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(sensitive_filter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str):
    """
    Get a logger instance for a module.

    Args:
        name: Module name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
