"""Build the four order reports as in-memory DataFrames."""

import pandas as pd


def create_overview(orders: pd.DataFrame) -> pd.DataFrame:
    """Build the whole-dataset totals report."""
    total_sales = round(orders["discounted_value"].sum(), 2)
    number_of_orders = orders["order_id"].nunique()
    number_of_returns = int(orders["returned"].sum())
    return pd.DataFrame(
        {
            "metric": ["total_sales", "order_count", "return_count"],
            "value": [total_sales, number_of_orders, number_of_returns],
        }
    )


def _summarize_sales(orders: pd.DataFrame, group_column: str) -> pd.DataFrame:
    """Group orders and calculate sales, returns, and return rate."""
    summary = orders.groupby(group_column, as_index=False).agg(
        order_count=("order_id", "nunique"),
        total_sales=("discounted_value", "sum"),
        returns=("returned", "sum"),
    )
    summary["total_sales"] = summary["total_sales"].round(2)
    summary["return_rate"] = (
        summary["returns"] / summary["order_count"]
    ).round(3)
    return (
        summary.sort_values("total_sales", ascending=False).reset_index(drop=True)
    )


def create_sales_by_category(orders: pd.DataFrame) -> pd.DataFrame:
    """Build sales and returns grouped by product category."""
    return _summarize_sales(orders, "product_category")


def create_sales_by_region(orders: pd.DataFrame) -> pd.DataFrame:
    """Build sales and returns grouped by region."""
    return _summarize_sales(orders, "region")


def create_returns_by_category(orders: pd.DataFrame) -> pd.DataFrame:
    """Build return counts and rates grouped by product category."""
    summary = orders.groupby("product_category", as_index=False).agg(
        order_count=("order_id", "nunique"),
        returns=("returned", "sum"),
    )
    summary["return_rate"] = (
        summary["returns"] / summary["order_count"]
    ).round(3)
    return (
        summary.sort_values("return_rate", ascending=False).reset_index(drop=True)
    )


def create_all_reports(orders: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Return all four reports keyed by their original CSV file names."""
    return {
        "overview.csv": create_overview(orders),
        "sales_by_category.csv": create_sales_by_category(orders),
        "sales_by_region.csv": create_sales_by_region(orders),
        "returns_by_category.csv": create_returns_by_category(orders),
    }
