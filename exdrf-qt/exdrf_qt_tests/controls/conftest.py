"""Fixtures for controls tests."""

import os

import pytest
from PySide6.QtWidgets import QApplication

from exdrf_qt.context import LocalSettings, QtContext

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def qt_app():
    """Ensure a single QApplication exists for Qt-based tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def mock_ctx(qt_app):
    """Minimal QtContext for RecordComparatorBase and similar widgets."""
    return QtContext(
        c_string="",
        stg=LocalSettings(),
        top_widget=None,  # type: ignore[arg-type]
        schema=os.environ.get("EXDRF_DB_SCHEMA", "public"),
    )
