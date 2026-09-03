"""Load, check, and prepare order data for reporting."""

from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = {
    "order_id",
    "order_date",
    "customer_id",
    "region",
    "product_category",
    "quantity",
    "unit_price",
    "discount",
    "returned",
}

ACCEPTED_RETURN_VALUES = ("true", "yes", "1", "ja")


def load_orders(path: Path) -> pd.DataFrame:
    """Read the orders CSV from path."""
    return pd.read_csv(path)


def validate_required_columns(orders: pd.DataFrame) -> None:
    """Raise the original error if any required column is missing."""
    if not REQUIRED_COLUMNS.issubset(orders.columns):
        raise Exception("Fel data")


def prepare_orders(orders: pd.DataFrame) -> pd.DataFrame:
    """Return a cleaned copy using the original filling and normalisation rules."""
    prepared = orders.copy()

    prepared["region"] = (
        prepared["region"].fillna("Unknown").astype(str).str.strip().str.title()
    )
    prepared["product_category"] = (
        prepared["product_category"]
        .fillna("Unknown")
        .astype(str)
        .str.strip()
        .str.title()
    )
    prepared["quantity"] = pd.to_numeric(
        prepared["quantity"], errors="coerce"
    ).fillna(1)
    prepared["unit_price"] = pd.to_numeric(
        prepared["unit_price"], errors="coerce"
    )
    prepared["unit_price"] = prepared["unit_price"].fillna(
        prepared["unit_price"].median()
    )
    prepared["discount"] = pd.to_numeric(
        prepared["discount"], errors="coerce"
    ).fillna(0)
    prepared["returned"] = (
        prepared["returned"]
        .fillna("false")
        .astype(str)
        .str.strip()
        .str.lower()
        .isin(ACCEPTED_RETURN_VALUES)
    )
    return prepared


def add_order_values(orders: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with order_value and discounted_value columns added."""
    with_values = orders.copy()
    with_values["order_value"] = (
        with_values["quantity"] * with_values["unit_price"]
    )
    with_values["discounted_value"] = with_values["order_value"] * (
        1 - with_values["discount"]
    )
    return with_values
