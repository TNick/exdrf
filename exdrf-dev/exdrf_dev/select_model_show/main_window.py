import logging

from exdrf_al.base import Base
from exdrf_qt.context import QtContext
from exdrf_qt.controls.search_list import SearchList
from exdrf_qt.field_ed.fed_sel_multi import DrfSelMultiEditor
from exdrf_qt.field_ed.fed_sel_one import DrfSelOneEditor
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
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

        self.model1 = QtParentNaMo(ctx=self.ctx)

        self.cw = QWidget(self)
        self.ly = QVBoxLayout()

        self.plain_list = SearchList(
            ctx=self.ctx,
            model=self.model1,
            parent=self,
        )
        self.ly.addWidget(self.plain_list)

        self.model2 = QtParentNaMo(ctx=self.ctx)
        self.single_select = DrfSelOneEditor(
            ctx=self.ctx,
            model=self.model2,
            parent=self,
            nullable=True,
        )
        self.ly.addWidget(self.single_select)

        self.model3 = QtParentNaMo(ctx=self.ctx)
        self.multi_select = DrfSelMultiEditor(
            ctx=self.ctx,
            model=self.model3,
            parent=self,
            nullable=True,
        )
        self.ly.addWidget(self.multi_select)

        self.cw.setLayout(self.ly)
        self.setCentralWidget(self.cw)

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
