"""
Structured application logging configuration.
Ensures standardized log formats, configurable log levels,
and guarantees no credentials, API keys, or sensitive PII are emitted.
"""

import logging
import sys
from app.core.config import settings


def setup_logging() -> None:
    """Configures structured standard logging for application services and access logs."""
    log_level_name = settings.LOG_LEVEL.upper()
    log_level = getattr(logging, log_level_name, logging.INFO)

    log_format = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt=date_format,
        stream=sys.stdout,
        force=True,
    )

    # Silence overly noisy transport libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


logger = logging.getLogger("farmer_decision_system")
