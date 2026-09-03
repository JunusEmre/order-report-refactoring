"""Unit tests for the project's report configuration."""

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from order_reporting.config import DEFAULT_CONFIG, ReportConfig


def test_report_config_stores_input_and_output_as_paths():
    config = ReportConfig(
        input_path=Path("tmp/orders.csv"),
        output_dir=Path("tmp/reports"),
    )

    assert config.input_path == Path("tmp/orders.csv")
    assert config.output_dir == Path("tmp/reports")
    assert isinstance(config.input_path, Path)
    assert isinstance(config.output_dir, Path)


def test_report_config_cannot_be_changed_after_creation():
    config = ReportConfig(
        input_path=Path("tmp/orders.csv"),
        output_dir=Path("tmp/reports"),
    )

    with pytest.raises(FrozenInstanceError):
        config.input_path = Path("other.csv")


def test_default_config_uses_data_orders_and_output_paths():
    assert DEFAULT_CONFIG.input_path == Path("data/orders.csv")
    assert DEFAULT_CONFIG.output_dir == Path("output")
