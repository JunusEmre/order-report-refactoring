"""Logging setup for the command-line entry point."""

import logging


def configure_logging(level: int = logging.INFO) -> None:
    """Configure readable logs. Call this only from the application entry point."""
    logging.basicConfig(
        level=level,
        format="%(levelname)s %(name)s: %(message)s",
    )
