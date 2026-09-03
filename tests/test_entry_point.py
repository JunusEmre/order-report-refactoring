"""Tests for the command-line entry point and import side effects."""

from pathlib import Path
import os
import shutil
import subprocess
import sys

import pytest

import order_report
from order_reporting.config import ReportConfig


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_main_returns_1_for_missing_input(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(
        order_report,
        "DEFAULT_CONFIG",
        ReportConfig(tmp_path / "missing.csv", tmp_path / "reports"),
    )

    assert order_report.main() == 1


def test_main_returns_0_for_teacher_dataset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    input_path = tmp_path / "data" / "orders.csv"
    output_dir = tmp_path / "output"
    input_path.parent.mkdir()
    shutil.copy2(REPO_ROOT / "data" / "orders.csv", input_path)
    monkeypatch.setattr(
        order_report,
        "DEFAULT_CONFIG",
        ReportConfig(input_path, output_dir),
    )

    assert order_report.main() == 0
    assert (output_dir / "overview.csv").exists()


def test_imports_do_not_run_pipeline_or_write_files(tmp_path: Path):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "import order_report; import order_reporting; "
            "import order_reporting.config; import order_reporting.data; "
            "import order_reporting.pipeline; import order_reporting.reports; "
            "import order_reporting.exceptions; import order_reporting.logging_config",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )

    assert completed.returncode == 0
    assert completed.stdout == ""
    assert "Starting the order report" not in completed.stderr
    assert list(tmp_path.rglob("*.csv")) == []
