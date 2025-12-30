from __future__ import annotations

import logging
from typing import TYPE_CHECKING, List, cast

from PyQt5.QtCore import QAbstractProxyModel, QModelIndex, QPoint, Qt, QTimer
from PyQt5.QtWidgets import (
    QAction,
    QActionGroup,
    QCompleter,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QSpinBox,
    QWidget,
    QWidgetAction,
)

from exdrf_qt.context_use import QtUseContext
from exdrf_qt.controls.command_palette.constants import (
    MAX_LINE_EDIT_WIDTH,
    SearchLocation,
)
from exdrf_qt.controls.command_palette.engine import ComEngine

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401
    from exdrf_qt.menus import ActionDef  # noqa: F401


class CommandPalette(QLineEdit, QtUseContext):
    """A line edit that shows a list of commands.

    The list of commands is shown in the popup that becomes visible when
    the control gets the focus. Clicking on a command will execute it's
    callback.
    """

    engine: ComEngine

    m_settings: QMenu

    ac_case_sensitive: QAction
    ac_list_style: QAction
    ag_filter_mode: QActionGroup
    ac_starts_with: QAction
    ac_contains: QAction
    ac_ends_with: QAction
    ac_menu: QAction
    ac_show_dropdown: QAction
    ac_use_description: QAction
    ac_use_tags: QAction

    c_max_items: QSpinBox

    stg_key: str

    def __init__(
        self,
        ctx: "QtContext",
        parent: "QWidget",
        action_defs: "List[ActionDef]",
        stg_key: str = "command-palette",
        max_width: int = MAX_LINE_EDIT_WIDTH,
    ):
        super().__init__(parent)
        self.ctx = ctx
        self.stg_key = stg_key
        self._setup_engine()
        self._setup_settings()
        self._setup_drop_down()
        self.set_action_defs(action_defs)
        self.setMaximumWidth(max_width)

    def set_action_defs(self, action_defs: "List[ActionDef]") -> None:
        """Set the action definitions for the command palette."""
        self.engine.set_action_defs(action_defs)
        self.c_max_items.blockSignals(True)
        self.c_max_items.setRange(1, len(action_defs))
        self.c_max_items.blockSignals(False)
        crt_val = self.ctx.stg.get_setting(f"{self.stg_key}.max-items", 9)
        self.c_max_items.setValue(
            crt_val
            if 1 < crt_val < len(action_defs)
            else min(9, len(action_defs))
        )

    def _setup_engine(self) -> None:
        """Setup the completer."""
        self.engine = ComEngine(
            ctx=self.ctx,
            default_icon=self.get_icon("blueprint"),
            parent=self,
            stg_key=self.stg_key,
        )
        self.engine.activated[QModelIndex].connect(self.command_activated)
        self.setCompleter(self.engine)

    def _setup_filter_mode(self, menu: QMenu) -> None:
        """Setup the filter mode actions."""
        self.ag_filter_mode = QActionGroup(self)
        self.ag_filter_mode.setExclusive(True)

        crt_filter_mode = self.ctx.stg.get_setting(
            f"{self.stg_key}.filter-mode", Qt.MatchFlag.MatchContains
        )

        # Starts with
        self.ac_starts_with = QAction(
            self.t(
                "exdrf.command-palette.filter-mode.starts-with", "Starts with"
            ),
            self,
        )
        self.ac_starts_with.setCheckable(True)
        self.ac_starts_with.setChecked(
            crt_filter_mode == Qt.MatchFlag.MatchStartsWith
        )
        self.ac_starts_with.triggered.connect(
            lambda: self._on_filter_mode_changed(Qt.MatchFlag.MatchStartsWith)
        )
        self.ag_filter_mode.addAction(self.ac_starts_with)
        menu.addAction(self.ac_starts_with)

        # Contains
        self.ac_contains = QAction(
            self.t("exdrf.command-palette.filter-mode.contains", "Contains"),
            self,
        )
        self.ac_contains.setCheckable(True)
        self.ac_contains.setChecked(
            crt_filter_mode == Qt.MatchFlag.MatchContains
        )
        self.ac_contains.triggered.connect(
            lambda: self._on_filter_mode_changed(Qt.MatchFlag.MatchContains)
        )
        self.ag_filter_mode.addAction(self.ac_contains)
        menu.addAction(self.ac_contains)

        # Ends with
        self.ac_ends_with = QAction(
            self.t("exdrf.command-palette.filter-mode.ends-with", "Ends with"),
            self,
        )
        self.ac_ends_with.setCheckable(True)
        self.ac_ends_with.setChecked(
            crt_filter_mode == Qt.MatchFlag.MatchEndsWith
        )
        self.ac_ends_with.triggered.connect(
            lambda: self._on_filter_mode_changed(Qt.MatchFlag.MatchEndsWith)
        )
        self.ag_filter_mode.addAction(self.ac_ends_with)
        menu.addAction(self.ac_ends_with)

    def _setup_max_items(self, menu: QMenu) -> None:
        """Setup the max items spinbox."""
        max_items_widget = QWidget()

        max_items_layout = QHBoxLayout(max_items_widget)
        max_items_layout.setContentsMargins(11, 5, 11, 5)

        max_items_label = QLabel(
            self.t("exdrf.command-palette.max-items", "Max items:"),
            max_items_widget,
        )
        max_items_layout.addWidget(max_items_label)

        self.c_max_items = QSpinBox(max_items_widget)
        model = self.engine.model()
        model_row_count = model.rowCount() if model else 9
        self.c_max_items.setMinimum(1)
        self.c_max_items.setMaximum(model_row_count)
        self.c_max_items.setValue(self.engine.maxVisibleItems() or 9)
        self.c_max_items.valueChanged.connect(self._on_max_items_changed)
        max_items_layout.addWidget(self.c_max_items)

        max_items_action = QWidgetAction(self)
        max_items_action.setDefaultWidget(max_items_widget)
        menu.addAction(max_items_action)

    def _setup_case_sensitive(self, menu: QMenu) -> None:
        self.ac_case_sensitive = QAction(
            self.t("exdrf.command-palette.case-sensitive", "Case Sensitive"),
            self,
        )
        self.ac_case_sensitive.setCheckable(True)
        self.ac_case_sensitive.triggered.connect(
            self._on_case_sensitive_toggled
        )
        self.ac_case_sensitive.setChecked(
            self.ctx.stg.get_setting(f"{self.stg_key}.case-sensitive", False)
        )
        menu.addAction(self.ac_case_sensitive)

    def _setup_list_style(self, menu: QMenu) -> None:
        self.ac_list_style = QAction(
            self.t("exdrf.command-palette.filtered", "Filter as I type"), self
        )
        self.ac_list_style.setCheckable(True)
        self.ac_list_style.triggered.connect(self._on_completion_mode_changed)
        self.ac_list_style.setChecked(
            self.ctx.stg.get_setting(f"{self.stg_key}.completion-mode", False)
        )
        menu.addAction(self.ac_list_style)

    def _setup_search_location(self, menu: QMenu) -> None:
        """Setup the search location actions."""
        self.ac_use_description = QAction(
            self.t(
                "exdrf.command-palette.use-description", "Search in description"
            ),
            self,
        )
        self.ac_use_description.setCheckable(True)
        self.ac_use_description.setChecked(
            self.engine.completer_model.searches_in_description()
        )
        self.ac_use_description.triggered.connect(
            self._on_search_location_changed
        )
        menu.addAction(self.ac_use_description)

        self.ac_use_tags = QAction(
            self.t("exdrf.command-palette.use-tags", "Search in tags"), self
        )
        self.ac_use_tags.setCheckable(True)
        self.ac_use_tags.setChecked(
            self.engine.completer_model.searches_in_tags()
        )
        self.ac_use_tags.triggered.connect(self._on_search_location_changed)
        menu.addAction(self.ac_use_tags)

    def _setup_settings(self) -> None:
        """Setup menu action for line edit."""
        menu = QMenu(self)

        self._setup_search_location(menu)
        menu.addSeparator()

        self._setup_filter_mode(menu)
        menu.addSeparator()

        self._setup_max_items(menu)
        menu.addSeparator()

        self._setup_case_sensitive(menu)
        self._setup_list_style(menu)

        # Create action with menu
        ma = self.addAction(
            self.get_icon("wrench"), QLineEdit.ActionPosition.TrailingPosition
        )
        assert ma is not None
        self.ac_menu = ma
        self.ac_menu.setToolTip(
            self.t(
                "exdrf.command-palette.completer-options", "Completer options"
            )
        )
        self.ac_menu.setMenu(menu)
        self.ac_menu.triggered.connect(self._show_menu)
        self.m_settings = menu

        # Set initial filter mode
        self.engine.setFilterMode(Qt.MatchFlag.MatchContains)

    def _setup_drop_down(self) -> None:
        self.ac_show_dropdown = QAction(
            self.get_icon("bullet_arrow_down"),
            self.t("exdrf.command-palette.show-dropdown", "Show command list"),
            self,
        )
        self.ac_show_dropdown.triggered.connect(lambda: self.engine.complete())
        self.addAction(
            self.ac_show_dropdown, QLineEdit.ActionPosition.LeadingPosition
        )

    def command_activated(self, index: QModelIndex) -> None:
        """Insert the completion into the line edit."""
        if index is None or not index.isValid():
            logger.warning("Invalid index: %s", index)
            return

        popup = self.engine.popup()
        assert popup is not None
        popup_m = popup.model()
        assert popup_m is not None

        if isinstance(popup_m, QAbstractProxyModel):
            index = popup_m.mapToSource(index)

        row = index.row()
        action_def = self.engine.get_action_def(row)
        if action_def.callback is not None:
            QTimer.singleShot(10, lambda: self._command_activated(action_def))
        else:
            logger.warning("No callback for action def: %s", action_def)

    def _command_activated(self, action_def: "ActionDef") -> None:
        """Execute the action.

        Because we cannot clear the line edit right away we execute the
        command after a short delay and we clear the completer.
        """
        self.setText("")
        action_def.callback()

    # def focusInEvent(self, a0: "QFocusEvent | None") -> None:
    #     """Show completer when line edit receives focus."""
    #     super().focusInEvent(a0)
    #     if self.engine:
    #         self.engine.complete()

    def _on_filter_mode_changed(self, match_flag: Qt.MatchFlag) -> None:
        """Handle filter mode change."""
        self.ctx.stg.set_setting(f"{self.stg_key}.filter-mode", int(match_flag))
        self.engine.setFilterMode(match_flag)

    def _on_max_items_changed(self, value: int) -> None:
        """Handle max visible items change."""
        self.engine.setMaxVisibleItems(value)
        self.ctx.stg.set_setting(f"{self.stg_key}.max-items", value)

    def _on_case_sensitive_toggled(self, checked: bool) -> None:
        """Handle case sensitive toggle."""
        self.ctx.stg.set_setting(f"{self.stg_key}.case-sensitive", checked)
        self.engine.setCaseSensitivity(
            Qt.CaseSensitivity.CaseSensitive
            if checked
            else Qt.CaseSensitivity.CaseInsensitive
        )

    def _on_completion_mode_changed(self, checked: bool) -> None:
        """Handle completion mode change."""
        self.ctx.stg.set_setting(f"{self.stg_key}.completion-mode", checked)
        self.engine.setCompletionMode(
            QCompleter.CompletionMode.PopupCompletion
            if checked
            else QCompleter.CompletionMode.UnfilteredPopupCompletion
        )

    def _on_search_location_changed(self) -> None:
        """Handle search location change."""
        self.engine.set_search_location(
            cast(
                "SearchLocation",
                SearchLocation.TITLE
                | (
                    SearchLocation.DESCRIPTION
                    if self.ac_use_description.isChecked()
                    else 0
                )
                | (SearchLocation.TAGS if self.ac_use_tags.isChecked() else 0),
            )
        )

    def _show_menu(self) -> None:
        """Show the completer options menu."""

        # Hide completer popup if visible
        self.hide_completer()

        # Show menu with right side aligned to right side of line edit
        line_edit_right = self.mapToGlobal(self.rect().bottomRight())
        menu_size = self.m_settings.sizeHint()
        menu_pos = QPoint(
            line_edit_right.x() - menu_size.width(), line_edit_right.y()
        )
        self.m_settings.exec_(menu_pos)

    def hide_completer(self) -> None:
        popup = self.engine.popup()
        if popup and popup.isVisible():
            popup.hide()
