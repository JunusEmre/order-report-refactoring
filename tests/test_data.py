"""Unit tests for order loading checks, cleaning rules, and value calculations."""

from pathlib import Path

import pandas as pd
from pandas.testing import assert_frame_equal
import pytest

from order_reporting.data import (
    REQUIRED_COLUMNS,
    add_order_values,
    load_orders,
    prepare_orders,
    validate_prepared_orders,
    validate_required_columns,
)
from order_reporting.exceptions import DataLoadError, DataValidationError


def _frame_with_required_columns(**overrides) -> pd.DataFrame:
    data = {column: ["placeholder"] for column in REQUIRED_COLUMNS}
    data.update(overrides)
    return pd.DataFrame(data)


def _valid_prepared(**overrides) -> pd.DataFrame:
    data = {
        "order_id": ["O1"],
        "order_date": ["2026-01-01"],
        "customer_id": ["C1"],
        "region": ["North"],
        "product_category": ["Books"],
        "quantity": [2.0],
        "unit_price": [100.0],
        "discount": [0.1],
        "returned": [False],
        "order_value": [200.0],
        "discounted_value": [180.0],
    }
    data.update(overrides)
    return pd.DataFrame(data)


def test_validate_required_columns_accepts_complete_data():
    orders = _frame_with_required_columns()

    validate_required_columns(orders)


def test_validate_required_columns_lists_missing_column_names():
    orders = _frame_with_required_columns()
    orders = orders.drop(columns=["discount", "returned"])

    with pytest.raises(DataValidationError) as error:
        validate_required_columns(orders)

    message = str(error.value)
    assert "Missing required columns:" in message
    assert message.index("discount") < message.index("returned")
    assert "discount" in message and "returned" in message


def test_validate_required_columns_rejects_empty_dataframe():
    orders = pd.DataFrame(columns=list(REQUIRED_COLUMNS))

    with pytest.raises(DataValidationError, match="no order rows"):
        validate_required_columns(orders)


def test_load_orders_missing_file_raises_data_load_error(tmp_path: Path):
    missing = tmp_path / "missing-orders.csv"

    with pytest.raises(DataLoadError) as error:
        load_orders(missing)

    assert "missing-orders.csv" in str(error.value)
    assert error.value.__cause__ is not None


def test_load_orders_undecodable_file_raises_data_load_error(tmp_path: Path):
    broken = tmp_path / "broken.csv"
    broken.write_bytes(b"\xff\xfe\x00not-utf8")

    with pytest.raises(DataLoadError) as error:
        load_orders(broken)

    assert "broken.csv" in str(error.value)


def test_load_orders_malformed_csv_raises_data_load_error(tmp_path: Path):
    malformed = tmp_path / "malformed.csv"
    malformed.write_text('order_id,region\n1,"unterminated', encoding="utf-8")

    with pytest.raises(DataLoadError) as error:
        load_orders(malformed)

    assert "malformed.csv" in str(error.value)
    assert error.value.__cause__ is not None


def test_load_orders_empty_file_raises_data_load_error(tmp_path: Path):
    empty = tmp_path / "empty.csv"
    empty.write_text("", encoding="utf-8")

    with pytest.raises(DataLoadError, match="empty.csv"):
        load_orders(empty)


def test_prepare_orders_normalizes_region_and_category_text():
    orders = pd.DataFrame(
        {
            "region": [" north ", "SOUTH", None, "  "],
            "product_category": ["electronics ", "HOME", None, " "],
            "quantity": [1, 1, 1, 1],
            "unit_price": [10.0, 10.0, 10.0, 10.0],
            "discount": [0.0, 0.0, 0.0, 0.0],
            "returned": ["false", "false", "false", "false"],
        }
    )

    prepared = prepare_orders(orders)

    assert list(prepared["region"]) == ["North", "South", "Unknown", "Unknown"]
    assert list(prepared["product_category"]) == [
        "Electronics",
        "Home",
        "Unknown",
        "Unknown",
    ]


def test_prepare_orders_converts_and_fills_numeric_fields():
    orders = pd.DataFrame(
        {
            "region": ["North", "South", "East"],
            "product_category": ["Books", "Home", "Books"],
            "quantity": ["2", None, "bad"],
            "unit_price": [10.0, 30.0, "unknown"],
            "discount": ["0.10", None, "unknown"],
            "returned": ["false", "false", "false"],
        }
    )

    prepared = prepare_orders(orders)

    assert list(prepared["quantity"]) == [2.0, 1.0, 1.0]
    assert list(prepared["unit_price"]) == [10.0, 30.0, 20.0]
    assert list(prepared["discount"]) == [0.10, 0.0, 0.0]


def test_prepare_orders_normalizes_returned_flags():
    orders = pd.DataFrame(
        {
            "region": ["North"] * 9,
            "product_category": ["Books"] * 9,
            "quantity": [1] * 9,
            "unit_price": [10.0] * 9,
            "discount": [0.0] * 9,
            "returned": [
                " True ",
                "YES",
                "1",
                " Ja ",
                "false",
                "no",
                "0",
                None,
                "maybe",
            ],
        }
    )

    prepared = prepare_orders(orders)

    assert list(prepared["returned"]) == [
        True,
        True,
        True,
        True,
        False,
        False,
        False,
        False,
        False,
    ]


def test_prepare_orders_logs_numeric_recovery_warnings(
    caplog: pytest.LogCaptureFixture,
):
    orders = pd.DataFrame(
        {
            "region": ["North", "South"],
            "product_category": ["Books", "Home"],
            "quantity": [None, "bad"],
            "unit_price": [10.0, "unknown"],
            "discount": [None, "unknown"],
            "returned": ["false", "false"],
        }
    )

    with caplog.at_level("WARNING", logger="order_reporting.data"):
        prepare_orders(orders)

    text = caplog.text
    assert "2 missing or invalid quantity" in text
    assert "1 missing or invalid unit price" in text
    assert "2 invalid discount values with 0" in text


def test_prepare_orders_logs_unrecognized_returned_warning(
    caplog: pytest.LogCaptureFixture,
):
    orders = pd.DataFrame(
        {
            "region": ["North", "South"],
            "product_category": ["Books", "Home"],
            "quantity": [1, 1],
            "unit_price": [10.0, 10.0],
            "discount": [0.0, 0.0],
            "returned": [None, "maybe"],
        }
    )

    with caplog.at_level("WARNING", logger="order_reporting.data"):
        prepared = prepare_orders(orders)

    assert list(prepared["returned"]) == [False, False]
    assert "2 blank or unrecognized returned values as false" in caplog.text


def test_add_order_values_calculates_order_and_discounted_value():
    orders = pd.DataFrame(
        {
            "quantity": [2],
            "unit_price": [100],
            "discount": [0.10],
        }
    )

    with_values = add_order_values(orders)

    assert with_values.loc[0, "order_value"] == 200
    assert with_values.loc[0, "discounted_value"] == 180


def test_prepare_orders_does_not_mutate_input_dataframe():
    orders = pd.DataFrame(
        {
            "region": [" north "],
            "product_category": ["electronics "],
            "quantity": [None],
            "unit_price": [10.0],
            "discount": [None],
            "returned": [" Yes "],
        }
    )
    original = orders.copy()

    prepare_orders(orders)

    assert_frame_equal(orders, original)


@pytest.mark.parametrize("column", ["order_id", "order_date", "customer_id"])
def test_validate_prepared_orders_rejects_blank_identifiers(column: str):
    orders = _valid_prepared(**{column: ["  "]})

    with pytest.raises(DataValidationError, match=column):
        validate_prepared_orders(orders)


def test_validate_prepared_orders_rejects_invalid_dates():
    orders = _valid_prepared(order_date=["not-a-date"])

    with pytest.raises(DataValidationError, match="order_date"):
        validate_prepared_orders(orders)


def test_validate_prepared_orders_rejects_negative_quantity():
    orders = _valid_prepared(quantity=[-1])

    with pytest.raises(DataValidationError, match="quantity"):
        validate_prepared_orders(orders)


def test_validate_prepared_orders_rejects_negative_unit_price():
    orders = _valid_prepared(unit_price=[-5])

    with pytest.raises(DataValidationError, match="unit_price"):
        validate_prepared_orders(orders)


@pytest.mark.parametrize("discount", [-0.1, 1.5])
def test_validate_prepared_orders_rejects_discount_outside_0_to_1(discount: float):
    orders = _valid_prepared(discount=[discount])

    with pytest.raises(DataValidationError, match="discount"):
        validate_prepared_orders(orders)


def test_validate_prepared_orders_rejects_all_invalid_unit_prices():
    orders = pd.DataFrame(
        {
            "order_id": ["O1", "O2"],
            "order_date": ["2026-01-01", "2026-01-02"],
            "customer_id": ["C1", "C2"],
            "region": ["North", "South"],
            "product_category": ["Books", "Home"],
            "quantity": [1, 1],
            "unit_price": ["bad", None],
            "discount": [0.0, 0.0],
            "returned": ["false", "false"],
        }
    )
    prepared = add_order_values(prepare_orders(orders))

    with pytest.raises(DataValidationError, match="median"):
        validate_prepared_orders(prepared)
