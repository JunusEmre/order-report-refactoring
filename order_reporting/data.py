"""Load, check, and prepare order data for reporting."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from order_reporting.exceptions import DataLoadError, DataValidationError

logger = logging.getLogger(__name__)

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

TRUE_RETURN_VALUES = ("true", "yes", "1", "ja")
FALSE_RETURN_VALUES = ("false", "no", "0")


def load_orders(path: Path) -> pd.DataFrame:
    """Read the orders CSV from path."""
    logger.info("Reading order data from %s", path)
    try:
        orders = pd.read_csv(path)
    except FileNotFoundError as error:
        raise DataLoadError(f"Order data file was not found: {path}") from error
    except UnicodeDecodeError as error:
        raise DataLoadError(
            f"Order data file could not be decoded: {path}"
        ) from error
    except pd.errors.EmptyDataError as error:
        raise DataLoadError(
            f"Order data file is empty or has no columns: {path}"
        ) from error
    except pd.errors.ParserError as error:
        raise DataLoadError(
            f"Order data file is not a valid CSV: {path}"
        ) from error
    except OSError as error:
        raise DataLoadError(f"Order data file could not be read: {path}") from error

    logger.info("Loaded %s order rows", len(orders))
    return orders


def validate_required_columns(orders: pd.DataFrame) -> None:
    """Reject missing columns or an empty orders table."""
    missing = sorted(REQUIRED_COLUMNS.difference(orders.columns))
    if missing:
        raise DataValidationError(
            "Missing required columns: " + ", ".join(missing)
        )
    if orders.empty:
        raise DataValidationError("Input data contains no order rows.")


def _blank_mask(series: pd.Series) -> pd.Series:
    """True where a value is missing, blank, or only whitespace."""
    return series.fillna("").astype(str).str.strip().eq("")


def _count_label(count: int, singular: str, plural: str) -> str:
    return singular if count == 1 else plural


def prepare_orders(orders: pd.DataFrame) -> pd.DataFrame:
    """Return a cleaned copy using the original filling and normalisation rules."""
    prepared = orders.copy()

    region_text = prepared["region"].fillna("").astype(str).str.strip()
    missing_regions = region_text.eq("")
    region_replacements = int(missing_regions.sum())
    if region_replacements:
        logger.warning(
            "Replaced %s missing or blank region values with Unknown.",
            region_replacements,
        )
    prepared["region"] = region_text.mask(missing_regions, "Unknown").str.title()

    category_text = prepared["product_category"].fillna("").astype(str).str.strip()
    missing_categories = category_text.eq("")
    category_replacements = int(missing_categories.sum())
    if category_replacements:
        logger.warning(
            "Replaced %s missing or blank product category values with Unknown.",
            category_replacements,
        )
    prepared["product_category"] = category_text.mask(
        missing_categories, "Unknown"
    ).str.title()

    numeric_quantity = pd.to_numeric(prepared["quantity"], errors="coerce")
    quantity_replacements = int(numeric_quantity.isna().sum())
    if quantity_replacements:
        logger.warning(
            "Replaced %s missing or invalid quantity values with 1.",
            quantity_replacements,
        )
    prepared["quantity"] = numeric_quantity.fillna(1)

    numeric_price = pd.to_numeric(prepared["unit_price"], errors="coerce")
    price_replacements = int(numeric_price.isna().sum())
    if price_replacements:
        logger.warning(
            "Replaced %s missing or invalid unit price values with the median of valid prices.",
            price_replacements,
        )
    if numeric_price.notna().any():
        prepared["unit_price"] = numeric_price.fillna(numeric_price.median())
    else:
        prepared["unit_price"] = numeric_price

    numeric_discount = pd.to_numeric(prepared["discount"], errors="coerce")
    discount_replacements = int(numeric_discount.isna().sum())
    if discount_replacements:
        logger.warning(
            "Replaced %s invalid discount values with 0.",
            discount_replacements,
        )
    prepared["discount"] = numeric_discount.fillna(0)

    returned_text = (
        prepared["returned"].fillna("").astype(str).str.strip().str.lower()
    )
    is_true = returned_text.isin(TRUE_RETURN_VALUES)
    is_recognized_false = returned_text.isin(FALSE_RETURN_VALUES)
    returned_fallbacks = int((~is_true & ~is_recognized_false).sum())
    if returned_fallbacks:
        logger.warning(
            "Interpreted %s blank or unrecognized returned values as false.",
            returned_fallbacks,
        )
    prepared["returned"] = is_true
    return prepared


def add_order_values(orders: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with order_value and discounted_value columns added."""
    with_values = orders.copy()
    with_values["order_value"] = with_values["quantity"] * with_values["unit_price"]
    with_values["discounted_value"] = with_values["order_value"] * (
        1 - with_values["discount"]
    )
    return with_values


def validate_prepared_orders(orders: pd.DataFrame) -> None:
    """Reject prepared data that cannot be turned into a reliable report."""
    for column in ("order_id", "order_date", "customer_id"):
        blank_count = int(_blank_mask(orders[column]).sum())
        if blank_count:
            label = _count_label(blank_count, "value", "values")
            raise DataValidationError(
                f"Column {column} contains {blank_count} missing or blank {label}."
            )

    unparseable_dates = pd.to_datetime(
        orders["order_date"], errors="coerce"
    ).isna()
    invalid_date_count = int(unparseable_dates.sum())
    if invalid_date_count:
        label = _count_label(invalid_date_count, "value", "values")
        raise DataValidationError(
            f"Column order_date contains {invalid_date_count} {label} "
            "that cannot be parsed as a date."
        )

    negative_quantity = int((orders["quantity"] < 0).sum())
    if negative_quantity:
        label = _count_label(negative_quantity, "value", "values")
        raise DataValidationError(
            f"Column quantity contains {negative_quantity} negative {label}."
        )

    negative_price = int((orders["unit_price"] < 0).sum())
    if negative_price:
        label = _count_label(negative_price, "value", "values")
        raise DataValidationError(
            f"Column unit_price contains {negative_price} negative {label}."
        )

    missing_price = int(orders["unit_price"].isna().sum())
    if missing_price:
        raise DataValidationError(
            "Column unit_price has no valid values, so a replacement median "
            "cannot be calculated."
        )

    invalid_discount = int(
        ((orders["discount"] < 0) | (orders["discount"] > 1)).sum()
    )
    if invalid_discount:
        label = _count_label(invalid_discount, "value", "values")
        raise DataValidationError(
            f"Column discount contains {invalid_discount} {label} outside the range 0 to 1."
        )

    logger.info("Order data passed validation.")
