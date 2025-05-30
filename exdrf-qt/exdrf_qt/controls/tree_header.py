from typing import TYPE_CHECKING, Generic, Optional, Set, TypeVar, cast

from exdrf.filter import FieldFilter, FilterVisitor, insert_quick_search
from PyQt5.QtCore import QEvent, QRect, Qt
from PyQt5.QtGui import QCursor, QMouseEvent, QPainter, QPen
from PyQt5.QtWidgets import (
    QAction,
    QDialog,
    QHeaderView,
    QMenu,
    QStyle,
    QStyleOptionHeader,
    QTreeView,
    QWidget,
)

from exdrf_qt.context_use import QtUseContext
from exdrf_qt.controls.column_sel.column_sel import ColumnSelDlg
from exdrf_qt.controls.search_line import SearchLine
from exdrf_qt.models import QtModel

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401

DBM = TypeVar("DBM")


class HeaderViewWithMenu(QHeaderView, QtUseContext, Generic[DBM]):
    """A header view with sorting, filtering, and dynamic filter icon
    capabilities.

    The menu is shown when the user right-clicks on the header. Shows a filter
    icon when a section is filtered. The search line appears dynamically when
    the mouse hovers over a filterable section.

    Attributes:
        ctx: The application context.
        search_line: The widget for filter input.
        search_section: Currently active section for filtering.
        filtered_sections: Set of sections currently filtered.
        filtered_sections: the list of sections that are filtered.
    """

    ctx: "QtContext"
    search_line: Optional[SearchLine[DBM]]
    search_section: Optional[int]
    filtered_sections: Set[int]

    def __init__(self, parent: "QWidget", ctx: "QtContext"):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.ctx = ctx
        self.search_line = None
        self.search_section = None
        self.filtered_sections = set()
        self.setMouseTracking(True)

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

    def mouseMoveEvent(self, e: Optional[QMouseEvent]):
        assert e is not None
        section = self.logicalIndexAt(e.pos())
        if section >= 0:
            # Compute the location of the activation area.
            w = self.sectionSize(section)
            h = self.height()
            x = self.sectionPosition(section) + w - h
            full_size = QRect(x, 0, w, h)

            # Adjust for horizontal scroll position
            h_scroll = self.treeview.horizontalScrollBar()
            assert h_scroll is not None
            scroll_offset = h_scroll.value()
            full_size.moveLeft(x - scroll_offset)

            # Check if the mouse is inside the activation area.
            if full_size.contains(e.pos()):
                self.show_search_line(section)
                if self.search_line is not None:
                    self.search_line.permanent = False
        elif (
            self.search_line is not None
            and not self.search_line.permanent
            and self.search_line.geometry().contains(e.pos())
        ):
            self.hide_search_line()
        super().mouseMoveEvent(e)

    def leaveEvent(self, e: Optional[QEvent]) -> None:  # type: ignore
        """Handle mouse leaving the header widget.

        This ensures we hide the search line when mouse moves outside the
        header, since mouseMoveEvent won't fire once outside the widget bounds.
        """
        if (
            self.search_line is not None
            and not self.search_line.permanent
            and not self.rect().contains(
                self.mapFromGlobal(self.cursor().pos())
            )
        ):
            self.hide_search_line()
        super().leaveEvent(e)

    def create_sort_actions(self, menu: QMenu, section: int):
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

        return ac_sort_asc, ac_sort_desc

    def create_filter_action(self, menu: QMenu, section: int):
        ac_filter = QAction(
            self.get_icon("filter"),
            self.t("cmn.filter.title", "Filter..."),
            self,
        )
        ac_filter.triggered.connect(lambda: self.show_search_line(section))
        return ac_filter

    def create_show_columns_action(self, menu: QMenu, section: int):
        ac_show = QAction(
            self.get_icon("column_double"),
            self.t("cmn.columns", "Columns"),
            self,
        )
        ac_show.triggered.connect(self.on_choose_columns)
        return ac_show

    def contextMenuEvent(self, event):  # type: ignore
        """Show a context menu when the user right-clicks on the header.

        Args:
            event: The event that triggered the context menu.
        """
        section = self.logicalIndexAt(event.pos())
        if section < 0:
            return

        menu = QMenu(self)

        ac_sort_asc, ac_sort_desc = self.create_sort_actions(menu, section)

        # Filter
        ac_filter = self.create_filter_action(menu, section)

        # Choose column visibility.
        ac_show = self.create_show_columns_action(menu, section)

        sort_order = self.sortIndicatorOrder()
        current_sort_col = self.sortIndicatorSection()

        if self.treeview.isSortingEnabled() and ac_sort_asc and ac_sort_desc:
            if current_sort_col == section:
                ac_sort_asc.setCheckable(True)
                ac_sort_asc.setChecked(
                    sort_order == Qt.SortOrder.AscendingOrder
                )
                ac_sort_desc.setCheckable(True)
                ac_sort_desc.setChecked(
                    sort_order == Qt.SortOrder.DescendingOrder
                )

            menu.addAction(ac_sort_asc)
            menu.addAction(ac_sort_desc)
            menu.addSeparator()

        if ac_filter:
            menu.addAction(ac_filter)

        if ac_show:
            menu.addAction(ac_show)

        if menu.isEmpty():
            return
        menu.exec_(QCursor.pos())

    def on_choose_columns(self):
        """Show the dialog for choosing which columns to show."""
        dlg = ColumnSelDlg(self.ctx, self)
        if dlg.exec_() == QDialog.Accepted:
            dlg.apply_changes()

    def _load_current_filter(self, section: int):
        # Get the current filter.
        current_filter = self.qt_model.filters
        current_filter_fld = self.qt_model.column_fields[section].name

        search_line = self.search_line
        filtered_sections = self.filtered_sections

        class Visitor(FilterVisitor):
            def visit_field(self, filter: FieldFilter):
                if filter.fld == current_filter_fld and filter.op == "ilike":
                    value = filter.vl
                    if isinstance(value, str):
                        if value.startswith("%") and value.endswith("%"):
                            value = value[1:-1]
                        assert search_line is not None
                        search_line.setText(value)
                        filtered_sections.add(section)

        Visitor(current_filter).run(current_filter)

    def prepare_search_line(self, section: int):
        if self.search_line is None:
            return

        # Replace the default placeholder text with the header text.
        model = self.model()
        assert model is not None
        self.search_line.setPlaceholderText(
            model.headerData(section, Qt.Orientation.Horizontal)
        )

        # Load the current filter.
        self._load_current_filter(section)

    def show_search_line(self, section: int):
        """Show the search line for the given section.

        Args:
            section: The 0-based index of the section to show the search line
            for.
        """
        # Get rid of previous search line.
        self.hide_search_line()

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
        self.search_line.raise_()

        self.prepare_search_line(section)

        # Place just above the header
        x = self.sectionPosition(section) + 1
        w = self.sectionSize(section)
        y = 2
        h = self.height() + 1
        header_rect = QRect(x, y, w, h)

        # Adjust for the horizontal scroll of the treeview.
        h_scroll = self.treeview.horizontalScrollBar()
        assert h_scroll is not None
        scroll_offset = h_scroll.value()
        header_rect.moveLeft(x - scroll_offset)

        # Place the search line at the correct position.
        pos = parent.mapToGlobal(header_rect.topLeft())
        parent_pos = parent.mapFromGlobal(pos)
        self.search_line.move(
            parent_pos.x(),
            max(0, parent_pos.y() - self.search_line.height() + 1),
        )

        # Connect the signals.
        self.search_line.hide_and_apply_search.connect(
            lambda text, exact: self.hide_search_line_and_apply(
                section, text, exact
            )
        )
        self.search_line.hide_and_cancel_search.connect(
            lambda: self.hide_search_line()
        )

        # Show the search line and set focus. Sometimes the search line is
        # hidden for some reason after the show() cal (BUG?).
        self.search_line.show()
        if self.search_line is not None:
            self.search_line.setFocus()

    def hide_search_line(self):
        """Hide the search line if we have one."""
        if self.search_line is not None:
            try:
                self.search_line.hide()
                self.search_line.deleteLater()
                self.search_line = None
            except Exception:
                pass

    def hide_and_cancel_search(self):
        """Hide the search line and cancel the search."""
        self.hide_search_line()

    def hide_search_line_and_apply(self, section: int, text: str, exact: bool):
        """Hide the search line and apply the filter.

        Args:
            section: The 0-based index of the section to apply the filter to.
            text: The text to filter the data by.
            exact: Whether the filter should be an exact match.
        """
        self.apply_filter(section, text, exact)
        self.hide_search_line()

    def _apply_filter(self, section: int, text: str, exact: bool):
        self.qt_model.apply_filter(
            insert_quick_search(
                self.qt_model.column_fields[section].name,
                text,
                self.qt_model.filters,
                exact,
            )
        )  # type: ignore

    def apply_filter(self, section: int, text: str, exact: bool):
        """Apply a filter to the data.

        Args:
            section: The 0-based index of the section to apply the filter to.
            text: The text to filter the data by.
            exact: Whether the filter should be an exact match.
        """
        text = text.strip()
        if text:
            self.filtered_sections.add(section)
        else:
            self.filtered_sections.discard(section)

        assert self.search_line is not None
        if text == self.search_line.initial_text:
            return

        try:
            self._apply_filter(section, text, exact)
        except Exception as e:
            self.ctx.show_error(
                title=self.t("cmn.error", "Error"),
                message=self.t(
                    "cmn.error.bad_filter",
                    "Invalid filter: {error}",
                    error=str(e),
                ),
            )
        self.search_line.initial_text = text

    def paintSection(
        self,
        painter: Optional[QPainter],
        rect: QRect,
        logicalIndex: int,
    ):
        """Paint the section with a filter icon if it is filtered."""
        assert painter is not None
        painter.save()

        model = self.model()
        assert model is not None

        # 1. Draw the background (use QStyle to respect themes)
        opt = QStyleOptionHeader()
        self.initStyleOption(opt)
        opt.rect = rect
        opt.section = logicalIndex
        opt.state = cast(
            QStyle.StateFlag, opt.state | QStyle.StateFlag.State_Raised
        )
        if (
            self.isSortIndicatorShown()
            and self.sortIndicatorSection() == logicalIndex
        ):
            opt.sortIndicator = (
                QStyleOptionHeader.SortDown
                if self.sortIndicatorOrder() == Qt.SortOrder.DescendingOrder
                else QStyleOptionHeader.SortUp
            )
        else:
            opt.sortIndicator = QStyleOptionHeader.SortIndicator.None_

        style = self.style()
        assert style is not None
        # style.drawControl(QStyle.ControlElement.CE_Header, opt, painter, self)

        # 2. Draw header text (shrink rect if you want icon space)
        text = model.headerData(
            logicalIndex, self.orientation(), Qt.ItemDataRole.DisplayRole
        )
        if text is None:
            text = ""
        text = str(text)

        icon = None
        icon_rect = QRect()
        icon_size = min(rect.height(), rect.width()) // 2
        icon_margin = 4

        # If filtered, draw icon at right
        if logicalIndex in self.filtered_sections:
            icon = self.get_icon("filter")
            if not icon.isNull():
                icon_rect = QRect(
                    rect.right() - icon_size - icon_margin,
                    rect.top() + (rect.height() - icon_size) // 2,
                    icon_size,
                    icon_size,
                )
                # Adjust text rect to not overlap icon
                text_rect = QRect(rect)
                text_rect.setRight(icon_rect.left() - icon_margin)
            else:
                text_rect = rect
        else:
            text_rect = rect

        # Draw the text, vertically and horizontally centered
        painter.setPen(QPen(self.palette().color(self.foregroundRole())))
        painter.drawText(
            text_rect,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignCenter,
            text,
        )

        # 3. Draw the filter icon (if any)
        if icon and not icon.isNull():
            icon.paint(painter, icon_rect, Qt.AlignmentFlag.AlignCenter)

        # 4. Draw sort indicator if needed (use QStyle!)
        if (
            self.isSortIndicatorShown()
            and self.sortIndicatorSection() == logicalIndex
        ):
            sort_rect = style.subElementRect(
                QStyle.SubElement.SE_HeaderArrow, opt, self
            )
            prev_rect = opt.rect
            opt.rect = sort_rect
            style.drawPrimitive(
                QStyle.PrimitiveElement.PE_IndicatorHeaderArrow,
                opt,
                painter,
                self,
            )
            opt.rect = prev_rect

        painter.restore()
