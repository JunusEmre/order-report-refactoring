"""Expected application errors for the order report program."""


class OrderReportError(Exception):
    """Base exception for expected order-report failures."""


class DataLoadError(OrderReportError):
    """Raised when order data cannot be read."""


class DataValidationError(OrderReportError):
    """Raised when order data cannot be safely processed."""


class ReportOutputError(OrderReportError):
    """Raised when report files cannot be written."""
