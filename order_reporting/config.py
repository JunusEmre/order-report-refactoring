"""Production paths for the order report program."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ReportConfig:
    """Input CSV path and output directory used by the reporting pipeline."""

    input_path: Path
    output_dir: Path


DEFAULT_CONFIG = ReportConfig(
    input_path=Path("data/orders.csv"),
    output_dir=Path("output"),
)
