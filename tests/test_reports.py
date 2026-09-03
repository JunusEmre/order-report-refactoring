"""Unit tests for the public report-building functions."""

import pandas as pd

from order_reporting.reports import (
    create_all_reports,
    create_overview,
    create_returns_by_category,
    create_sales_by_category,
    create_sales_by_region,
)


def _prepared_orders() -> pd.DataFrame:
    """Four orders with values that are easy to check by hand.

    Books: 180 + 100 + 50 = 330 sales, 3 orders, 1 return, rate 0.333
    Home: 40 sales, 1 order, 1 return, rate 1.000
    North: same as Books
    South: same as Home
    """
    return pd.DataFrame(
        {
            "order_id": ["O1", "O2", "O3", "O4"],
            "region": ["North", "North", "North", "South"],
            "product_category": ["Books", "Books", "Books", "Home"],
            "returned": [False, True, False, True],
            "discounted_value": [180.0, 100.0, 50.0, 40.0],
        }
    )


def test_create_overview_reports_sales_orders_and_returns():
    overview = create_overview(_prepared_orders())
    values = overview.set_index("metric")["value"]

    assert list(overview.columns) == ["metric", "value"]
    assert list(overview["metric"]) == [
        "total_sales",
        "order_count",
        "return_count",
    ]
    assert values["total_sales"] == 370.0
    assert values["order_count"] == 4
    assert values["return_count"] == 2


def test_create_sales_by_category_sorts_rounds_and_keeps_column_order():
    by_category = create_sales_by_category(_prepared_orders())

    assert list(by_category.columns) == [
        "product_category",
        "order_count",
        "total_sales",
        "returns",
        "return_rate",
    ]
    assert list(by_category["product_category"]) == ["Books", "Home"]
    assert list(by_category["order_count"]) == [3, 1]
    assert list(by_category["total_sales"]) == [330.0, 40.0]
    assert list(by_category["returns"]) == [1, 1]
    assert list(by_category["return_rate"]) == [0.333, 1.0]


def test_create_sales_by_region_sorts_rounds_and_keeps_column_order():
    by_region = create_sales_by_region(_prepared_orders())

    assert list(by_region.columns) == [
        "region",
        "order_count",
        "total_sales",
        "returns",
        "return_rate",
    ]
    assert list(by_region["region"]) == ["North", "South"]
    assert list(by_region["order_count"]) == [3, 1]
    assert list(by_region["total_sales"]) == [330.0, 40.0]
    assert list(by_region["returns"]) == [1, 1]
    assert list(by_region["return_rate"]) == [0.333, 1.0]


def test_create_returns_by_category_sorts_by_return_rate():
    returns = create_returns_by_category(_prepared_orders())

    assert list(returns.columns) == [
        "product_category",
        "order_count",
        "returns",
        "return_rate",
    ]
    assert list(returns["product_category"]) == ["Home", "Books"]
    assert list(returns["order_count"]) == [1, 3]
    assert list(returns["returns"]) == [1, 1]
    assert list(returns["return_rate"]) == [1.0, 0.333]


def test_create_all_reports_returns_four_named_reports():
    reports = create_all_reports(_prepared_orders())

    assert list(reports.keys()) == [
        "overview.csv",
        "sales_by_category.csv",
        "sales_by_region.csv",
        "returns_by_category.csv",
    ]
    assert list(reports["overview.csv"].columns) == ["metric", "value"]
    assert list(reports["sales_by_category.csv"].columns) == [
        "product_category",
        "order_count",
        "total_sales",
        "returns",
        "return_rate",
    ]
    assert list(reports["sales_by_region.csv"].columns) == [
        "region",
        "order_count",
        "total_sales",
        "returns",
        "return_rate",
    ]
    assert list(reports["returns_by_category.csv"].columns) == [
        "product_category",
        "order_count",
        "returns",
        "return_rate",
    ]
