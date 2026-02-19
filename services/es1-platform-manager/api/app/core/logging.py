"""Structured logging configuration."""
import logging
import json
import sys
from datetime import datetime
from typing import Any


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields if present
        if hasattr(record, "extra"):
            log_data.update(record.extra)

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


class StructuredLogger:
    """
    Structured logger wrapper for consistent logging.

    Supports both human-readable and JSON formats.
    """

    def __init__(self, name: str, json_format: bool = False):
        """Initialize the logger."""
        self.logger = logging.getLogger(name)
        self._setup_handler(json_format)

    def _setup_handler(self, json_format: bool) -> None:
        """Set up the log handler with appropriate formatter."""
        if self.logger.handlers:
            return  # Already configured

        handler = logging.StreamHandler(sys.stdout)

        if json_format:
            handler.setFormatter(JSONFormatter())
        else:
            handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            )

        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def _log(self, level: int, message: str, **extra: Any) -> None:
        """Log with extra context."""
        record = self.logger.makeRecord(
            self.logger.name,
            level,
            "",
            0,
            message,
            (),
            None,
        )
        if extra:
            record.extra = extra
        self.logger.handle(record)

    def info(self, message: str, **extra: Any) -> None:
        """Log info level message."""
        if extra:
            self._log(logging.INFO, message, **extra)
        else:
            self.logger.info(message)

    def warning(self, message: str, **extra: Any) -> None:
        """Log warning level message."""
        if extra:
            self._log(logging.WARNING, message, **extra)
        else:
            self.logger.warning(message)

    def error(self, message: str, **extra: Any) -> None:
        """Log error level message."""
        if extra:
            self._log(logging.ERROR, message, **extra)
        else:
            self.logger.error(message)

    def debug(self, message: str, **extra: Any) -> None:
        """Log debug level message."""
        if extra:
            self._log(logging.DEBUG, message, **extra)
        else:
            self.logger.debug(message)

    def exception(self, message: str, **extra: Any) -> None:
        """Log exception with traceback."""
        self.logger.exception(message, extra=extra if extra else None)


def get_logger(name: str, json_format: bool = False) -> StructuredLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (typically __name__)
        json_format: If True, output JSON formatted logs

    Returns:
        StructuredLogger instance
    """
    return StructuredLogger(name, json_format)


# Default application logger
logger = get_logger("platform-manager")
