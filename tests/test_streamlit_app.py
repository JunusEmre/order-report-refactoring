"""Smoke test for the Streamlit dashboard script."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).resolve().parents[1] / "streamlit_app.py"


def test_dashboard_loads_title_and_instructions():
    app = AppTest.from_file(str(APP_PATH))
    app.run()

    assert not app.exception
    assert app.title[0].value == "Order Report Dashboard"
    assert any("Upload a CSV file" in str(item.label) for item in app.file_uploader)
    assert any("Generate reports" in str(item.label) for item in app.button)
    assert any("reviewed the uploaded file" in str(item.label) for item in app.checkbox)
