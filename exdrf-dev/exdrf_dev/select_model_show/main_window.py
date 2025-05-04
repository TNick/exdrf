import logging

from exdrf_al.base import Base
from exdrf_qt.context import QtContext
from PyQt5.QtWidgets import (
    QApplication,
    QLineEdit,
    QMainWindow,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

import exdrf_dev.db.models  # noqa: F401
from exdrf_dev.db.populate import populate_session
from exdrf_dev.qt.parents.models.parents_one_col_model import QtParentNaMo

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

        # Populate the database with initial data.
        if populate:
            self.ctx.create_all_tables(Base)
            with self.ctx.session() as session:
                populate_session(
                    session,
                    num_parents=10000,
                    num_tags=1500,
                    max_children_per_parent=50,
                    max_tags_per_parent=30,
                    num_composite_models=80,
                    max_related_items_per_comp_model=30,
                )

        self.cw = QWidget(self)
        self.ly = QVBoxLayout()

        self.src_line = QLineEdit(self)
        self.src_line.setPlaceholderText("Enter search term")
        self.ly.addWidget(self.src_line)

        self.model = QtParentNaMo(ctx=self.ctx)

        self.tree = QTreeView(self)
        self.tree.setAlternatingRowColors(True)
        self.tree.setSelectionMode(QTreeView.SingleSelection)
        self.tree.setSelectionBehavior(QTreeView.SelectRows)
        self.tree.setModel(self.model)
        self.ly.addWidget(self.tree)

        self.ly.setContentsMargins(1, 1, 1, 1)
        self.ly.setSpacing(1)
        self.cw.setLayout(self.ly)

        self.setCentralWidget(self.cw)

        # Set the window title and icon
        self.setWindowTitle("ExDRF Field Editor Showcase")

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
