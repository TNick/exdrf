import logging

from exdrf_qt.context import QtContext
from PyQt5.QtWidgets import QApplication, QMainWindow

from exdrf_dev.field_ed_show.main_window_ui import Ui_MainWindow

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow, Ui_MainWindow):
    """Main window for the application."""

    shutting_down: bool = False
    ctx: "QtContext"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ctx = QtContext(c_string="", top_widget=self)
        self.setup_ui(self)

        # Set the window title and icon
        self.setWindowTitle("ExDRF Field Editor Showcase")

    def signal_handler(self, *args):
        self.shutdown()

    def shutdown(self):
        logger.info("Shutting down")
        if self.shutting_down:
            logger.error("Exiting forcefully")
            raise SystemExit
        self.shutting_down = True

        QApplication.quit()
