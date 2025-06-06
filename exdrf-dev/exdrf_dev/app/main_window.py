import logging

from exdrf_qt.context import QtContext
from PyQt5.QtWidgets import QApplication, QMainWindow

from exdrf_dev.app.main_window_ui import Ui_MainWindow
from exdrf_dev.qt_gen.menus import ExdrfMenus
from exdrf_dev.qt_gen.router import ExdrfRouter

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow, Ui_MainWindow):
    """Main window for the application."""

    menus: ExdrfMenus
    shutting_down: bool = False
    ctx: "QtContext"

    def __init__(self, db_string: str, Base, parent=None):
        super().__init__(parent)
        self.setup_ui(self)
        self.ctx = QtContext(
            c_string=db_string,
            top_widget=self,
            router=ExdrfRouter(
                ctx=None,  # type: ignore
                base_path="exdrf://navigation/resource",
            ),
        )
        self.ctx.router.ctx = self.ctx
        self.ctx.create_all_tables(Base)

        # Create the menus.
        self.menus = ExdrfMenus(ctx=self.ctx, parent=self.menu_concerns)

        # Set the window title and icon
        self.setWindowTitle("ExDRF Dev App")

    def signal_handler(self, *args):
        self.shutdown()

    def shutdown(self):
        logger.info("Shutting down")
        if self.shutting_down:
            logger.error("Exiting forcefully")
            raise SystemExit
        self.shutting_down = True

        QApplication.quit()
