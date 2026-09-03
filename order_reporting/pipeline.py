"""Coordinate loading, report creation, and saving."""

from pathlib import Path

import pandas as pd

from order_reporting.config import ReportConfig
from order_reporting.data import (
    add_order_values,
    load_orders,
    prepare_orders,
    validate_required_columns,
)
from order_reporting.reports import create_all_reports


def generate_reports(config: ReportConfig) -> dict[str, pd.DataFrame]:
    """Load, validate, prepare, and build all reports without writing files."""
    orders = load_orders(config.input_path)
    validate_required_columns(orders)
    prepared = add_order_values(prepare_orders(orders))
    return create_all_reports(prepared)


def save_reports(reports: dict[str, pd.DataFrame], output_dir: Path) -> None:
    """Write each report DataFrame to CSV in output_dir."""
    for filename, frame in reports.items():
        frame.to_csv(output_dir / filename, index=False)


def run_pipeline(config: ReportConfig) -> dict[str, pd.DataFrame]:
    """Generate all reports and save them using the given configuration."""
    reports = generate_reports(config)
    save_reports(reports, config.output_dir)
    return reports
