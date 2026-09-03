"""Unit tests for in-memory report generation and file saving."""

from pathlib import Path

import pandas as pd
import pytest

from order_reporting.config import ReportConfig
from order_reporting.exceptions import ReportOutputError
from order_reporting.pipeline import generate_reports, run_pipeline, save_reports

REPORT_FILES = (
    "overview.csv",
    "sales_by_category.csv",
    "sales_by_region.csv",
    "returns_by_category.csv",
)


def _write_sample_orders(path: Path) -> None:
    """Write one order: quantity 2, price 100, discount 0.10 -> sales 180."""
    pd.DataFrame(
        {
            "order_id": ["O1"],
            "order_date": ["2026-01-01"],
            "customer_id": ["C1"],
            "region": ["North"],
            "product_category": ["Books"],
            "quantity": [2],
            "unit_price": [100],
            "discount": [0.10],
            "returned": ["false"],
        }
    ).to_csv(path, index=False)


def test_generate_reports_builds_frames_without_writing_files(tmp_path: Path):
    input_path = tmp_path / "inbox" / "orders.csv"
    output_dir = tmp_path / "unused_output"
    input_path.parent.mkdir()
    _write_sample_orders(input_path)
    config = ReportConfig(input_path=input_path, output_dir=output_dir)

    reports = generate_reports(config)

    assert list(reports.keys()) == list(REPORT_FILES)
    overview = reports["overview.csv"].set_index("metric")["value"]
    assert overview["total_sales"] == 180.0
    assert overview["order_count"] == 1
    assert overview["return_count"] == 0
    assert not output_dir.exists()
    assert list(tmp_path.glob("**/*.csv")) == [input_path]


def test_save_reports_writes_csv_files_to_given_directory(tmp_path: Path):
    output_dir = tmp_path / "reports"
    output_dir.mkdir()
    reports = {
        "overview.csv": pd.DataFrame({"metric": ["total_sales"], "value": [180.0]}),
        "sales_by_category.csv": pd.DataFrame({"product_category": ["Books"]}),
        "sales_by_region.csv": pd.DataFrame({"region": ["North"]}),
        "returns_by_category.csv": pd.DataFrame({"product_category": ["Books"]}),
    }

    save_reports(reports, output_dir)

    created = sorted(path.name for path in output_dir.glob("*.csv"))
    assert created == sorted(REPORT_FILES)
    saved_overview = pd.read_csv(output_dir / "overview.csv")
    assert saved_overview.loc[0, "value"] == 180.0


def test_save_reports_creates_missing_directory(tmp_path: Path):
    output_dir = tmp_path / "new" / "reports"
    reports = {
        "overview.csv": pd.DataFrame({"metric": ["total_sales"], "value": [180.0]}),
        "sales_by_category.csv": pd.DataFrame({"product_category": ["Books"]}),
        "sales_by_region.csv": pd.DataFrame({"region": ["North"]}),
        "returns_by_category.csv": pd.DataFrame({"product_category": ["Books"]}),
    }

    save_reports(reports, output_dir)

    assert output_dir.is_dir()
    assert (output_dir / "overview.csv").exists()


def test_save_reports_raises_when_output_location_cannot_be_used(tmp_path: Path):
    blocked = tmp_path / "not-a-directory"
    blocked.write_text("this is a file", encoding="utf-8")
    reports = {
        "overview.csv": pd.DataFrame({"metric": ["total_sales"], "value": [180.0]}),
    }

    with pytest.raises(ReportOutputError) as error:
        save_reports(reports, blocked)

    assert str(blocked) in str(error.value)
    assert error.value.__cause__ is not None


def test_run_pipeline_uses_config_paths_instead_of_production_paths(tmp_path: Path):
    input_path = tmp_path / "inbox" / "orders.csv"
    output_dir = tmp_path / "reports"
    input_path.parent.mkdir()
    _write_sample_orders(input_path)
    config = ReportConfig(input_path=input_path, output_dir=output_dir)

    reports = run_pipeline(config)

    created = sorted(path.name for path in output_dir.glob("*.csv"))
    assert created == sorted(REPORT_FILES)
    overview = pd.read_csv(output_dir / "overview.csv").set_index("metric")["value"]
    assert overview["total_sales"] == 180.0
    assert reports["overview.csv"].set_index("metric").at["order_count", "value"] == 1
    assert output_dir.is_dir()
    assert not (tmp_path / "data").exists()
    assert not (tmp_path / "output").exists()


def test_generate_reports_logs_operational_info(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
):
    input_path = tmp_path / "orders.csv"
    _write_sample_orders(input_path)
    config = ReportConfig(input_path=input_path, output_dir=tmp_path / "unused")

    with caplog.at_level("INFO"):
        generate_reports(config)

    text = caplog.text
    assert "Reading order data" in text
    assert "Loaded 1 order rows" in text
    assert "passed validation" in text
    assert "Creating order reports" in text
    assert "Saved " not in text
