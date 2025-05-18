from typing import TYPE_CHECKING, Callable, Generic, Optional, TypeVar

from PyQt5.QtWidgets import QAction, QLineEdit, QWidget

from exdrf_qt.context_use import QtUseContext

# QIcon was imported but not used directly, assuming get_icon handles it.
# If QIcon is directly needed later, it can be re-added.


if TYPE_CHECKING:
    from exdrf_qt.context import QtContext

from PyQt5.QtCore import QTimer

DBM = TypeVar("DBM")


class SearchLine(QLineEdit, QtUseContext, Generic[DBM]):
    """A text line that is used to search a model."""

    _search_timer: Optional[QTimer]
    _callback: Callable[[str, bool], None]
    _exact_search_enabled: bool
    ac_exact: QAction

    def __init__(
        self,
        ctx: "QtContext",
        callback: Callable[[str, bool], None],
        parent: Optional["QWidget"] = None,
    ):
        super().__init__(parent)
        self.ctx = ctx
        self._search_timer = None
        self._callback = callback
        self._exact_search_enabled = False

        label = self.t("cmn.search.term", "Enter search term")
        self.setPlaceholderText(label)
        self.setToolTip(label)
        self.setWhatsThis(label)
        self.setClearButtonEnabled(True)
        self.textChanged.connect(self.on_search_term_changed)

        # Exact search action
        self.ac_exact = QAction(self)
        self._update_exact_search_action_visuals()
        self.ac_exact.setCheckable(True)
        self.ac_exact.toggled.connect(self._on_toggle_exact_search)
        self.addAction(self.ac_exact, QLineEdit.ActionPosition.LeadingPosition)

    def _update_exact_search_action_visuals(self) -> None:
        """Updates the icon and tooltip of the exact search action."""
        if self._exact_search_enabled:
            self.ac_exact.setIcon(self.get_icon("asterisk_orange"))
            self.ac_exact.setToolTip(
                self.t("cmn.search.exact_on", "Exact match is ON")
            )
        else:
            self.ac_exact.setIcon(
                self.get_icon("token_match_character_literally")
            )
            tooltip_text = self.t(
                "cmn.search.exact_off", "Exact match is OFF (wildcards enabled)"
            )
            self.ac_exact.setToolTip(tooltip_text)

    def _on_toggle_exact_search(self, checked: bool) -> None:
        """Handles the toggling of the exact search action."""
        self._exact_search_enabled = checked
        self._update_exact_search_action_visuals()
        # Re-trigger search with the new exact state
        self.on_search_term_changed(self.text())

    def on_search_term_changed(self, term: str) -> None:
        """Set the search term in the line edit.

        The function will wait for 500 ms after the user stops typing before
        applying the search term. This is to avoid applying the search term too
        frequently and to improve performance.
        """
        if term == "":
            # Be quick when the user clears the search term.
            self._callback("", self._exact_search_enabled)
            return

        if self._search_timer is None:
            self._search_timer = QTimer(self)
            self._search_timer.setSingleShot(True)
            self._search_timer.setInterval(500)
        else:
            self._search_timer.stop()
            # ensure previous connection is removed
            self._search_timer.disconnect()

        # Connect with current exact state
        def do_callback():
            self._callback(term, self._exact_search_enabled)

        self._search_timer.timeout.connect(do_callback)
        self._search_timer.start()
