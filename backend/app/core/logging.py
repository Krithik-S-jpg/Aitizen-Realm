"""Logging configuration for Aitizen Realm."""

import logging
import sys

from app.core.config import settings


def setup_logging() -> None:
    """Configures the standard Python logging system."""
    logging.basicConfig(
        level=settings.LOG_LEVEL.upper(),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )
