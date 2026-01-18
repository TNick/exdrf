import logging
from contextlib import contextmanager
from typing import TYPE_CHECKING, Generic, Optional, Set, TypeVar, Union, cast

from exdrf.filter import FieldFilter, FilterVisitor, insert_quick_search
from PyQt5.QtCore import QPoint, QRect, Qt
from PyQt5.QtGui import QPainter, QPen
from PyQt5.QtWidgets import (
    QAction,
    QDialog,
    QHeaderView,
    QMenu,
    QStyle,
    QStyleOptionHeader,
    QTreeView,
)

from exdrf_qt.context_use import QtUseContext
from exdrf_qt.controls.column_sel.column_sel import ColumnSelDlg
from exdrf_qt.controls.search_lines.base import (
    BasicSearchLine,
    SearchData,
)
from exdrf_qt.models import QtModel

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401

DBM = TypeVar("DBM")
logger = logging.getLogger(__name__)


class ListDbHeader(QHeaderView, QtUseContext, Generic[DBM]):
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
    search_line: Optional[BasicSearchLine]
    search_section: Optional[int]
    filtered_sections: Set[int]
    save_settings: bool
    _no_stg_write: bool
    qt_model: "QtModel[DBM]"

    def __init__(
        self,
        parent: "QTreeView",
        ctx: "QtContext",
        qt_model: "QtModel[DBM]",
        save_settings: bool = True,
    ):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self._no_stg_write = True
        self.save_settings = save_settings
        self.ctx = ctx
        self.search_line = None
        self.qt_model = qt_model
        self.search_section = None
        self.filtered_sections = set()
        self.setMouseTracking(True)
        self.setSectionsMovable(True)
        self.setFirstSectionMovable(True)
        if save_settings:
            self.sectionMoved.connect(self.on_section_moved)
            self.sectionResized.connect(self.on_section_resized)
            self.geometriesChanged.connect(self.on_geometries_changed)
            self.sectionCountChanged.connect(self.on_section_count_changed)
            self.sectionClicked.connect(self.on_section_clicked)
            self.sectionDoubleClicked.connect(self.on_section_double_clicked)
            self.sectionEntered.connect(self.on_section_entered)
            self.sectionHandleDoubleClicked.connect(
                self.on_section_handle_double_clicked
            )
            self.sectionPressed.connect(self.on_section_pressed)
            self.sortIndicatorChanged.connect(self.on_sort_indicator_changed)
        self._no_stg_write = False

    @contextmanager
    def no_stg_write(self):
        if self._no_stg_write:
            yield True
            return

        self._no_stg_write = True
        try:
            yield False
        finally:
            self._no_stg_write = False

    def on_geometries_changed(self):
        logger.log(1, "geometriesChanged")
        self.setFirstSectionMovable(True)

    def on_section_moved(
        self, logical_index: int, old_visual_index: int, new_visual_index: int
    ):
        logger.debug(
            "sectionMoved: %s, %s, %s",
            logical_index,
            old_visual_index,
            new_visual_index,
        )
        self.hide_search_line()
        with self.no_stg_write() as write_blocked:
            if not write_blocked:
                for i in range(self.count()):
                    key = self.stg_key_name(i, "vi")
                    self.ctx.stg.set_setting(key, self.visualIndex(i))

    def on_section_resized(
        self, logical_index: int, old_size: int, new_size: int
    ):
        logger.log(
            1, "sectionResized: %s, %s, %s", logical_index, old_size, new_size
        )
        if new_size < 1:
            return
        with self.no_stg_write() as write_blocked:
            if not write_blocked:
                key = self.stg_key_name(logical_index, "size")
                self.ctx.stg.set_setting(key, new_size)

    def on_section_count_changed(self, old_count: int, new_count: int):
        logger.log(1, "sectionCountChanged: %s, %s", old_count, new_count)

    def on_section_clicked(self, logical_index: int):
        logger.log(1, "sectionClicked: %s", logical_index)

    def on_section_double_clicked(self, logical_index: int):
        logger.log(1, "sectionDoubleClicked: %s", logical_index)
        self.show_search_line(logical_index)

    def on_section_entered(self, logical_index: int):
        logger.log(1, "sectionEntered: %s", logical_index)

    def on_section_handle_double_clicked(self, logical_index: int):
        logger.log(1, "sectionHandleDoubleClicked: %s", logical_index)

    def on_section_pressed(self, logical_index: int):
        logger.log(1, "sectionPressed: %s", logical_index)

    def on_sort_indicator_changed(
        self, logical_index: int, order: Qt.SortOrder
    ):
        logger.debug("sortIndicatorChanged: %s, %s", logical_index, order)

    @property
    def treeview(self) -> "QTreeView":
        """The tree view that is used to present the data in the list.

        We assume that the parent is a tree-view,
        """
        parent = self.parent()
        assert isinstance(parent, QTreeView), "Parent should be a QTreeView"
        return parent

    def create_sort_actions(self, section: int):
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

    def create_filter_action(self, section: int):
        ac_filter = QAction(
            self.get_icon("filter"),
            self.t("cmn.filter.title", "Filter..."),
            self,
        )
        ac_filter.triggered.connect(lambda: self.show_search_line(section))
        return ac_filter

    def create_show_columns_action(self, section: int) -> Union[QAction, None]:
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

        ac_sort_asc, ac_sort_desc = self.create_sort_actions(section)

        # Filter
        ac_filter = self.create_filter_action(section)

        # Choose column visibility.
        ac_show = self.create_show_columns_action(section)

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

        # Get the visual rect of the section under the cursor
        x = self.sectionPosition(section)
        w = self.sectionSize(section)
        menu_size = menu.sizeHint()

        # Calculate the center of the section
        section_center_x = x + w / 2
        section_bottom_y = self.height()
        section_center_local = QPoint(int(section_center_x), section_bottom_y)
        section_center_global = self.mapToGlobal(section_center_local)

        # Align the menu such that its center matches the section's center
        menu_pos = section_center_global
        menu_pos.setX(int(section_center_global.x() - menu_size.width() / 2))
        menu.exec_(menu_pos)

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
                if filter.fld == current_filter_fld and filter.op in (
                    "ilike",
                    "regex",
                    "eq",
                    "==",
                ):
                    value = filter.vl
                    if isinstance(value, str):
                        if value.startswith("%") and value.endswith("%"):
                            value = value[1:-1]
                        assert search_line is not None
                        search_line.change_search_term(value, emit=False)
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
        self.search_line = BasicSearchLine(
            ctx=self.ctx,
            parent=parent,
            delay=1000,
        )
        assert self.search_line is not None
        self.search_line.setFixedWidth(self.sectionSize(section))
        self.search_line.setFixedHeight(self.height() + 1)
        self.search_line.raise_()
        self.search_line.searchDataChanged.connect(
            lambda search_data: self.apply_filter(section, search_data)
        )
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
        self.search_line.returnPressed.connect(
            lambda: self.hide_search_line_and_apply(section)
        )
        self.search_line.escapePressed.connect(lambda: self.hide_search_line())

        # Show the search line and set focus. Sometimes the search line is
        # hidden for some reason after the show() cal (BUG?).
        self.search_line.show()
        if self.search_line is not None:
            self.search_line.setFocus()

    def hide_search_line(self):
        """Hide the search line if we have one."""
        if self.search_line is not None:
            try:
                self.search_line.stop_timer()
                self.search_line.hide()
                self.search_line.deleteLater()
                self.search_line = None
            except Exception:
                pass

    def hide_search_line_and_apply(self, section: int):
        """Hide the search line and apply the filter.

        Args:
            section: The 0-based index of the section to apply the filter to.
            data: The search data to apply the filter to.
        """
        if self.search_line is None:
            return
        data = self.search_line.search_data
        self.hide_search_line()
        self.apply_filter(section, data)

    def _apply_filter(self, section: int, data: "SearchData"):
        self.qt_model.apply_filter(
            insert_quick_search(
                self.qt_model.column_fields[section].name,
                data.term,
                self.qt_model.filters,
                search_type=data.search_type,
            )
        )  # type: ignore

    def apply_filter(self, section: int, data: "SearchData"):
        """Apply a filter to the data.

        Args:
            section: The 0-based index of the section to apply the filter to.
            text: The text to filter the data by.
            exact: Whether the filter should be an exact match.
        """
        text = data.term.strip()
        if text:
            self.filtered_sections.add(section)
        else:
            self.filtered_sections.discard(section)

        try:
            self._apply_filter(
                section,
                SearchData(
                    term=text,
                    search_type=data.search_type,
                ),
            )
        except Exception as e:
            self.ctx.show_error(
                title=self.t("cmn.error", "Error"),
                message=self.t(
                    "cmn.error.bad_filter",
                    "Invalid filter: {error}",
                    error=str(e),
                ),
            )
            logger.exception("Error in ListDbHeader.apply_filter: bad filter")

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

    def read_sections_layout(self) -> dict[str, dict[str, int]]:
        """Read the sections layout from the settings."""
        qt_model = self.qt_model

        # Go through all sections and save their current visual index and size.
        settings = {}
        for i in range(self.count()):
            # Get the name of this field.
            field_name = qt_model.column_fields[i].name

            # Get the current visual index and size.
            visual_index = self.visualIndex(i)

            # Get the current size.
            size = self.sectionSize(i)

            # Save the current visual index and size.
            hidden = self.isSectionHidden(i)
            settings[field_name] = {
                "vi": visual_index,  # Will be updated by the incoming settings.
                "crt-vi": visual_index,
                "li": i,
                "size": size,
                "crt-size": size,
                "hidden": hidden,  # Will be updated by the incoming settings.
                "crt-hidden": hidden,
            }

        return settings

    def stg_key_name(self, field_li: int, key: str) -> str:
        # Underlying model.
        qt_model = self.qt_model

        # Common prefix for this model.
        prefix = qt_model.__module__ + "." + qt_model.__class__.__name__

        # Get the name of this field.
        field_name = qt_model.column_fields[field_li].name
        return f"{prefix}.{field_name}.{key}"

    def apply_sections_layout(
        self,
        sections_layout: dict[str, dict[str, int]],
        save_to_settings: bool = False,
    ):
        qt_model = self.qt_model
        prefix = qt_model.__module__ + "." + qt_model.__class__.__name__
        self._no_stg_write = True

        self.setUpdatesEnabled(False)
        try:
            # Step 1: Show all sections to make sure movement is possible
            for f_values in sections_layout.values():
                self.showSection(f_values["li"])

            # Step 2: Reorder sections based on saved visual indices
            for f_name in sorted(
                sections_layout.keys(), key=lambda x: sections_layout[x]["vi"]
            ):
                f_values = sections_layout[f_name]
                logical_index = f_values["li"]
                current_visual = self.visualIndex(logical_index)
                target_visual = f_values["vi"]
                if current_visual != target_visual:
                    self.moveSection(current_visual, target_visual)

            # Step 3: Apply visibility and resize
            for f_name, f_values in sections_layout.items():
                logical_index = f_values["li"]

                size = f_values["size"]
                if size == 0:
                    size = self.ctx.stg.get_setting(f"{prefix}.{f_name}.size")
                    if size == 0:
                        size = 20
                self.resizeSection(logical_index, size)
                if f_values["hidden"]:
                    self.hideSection(logical_index)

                if save_to_settings:
                    logger.debug(f"saving {f_name}.vi = {f_values['vi']}")
                    self.ctx.stg.set_setting(
                        f"{prefix}.{f_name}.vi", f_values["vi"]
                    )

                    size = max(size, 20)
                    logger.debug(f"saving {f_name}.size = {size}")
                    self.ctx.stg.set_setting(f"{prefix}.{f_name}.size", size)

                    logger.debug(
                        f"saving {f_name}.hidden = {f_values['hidden']}"
                    )
                    self.ctx.stg.set_setting(
                        f"{prefix}.{f_name}.hidden", f_values["hidden"]
                    )

        finally:
            self.setUpdatesEnabled(True)
            self._no_stg_write = False

    def load_sections_from_settings(self):
        """Load the visible sections and their length from the settings."""
        qt_model = self.qt_model
        prefix = qt_model.__module__ + "." + qt_model.__class__.__name__

        # Read settings from the current layout.
        crt_settings = self.read_sections_layout()

        # Apply changes from the settings.
        for f_name, f_values in crt_settings.items():
            key = f"{prefix}.{f_name}"
            new_values = self.ctx.stg.get_setting(key)
            if new_values is not None:
                f_values["hidden"] = new_values.get(
                    "hidden", f_values["hidden"]
                )
                prev_size = f_values["size"]
                f_values["size"] = new_values.get("size", prev_size)
                if f_values["size"] < 1:
                    f_values["size"] = max(prev_size, 10)
                f_values["vi"] = new_values.get("vi", f_values["vi"])

        # Apply changes from the settings.
        self.apply_sections_layout(crt_settings)
