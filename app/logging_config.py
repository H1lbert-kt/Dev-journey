import logging
import logging.config
import os


SENSITIVE_KEYS = {
    "password", "senha", "secret", "token", "session_token",
    "authorization", "cookie", "cookies", "secret_key",
    "SENTRY_DSN", "DATABASE_URL", "POSTGRES_PASSWORD",
}


class SensitiveFilter(logging.Filter):
    """Filter that redacts sensitive data from log records."""

    def __init__(self, name: str = ""):
        super().__init__(name)

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = _redact_string(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: _redact_value(k, v) for k, v in record.args.items()
                }
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    _redact_value(str(i), v) for i, v in enumerate(record.args)
                )
        return True


def _redact_string(text: str) -> str:
    for key in SENSITIVE_KEYS:
        for pattern in [f"{key}=", f"{key}:", f"{key} "]:
            idx = text.lower().find(pattern.lower())
            if idx != -1:
                start = idx + len(pattern)
                if start < len(text):
                    end = text.find(" ", start)
                    if end == -1:
                        end = min(start + 8, len(text))
                    text = text[:start] + "***REDACTED***" + text[end:]
    return text


def _redact_value(key: str, value) -> str:
    key_lower = key.lower()
    if any(s in key_lower for s in SENSITIVE_KEYS):
        return "***REDACTED***"
    return value


def setup_logging() -> None:
    """Configure centralized logging for the application."""
    log_level = os.environ.get("LOG_LEVEL", "INFO")

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "sensitive": {
                "()": SensitiveFilter,
            },
        },
        "formatters": {
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "standard",
                "filters": ["sensitive"],
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "": {
                "level": log_level,
                "handlers": ["console"],
                "propagate": False,
            },
            "uvicorn": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False,
            },
            "uvicorn.error": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False,
            },
            "uvicorn.access": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False,
            },
            "sqlalchemy.engine": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False,
            },
        },
    }

    logging.config.dictConfig(config)
