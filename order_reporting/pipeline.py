"""Coordinate loading, report creation, and saving."""

import logging
from pathlib import Path

import pandas as pd

from order_reporting.config import ReportConfig
from order_reporting.data import (
    add_order_values,
    load_orders,
    prepare_orders,
    validate_prepared_orders,
    validate_required_columns,
)
from order_reporting.exceptions import ReportOutputError
from order_reporting.reports import create_all_reports

logger = logging.getLogger(__name__)


def generate_reports(config: ReportConfig) -> dict[str, pd.DataFrame]:
    """Load, validate, prepare, and build all reports without writing files."""
    orders = load_orders(config.input_path)
    validate_required_columns(orders)
    prepared = add_order_values(prepare_orders(orders))
    validate_prepared_orders(prepared)
    logger.info("Creating order reports.")
    return create_all_reports(prepared)


def save_reports(reports: dict[str, pd.DataFrame], output_dir: Path) -> None:
    """Write each report DataFrame to CSV, creating output_dir if needed."""
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        for filename, frame in reports.items():
            frame.to_csv(output_dir / filename, index=False)
            logger.info("Saved %s", filename)
    except OSError as error:
        raise ReportOutputError(
            f"Could not write reports to {output_dir}"
        ) from error


def run_pipeline(config: ReportConfig) -> dict[str, pd.DataFrame]:
    """Generate all reports and save them using the given configuration."""
    reports = generate_reports(config)
    save_reports(reports, config.output_dir)
    return reports
