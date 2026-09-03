"""Command-line entry point for the order report program."""

from order_reporting.config import DEFAULT_CONFIG
from order_reporting.pipeline import generate_reports, save_reports


def main() -> None:
    """Read the default orders file and write the four CSV reports."""
    print("Startar orderrapport")
    try:
        reports = generate_reports(DEFAULT_CONFIG)
        row_count = int(
            reports["overview.csv"].set_index("metric").at["order_count", "value"]
        )
        print("Läste in", row_count, "rader")
        save_reports(reports, DEFAULT_CONFIG.output_dir)
        print("Sparade overview.csv")
        print("Sparade sales_by_category.csv")
        print("Sparade sales_by_region.csv")
        print("Sparade returns_by_category.csv")
        print("Klart")
    except Exception as error:
        print("Något gick fel:", error)


if __name__ == "__main__":
    main()
