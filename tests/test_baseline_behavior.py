"""Characterization tests for the original order_report.py behaviour.

These tests run the root entry point in an isolated temporary directory
and compare its CSV reports with protected Stage 1 fixtures. They exist
so later refactoring cannot change calculations, cleaning rules, report
structure, or file names unnoticed.
"""

from pathlib import Path
import shutil
import subprocess
import sys

import pandas as pd
from pandas.testing import assert_frame_equal
import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
ORIGINAL_SCRIPT = REPO_ROOT / "order_report.py"
PACKAGE_DIR = REPO_ROOT / "order_reporting"
ORIGINAL_ORDERS = REPO_ROOT / "data" / "orders.csv"
EXPECTED_DIR = Path(__file__).resolve().parent / "fixtures" / "expected"

REPORT_FILES = (
    "overview.csv",
    "sales_by_category.csv",
    "sales_by_region.csv",
    "returns_by_category.csv",
)


def run_original_program(tmp_path: Path) -> subprocess.CompletedProcess:
    """Copy the entry point, package, and data, then run the script in tmp_path."""
    shutil.copy2(ORIGINAL_SCRIPT, tmp_path / "order_report.py")
    shutil.copytree(
        PACKAGE_DIR,
        tmp_path / "order_reporting",
        ignore=shutil.ignore_patterns("__pycache__"),
    )

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    shutil.copy2(ORIGINAL_ORDERS, data_dir / "orders.csv")

    # The original program writes into output/ and does not create it.
    (tmp_path / "output").mkdir()

    return subprocess.run(
        [sys.executable, str(tmp_path / "order_report.py")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def read_report(path: Path) -> pd.DataFrame:
    """Read a generated or expected CSV report."""
    return pd.read_csv(path)


@pytest.fixture
def isolated_run(tmp_path: Path) -> tuple[subprocess.CompletedProcess, Path]:
    """Run the original program once per test in a fresh temporary directory."""
    completed = run_original_program(tmp_path)
    return completed, tmp_path / "output"


def test_program_exits_successfully(isolated_run):
    """The original program must finish without an error exit code."""
    completed, _output_dir = isolated_run
    assert completed.returncode == 0


def test_exactly_four_report_files_are_created(isolated_run):
    """Only the four known report file names may be written."""
    _completed, output_dir = isolated_run
    created = sorted(path.name for path in output_dir.glob("*.csv"))
    assert created == sorted(REPORT_FILES)


@pytest.mark.parametrize("filename", REPORT_FILES)
def test_report_matches_protected_fixture(isolated_run, filename):
    """Each report must match its Stage 1 fixture in columns, order, values, and dtypes."""
    _completed, output_dir = isolated_run
    actual = read_report(output_dir / filename)
    expected = read_report(EXPECTED_DIR / filename)
    assert_frame_equal(actual, expected, check_dtype=True, check_exact=True)


def test_overview_baseline_totals(isolated_run):
    """The overview report must keep the confirmed Stage 1 totals."""
    _completed, output_dir = isolated_run
    overview = read_report(output_dir / "overview.csv").set_index("metric")["value"]

    assert overview["total_sales"] == 138036.05
    assert overview["order_count"] == 80
    assert overview["return_count"] == 15


def test_category_totals_match_overview(isolated_run):
    """Category rows must add up to the same overall totals."""
    _completed, output_dir = isolated_run
    by_category = read_report(output_dir / "sales_by_category.csv")

    assert by_category["order_count"].sum() == 80
    assert by_category["returns"].sum() == 15
    assert by_category["total_sales"].sum() == pytest.approx(138036.05)


def test_region_totals_match_overview(isolated_run):
    """Region rows must add up to the same overall totals."""
    _completed, output_dir = isolated_run
    by_region = read_report(output_dir / "sales_by_region.csv")

    assert by_region["order_count"].sum() == 80
    assert by_region["returns"].sum() == 15
    assert by_region["total_sales"].sum() == pytest.approx(138036.05)


def test_category_return_rates(isolated_run):
    """Category return rates must stay at the Stage 1 baseline values."""
    _completed, output_dir = isolated_run
    rates = read_report(output_dir / "sales_by_category.csv").set_index(
        "product_category"
    )["return_rate"]

    assert rates["Electronics"] == 0.269
    assert rates["Home"] == 0.235
    assert rates["Sports"] == 0.125
    assert rates["Books"] == 0.095


def test_unknown_region_is_preserved(isolated_run):
    """The blank source region must still appear as normalized Unknown."""
    _completed, output_dir = isolated_run
    unknown = read_report(output_dir / "sales_by_region.csv").set_index("region").loc[
        "Unknown"
    ]

    assert unknown["order_count"] == 1
    assert unknown["returns"] == 1
    assert unknown["total_sales"] == 3196.0
    assert unknown["return_rate"] == 1.0
