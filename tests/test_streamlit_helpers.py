"""Tests for dashboard helpers and the shared in-memory reporting path."""

from pathlib import Path
import logging

import pandas as pd
from pandas.testing import assert_frame_equal
import pytest

from order_reporting.config import ReportConfig
from order_reporting.exceptions import DataLoadError
from order_reporting.pipeline import generate_reports, process_orders
from streamlit_app import (
    collect_warning_messages,
    dataframe_to_csv_bytes,
    overview_metric_values,
    read_csv_bytes,
    reset_results_if_file_changed,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_DIR = REPO_ROOT / "tests" / "fixtures" / "expected"


def test_dataframe_to_csv_bytes_preserves_columns_and_omits_index():
    frame = pd.DataFrame({"metric": ["total_sales"], "value": [180.0]})

    text = dataframe_to_csv_bytes(frame).decode("utf-8")

    assert text.startswith("metric,value")
    assert ",0," not in text
    assert "total_sales,180.0" in text.replace("\r\n", "\n")


def test_overview_metric_values_reads_existing_report():
    overview = pd.DataFrame(
        {
            "metric": ["total_sales", "order_count", "return_count"],
            "value": [138036.05, 80.0, 15.0],
        }
    )

    total_sales, order_count, return_count = overview_metric_values(overview)

    assert total_sales == 138036.05
    assert order_count == 80
    assert return_count == 15


def test_process_orders_matches_teacher_baseline_totals():
    orders = pd.read_csv(REPO_ROOT / "data" / "orders.csv")

    reports = process_orders(orders)
    total_sales, order_count, return_count = overview_metric_values(
        reports["overview.csv"]
    )

    assert total_sales == 138036.05
    assert order_count == 80
    assert return_count == 15
    assert list(reports["sales_by_category.csv"]["product_category"]) == list(
        pd.read_csv(EXPECTED_DIR / "sales_by_category.csv")["product_category"]
    )


def test_process_orders_matches_file_pipeline_for_teacher_data(tmp_path: Path):
    input_path = REPO_ROOT / "data" / "orders.csv"
    from_file = generate_reports(
        ReportConfig(input_path=input_path, output_dir=tmp_path / "unused")
    )
    from_memory = process_orders(pd.read_csv(input_path))

    for filename, frame in from_memory.items():
        assert_frame_equal(frame, from_file[filename])
    assert not (tmp_path / "unused").exists()


def test_read_csv_bytes_rejects_empty_file():
    with pytest.raises(DataLoadError, match="empty"):
        read_csv_bytes(b"")


def test_collect_warning_messages_returns_distinct_warnings_and_removes_handler():
    orders = pd.DataFrame(
        {
            "order_id": ["O1", "O2"],
            "order_date": ["2026-01-01", "2026-01-02"],
            "customer_id": ["C1", "C2"],
            "region": [None, "North"],
            "product_category": ["Books", "Home"],
            "quantity": [1, 1],
            "unit_price": [10.0, 10.0],
            "discount": [0.0, "unknown"],
            "returned": ["false", "false"],
        }
    )
    package_logger = logging.getLogger("order_reporting")
    handlers_before = list(package_logger.handlers)

    reports, first = collect_warning_messages(lambda: process_orders(orders))
    _, second = collect_warning_messages(lambda: process_orders(orders))

    assert reports["overview.csv"] is not None
    assert first == second
    assert len(first) == len(set(first))
    assert any("region" in message for message in first)
    assert any("discount" in message for message in first)
    assert list(package_logger.handlers) == handlers_before


def test_reset_results_if_file_changed_clears_previous_reports():
    state = {
        "file_signature": "old",
        "reports": {"overview.csv": pd.DataFrame()},
        "warnings": ["old warning"],
        "error": "old error",
    }

    reset_results_if_file_changed(state, "new")

    assert state["file_signature"] == "new"
    assert state["reports"] is None
    assert state["warnings"] == []
    assert state["error"] is None


def test_reset_results_if_file_changed_keeps_results_for_same_file():
    reports = {"overview.csv": pd.DataFrame({"metric": ["total_sales"]})}
    state = {
        "file_signature": "same",
        "reports": reports,
        "warnings": ["keep"],
        "error": None,
    }

    reset_results_if_file_changed(state, "same")

    assert state["reports"] is reports
    assert state["warnings"] == ["keep"]
