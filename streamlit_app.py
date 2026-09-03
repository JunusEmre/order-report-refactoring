"""Streamlit dashboard for validating orders and generating reports."""

from __future__ import annotations

from collections.abc import Callable
from hashlib import sha256
import io
import logging
from typing import TypeVar

import pandas as pd
import streamlit as st

from order_reporting.exceptions import DataLoadError, OrderReportError
from order_reporting.pipeline import process_orders

logger = logging.getLogger(__name__)

REPORT_FILES = (
    "overview.csv",
    "sales_by_category.csv",
    "sales_by_region.csv",
    "returns_by_category.csv",
)

T = TypeVar("T")


class _WarningListHandler(logging.Handler):
    """Collect warning messages without configuring application-wide logging."""

    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self.messages: list[str] = []
        self.setFormatter(logging.Formatter("%(message)s"))

    def emit(self, record: logging.LogRecord) -> None:
        if record.levelno == logging.WARNING:
            self.messages.append(self.format(record))


def read_csv_bytes(data: bytes) -> pd.DataFrame:
    """Read uploaded CSV bytes into a DataFrame without changing values."""
    try:
        return pd.read_csv(io.BytesIO(data))
    except UnicodeDecodeError as error:
        raise DataLoadError(
            "The uploaded file could not be decoded as text."
        ) from error
    except pd.errors.EmptyDataError as error:
        raise DataLoadError(
            "The uploaded file is empty or has no columns."
        ) from error
    except pd.errors.ParserError as error:
        raise DataLoadError("The uploaded file is not a valid CSV.") from error


def dataframe_to_csv_bytes(frame: pd.DataFrame) -> bytes:
    """Return CSV bytes for a report using the original column order and no index."""
    return frame.to_csv(index=False).encode("utf-8")


def overview_metric_values(overview: pd.DataFrame) -> tuple[float, int, int]:
    """Read total sales, order count, and return count from the overview report."""
    values = overview.set_index("metric")["value"]
    return (
        float(values["total_sales"]),
        int(values["order_count"]),
        int(values["return_count"]),
    )


def collect_warning_messages(action: Callable[[], T]) -> tuple[T, list[str]]:
    """Run action and return distinct WARNING messages from order_reporting."""
    package_logger = logging.getLogger("order_reporting")
    handler = _WarningListHandler()
    package_logger.addHandler(handler)
    try:
        result = action()
        return result, list(dict.fromkeys(handler.messages))
    finally:
        package_logger.removeHandler(handler)


def reset_results_if_file_changed(state: dict, file_signature: str) -> None:
    """Clear stored reports when a different file is uploaded."""
    if state.get("file_signature") != file_signature:
        state["file_signature"] = file_signature
        state["reports"] = None
        state["warnings"] = []
        state["error"] = None


def _render_report_tab(
    title: str, frame: pd.DataFrame, chart_x: str | None = None, chart_y: str | None = None
) -> None:
    """Show one report table and an optional bar chart from that table."""
    st.subheader(title)
    st.dataframe(frame, use_container_width=True)
    if chart_x is not None and chart_y is not None:
        st.bar_chart(frame, x=chart_x, y=chart_y)


def render() -> None:
    """Draw the Order Report Dashboard."""
    st.set_page_config(
        page_title="Order Report Dashboard",
        page_icon="📊",
        layout="wide",
    )
    st.title("Order Report Dashboard")
    st.write(
        "Upload an order CSV file, review it, then generate sales and return "
        "reports. The dashboard validates the file and uses the same reporting "
        "engine as the command-line program."
    )
    st.markdown(
        """
1. **Upload** a CSV file of orders.
2. **Review and confirm** the previewed table.
3. **Generate and download** the sales and return reports.
"""
    )

    uploaded = st.file_uploader("Upload a CSV file", type=["csv"])
    orders: pd.DataFrame | None = None

    if uploaded is None:
        reset_results_if_file_changed(st.session_state, "")
    else:
        file_bytes = uploaded.getvalue()
        reset_results_if_file_changed(st.session_state, sha256(file_bytes).hexdigest())
        try:
            orders = read_csv_bytes(file_bytes)
        except DataLoadError as error:
            st.error(str(error))
        else:
            st.caption(
                f"File: **{uploaded.name}** · {len(orders)} rows · {len(orders.columns)} columns"
            )
            st.dataframe(orders, use_container_width=True, height=360)

    confirmed = st.checkbox(
        "I have reviewed the uploaded file and want to generate the reports."
    )
    generate_clicked = st.button(
        "Generate reports",
        type="primary",
        disabled=orders is None or not confirmed,
    )

    if generate_clicked and orders is not None:
        try:
            reports, warnings = collect_warning_messages(
                lambda: process_orders(orders)
            )
            st.session_state["reports"] = reports
            st.session_state["warnings"] = warnings
            st.session_state["error"] = None
        except OrderReportError as error:
            st.session_state["reports"] = None
            st.session_state["warnings"] = []
            st.session_state["error"] = str(error)
        except Exception:
            logger.exception("Unexpected dashboard failure while generating reports.")
            st.session_state["reports"] = None
            st.session_state["warnings"] = []
            st.session_state["error"] = (
                "An unexpected error occurred while generating the reports."
            )

    if st.session_state.get("error"):
        st.error(st.session_state["error"])

    reports = st.session_state.get("reports")
    if not reports:
        return

    st.success("Reports generated successfully.")
    for warning in st.session_state.get("warnings", []):
        st.warning(warning)

    total_sales, order_count, return_count = overview_metric_values(
        reports["overview.csv"]
    )
    metric_one, metric_two, metric_three = st.columns(3)
    metric_one.metric("Total sales", f"{total_sales:,.2f}")
    metric_two.metric("Order count", f"{order_count:,}")
    metric_three.metric("Return count", f"{return_count:,}")

    overview_tab, category_tab, region_tab, returns_tab, downloads_tab = st.tabs(
        [
            "Overview",
            "Sales by Category",
            "Sales by Region",
            "Returns by Category",
            "Downloads",
        ]
    )
    with overview_tab:
        _render_report_tab("Overview", reports["overview.csv"])
    with category_tab:
        _render_report_tab(
            "Sales by category",
            reports["sales_by_category.csv"],
            chart_x="product_category",
            chart_y="total_sales",
        )
    with region_tab:
        _render_report_tab(
            "Sales by region",
            reports["sales_by_region.csv"],
            chart_x="region",
            chart_y="total_sales",
        )
    with returns_tab:
        _render_report_tab(
            "Returns by category",
            reports["returns_by_category.csv"],
            chart_x="product_category",
            chart_y="return_rate",
        )
    with downloads_tab:
        st.subheader("Download reports")
        st.write("Each file matches the command-line report of the same name.")
        for filename in REPORT_FILES:
            st.download_button(
                label=f"Download {filename}",
                data=dataframe_to_csv_bytes(reports[filename]),
                file_name=filename,
                mime="text/csv",
                key=f"download-{filename}",
            )


if __name__ == "__main__":
    render()
