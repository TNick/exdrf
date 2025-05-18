from typing import TYPE_CHECKING, Generic, Optional, TypeVar, cast

from PyQt5.QtCore import QRect, Qt
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import QAction, QHeaderView, QMenu, QTreeView, QWidget

from exdrf_qt.context_use import QtUseContext
from exdrf_qt.controls.search_line import SearchLine
from exdrf_qt.models import QtModel

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401

DBM = TypeVar("DBM")


class HeaderViewWithMenu(QHeaderView, QtUseContext, Generic[DBM]):
    """A header view that has a menu with actions to sort and filter the data.

    Attributes:
        ctx: The context of the application.
        search_line: The search line that is used to filter the data.
        search_section: The section that is used to filter the data.
    """

    ctx: "QtContext"
    search_line: Optional[SearchLine[DBM]]
    search_section: Optional[int]

    def __init__(self, parent: "QWidget", ctx: "QtContext"):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.ctx = ctx
        self.search_line = None
        self.search_section = None

    @property
    def qt_model(self) -> "QtModel[DBM]":
        """The model that is used to present the data in the list."""
        return cast("QtModel[DBM]", cast("QTreeView", self.parent()).model())

    @property
    def treeview(self) -> "QTreeView":
        """The tree view that is used to present the data in the list."""
        parent = self.parent()
        assert isinstance(parent, QTreeView), "Parent should be a QTreeView"
        return parent

    def contextMenuEvent(self, event):  # type: ignore
        section = self.logicalIndexAt(event.pos())
        if section < 0:
            return

        menu = QMenu(self)
        sort_asc = QAction(self.t("Sort Ascending", "Sort ascending"), self)
        sort_desc = QAction(self.t("Sort Descending", "Sort descending"), self)
        filter_action = QAction(
            self.get_icon("filter"),
            self.t("Filter...", "Filter"),
            self,
        )

        assert self.treeview is not None
        header = self.treeview.header()
        assert header is not None
        sort_order = header.sortIndicatorOrder()
        current_sort_col = header.sortIndicatorSection()

        if self.treeview.isSortingEnabled():
            if current_sort_col == section:
                if sort_order == Qt.SortOrder.AscendingOrder:
                    sort_asc.setCheckable(True)
                    sort_asc.setChecked(True)
                elif sort_order == Qt.SortOrder.DescendingOrder:
                    sort_desc.setCheckable(True)
                    sort_desc.setChecked(True)

        menu.addAction(sort_asc)
        menu.addAction(sort_desc)
        menu.addSeparator()
        menu.addAction(filter_action)

        sort_asc.triggered.connect(
            lambda: self.treeview.sortByColumn(
                section, Qt.SortOrder.AscendingOrder
            )
        )
        sort_desc.triggered.connect(
            lambda: self.treeview.sortByColumn(
                section, Qt.SortOrder.DescendingOrder
            )
        )
        filter_action.triggered.connect(lambda: self.show_search_line(section))

        menu.exec_(QCursor.pos())

    def show_search_line(self, section):
        if self.search_line is not None:
            self.search_line.hide()
            self.search_line.deleteLater()
            self.search_line = None

        parent = self.treeview

        self.search_section = section
        self.search_line = SearchLine(
            ctx=self.ctx,
            callback=lambda text, exact: self.apply_filter(
                section, text, exact
            ),
            parent=parent,
        )
        assert self.search_line is not None
        self.search_line.setFixedWidth(self.sectionSize(section))
        self.search_line.setFixedHeight(self.height() + 1)

        # Place just above the header
        x = self.sectionPosition(section) + 1
        w = self.sectionSize(section)
        y = 2
        h = self.height() + 1

        header_rect = QRect(x, y, w, h)

        pos = parent.mapToGlobal(header_rect.topLeft())
        parent_pos = parent.mapFromGlobal(pos)
        self.search_line.move(
            parent_pos.x(), max(0, parent_pos.y() - self.search_line.height())
        )
        self.search_line.show()
        self.search_line.setFocus()
        self.search_line.hide_and_apply_search.connect(
            lambda text, exact: self.hide_search_line_and_apply(
                section, text, exact
            )
        )

    def hide_search_line_and_apply(self, section, text, exact):
        self.apply_filter(section, text, exact)
        if self.search_line:
            try:
                self.search_line.hide()
                self.search_line.deleteLater()
                self.search_line = None
            except Exception:
                pass

    def apply_filter(self, section, text, exact):
        self.qt_model.apply_simple_search(
            text, exact, limit=self.qt_model.column_fields[section].name
        )
