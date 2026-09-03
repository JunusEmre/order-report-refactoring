"""Command-line entry point for the order report program."""

import logging

from order_reporting.config import DEFAULT_CONFIG
from order_reporting.exceptions import OrderReportError
from order_reporting.logging_config import configure_logging
from order_reporting.pipeline import generate_reports, save_reports

logger = logging.getLogger(__name__)


def main() -> int:
    """Run the order report pipeline and return a process exit code."""
    configure_logging()
    try:
        logger.info("Starting the order report.")
        reports = generate_reports(DEFAULT_CONFIG)
        save_reports(reports, DEFAULT_CONFIG.output_dir)
        logger.info("Order report completed successfully.")
        return 0
    except OrderReportError as error:
        logger.error("%s", error)
        return 1
    except Exception:
        logger.exception("Unexpected error while creating the order report.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
