from typing import TYPE_CHECKING, Generic, Optional, TypeVar, cast

from exdrf.filter import FilterVisitor
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

    This is a modified version of the QHeaderView class that adds a menu with
    actions to sort and filter the data.

    The menu is shown when the user right-clicks on the header.

    Attributes:
        ctx: The context of the application. search_line: The search line that
        is used to filter the data. search_section: The section that is used to
        filter the data.
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
        """The tree view that is used to present the data in the list.

        We assume that the parent is a tree-view,
        """
        parent = self.parent()
        assert isinstance(parent, QTreeView), "Parent should be a QTreeView"
        return parent

    def contextMenuEvent(self, event):  # type: ignore
        """Show a context menu when the user right-clicks on the header.

        Args:
            event: The event that triggered the context menu.
        """
        section = self.logicalIndexAt(event.pos())
        if section < 0:
            return

        menu = QMenu(self)

        # Sort ascending
        ac_sort_asc = QAction(
            self.get_icon("sort_asc_az"),
            self.t("cmn.sort.ascending", "Sort ascending"),
            self,
        )
        ac_sort_asc.triggered.connect(
            lambda: self.treeview.sortByColumn(
                section, Qt.SortOrder.AscendingOrder
            )
        )

        # Sort descending
        ac_sort_desc = QAction(
            self.get_icon("sort_desc_az"),
            self.t("cmn.sort.descending", "Sort descending"),
            self,
        )
        ac_sort_desc.triggered.connect(
            lambda: self.treeview.sortByColumn(
                section, Qt.SortOrder.DescendingOrder
            )
        )

        # Filter
        filter_action = QAction(
            self.get_icon("filter"),
            self.t("cmn.filter.title", "Filter..."),
            self,
        )
        filter_action.triggered.connect(lambda: self.show_search_line(section))

        sort_order = self.sortIndicatorOrder()
        current_sort_col = self.sortIndicatorSection()

        if self.treeview.isSortingEnabled():
            if current_sort_col == section:
                if sort_order == Qt.SortOrder.AscendingOrder:
                    ac_sort_asc.setCheckable(True)
                    ac_sort_asc.setChecked(True)
                elif sort_order == Qt.SortOrder.DescendingOrder:
                    ac_sort_desc.setCheckable(True)
                    ac_sort_desc.setChecked(True)

            menu.addAction(ac_sort_asc)
            menu.addAction(ac_sort_desc)
            menu.addSeparator()
        menu.addAction(filter_action)

        menu.exec_(QCursor.pos())

    def show_search_line(self, section: int):
        """Show the search line for the given section.

        Args:
            section: The 0-based index of the section to show the search line
            for.
        """
        if self.search_line is not None:
            self.search_line.hide()
            self.search_line.deleteLater()
            self.search_line = None

        parent = self.treeview

        self.search_section = section

        # Create the search line.
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

        # Get the current filter.
        current_filter = self.qt_model.filters
        current_filter_fld = self.qt_model.column_fields[section].name

        search_line = self.search_line

        class Visitor(FilterVisitor):
            def visit_field(self, filter: dict):
                if (
                    filter["fld"] == current_filter_fld
                    and filter["op"] == "ilike"
                ):
                    value = filter["vl"]
                    if isinstance(value, str):
                        if value.startswith("%") and value.endswith("%"):
                            value = value[1:-1]
                        search_line.setText(value)

        Visitor(current_filter).run(current_filter)

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

    def hide_search_line_and_apply(self, section: int, text: str, exact: bool):
        """Hide the search line and apply the filter.

        Args:
            section: The 0-based index of the section to apply the filter to.
            text: The text to filter the data by.
            exact: Whether the filter should be an exact match.
        """
        self.apply_filter(section, text, exact)
        if self.search_line:
            try:
                self.search_line.hide()
                self.search_line.deleteLater()
                self.search_line = None
            except Exception:
                pass

    def apply_filter(self, section: int, text: str, exact: bool):
        """Apply a filter to the data.

        Args:
            section: The 0-based index of the section to apply the filter to.
            text: The text to filter the data by.
            exact: Whether the filter should be an exact match.
        """
        self.qt_model.apply_simple_search(
            text, exact, limit=self.qt_model.column_fields[section].name
        )
