"""Centralized logging configuration."""

from __future__ import annotations

import logging


LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def configure_logging(level: str) -> None:
    """Configure application logging once per process."""

    log_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(level=log_level, format=LOG_FORMAT, force=True)
    logging.captureWarnings(True)

