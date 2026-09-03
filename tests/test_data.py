"""Unit tests for order loading checks, cleaning rules, and value calculations."""

import pandas as pd
from pandas.testing import assert_frame_equal
import pytest

from order_reporting.data import (
    REQUIRED_COLUMNS,
    add_order_values,
    prepare_orders,
    validate_required_columns,
)


def _frame_with_required_columns(**overrides) -> pd.DataFrame:
    data = {column: ["placeholder"] for column in REQUIRED_COLUMNS}
    data.update(overrides)
    return pd.DataFrame(data)


def test_validate_required_columns_accepts_complete_data():
    orders = _frame_with_required_columns()

    validate_required_columns(orders)


def test_validate_required_columns_raises_fel_data_for_missing_column():
    orders = _frame_with_required_columns()
    orders = orders.drop(columns=["discount"])

    with pytest.raises(Exception) as error:
        validate_required_columns(orders)

    assert type(error.value) is Exception
    assert str(error.value) == "Fel data"


def test_prepare_orders_normalizes_region_and_category_text():
    orders = pd.DataFrame(
        {
            "region": [" north ", "SOUTH", None],
            "product_category": ["electronics ", "HOME", None],
            "quantity": [1, 1, 1],
            "unit_price": [10.0, 10.0, 10.0],
            "discount": [0.0, 0.0, 0.0],
            "returned": ["false", "false", "false"],
        }
    )

    prepared = prepare_orders(orders)

    assert list(prepared["region"]) == ["North", "South", "Unknown"]
    assert list(prepared["product_category"]) == ["Electronics", "Home", "Unknown"]


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
            "region": ["North"] * 8,
            "product_category": ["Books"] * 8,
            "quantity": [1] * 8,
            "unit_price": [10.0] * 8,
            "discount": [0.0] * 8,
            "returned": [
                " True ",
                "YES",
                "1",
                " Ja ",
                "false",
                "no",
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
    ]


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
