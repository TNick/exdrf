import logging

from exdrf_qt.context import QtContext
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
)

import exdrf_dev.db.models  # noqa: F401

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main window for the application."""

    shutting_down: bool = False
    ctx: "QtContext"

    def __init__(self, c_string: str, populate: bool, parent=None):
        super().__init__(parent)

        # The context that indicates the database connection.
        self.ctx = QtContext(
            c_string=c_string,
            top_widget=self,
        )

        # Set the window title and icon
        self.setWindowTitle("ExDRF Line Search Showcase")

        # Change the size of the window.
        self.resize(239, 468)

    def signal_handler(self, *args):
        self.shutdown()

    def shutdown(self):
        logger.info("Shutting down")
        if self.shutting_down:
            logger.error("Exiting forcefully")
            raise SystemExit
        self.shutting_down = True

        QApplication.quit()
