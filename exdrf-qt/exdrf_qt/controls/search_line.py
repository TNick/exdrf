from typing import TYPE_CHECKING, Callable, Generic, Optional, TypeVar

from PyQt5.QtCore import QEvent, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFocusEvent, QKeyEvent, QMouseEvent
from PyQt5.QtWidgets import QAction, QLineEdit, QWidget

from exdrf_qt.context_use import QtUseContext

# QIcon was imported but not used directly, assuming get_icon handles it.
# If QIcon is directly needed later, it can be re-added.


if TYPE_CHECKING:
    from exdrf_qt.context import QtContext


DBM = TypeVar("DBM")


class SearchLine(QLineEdit, QtUseContext, Generic[DBM]):
    """A text line that is used to search a model.

    Attributes:
        initial_text: The initial text of the search line.
        _search_timer: The timer that is used to delay the search.
        _callback: The callback that is called when the search term changes.
        _exact_search_enabled: Whether exact search is enabled.
        ac_exact: The action that is used to toggle exact search.
        permanent: Whether the search line is permanent. This class simply
            provides storage for this property. The parent can use it to
            only show the search line when the mouse hovers over the header,
            for example. The property changes to True when the user starts
            typing or when the user clicks on the search line.

    Signals:
        hide_and_apply_search: Signal to indicate search should be applied and
            the line hidden.
        hide_and_cancel_search: Signal to indicate search should be cancelled
            and the line hidden.
    """

    # Signal to indicate search should be applied and the line hidden
    # Arguments: search_text (str), is_exact_match (bool)
    hide_and_apply_search = pyqtSignal(str, bool)

    # Signal to indicate search should be cancelled and the line hidden
    hide_and_cancel_search = pyqtSignal()

    _search_timer: Optional[QTimer]
    _callback: Callable[[str, bool], None]
    _exact_search_enabled: bool
    ac_exact: QAction
    initial_text: str
    permanent: bool

    def __init__(
        self,
        ctx: "QtContext",
        callback: Callable[[str, bool], None],
        parent: Optional["QWidget"] = None,
    ):
        super().__init__(parent)
        self.permanent = False
        self.ctx = ctx
        self.initial_text = ""
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
            self.ac_exact.setIcon(
                self.get_icon("token_match_character_literally")
            )
            self.ac_exact.setToolTip(
                self.t("cmn.search.exact_on", "Exact match is ON")
            )
        else:
            self.ac_exact.setIcon(self.get_icon("asterisk_orange"))
            self.ac_exact.setToolTip(
                self.t(
                    "cmn.search.exact_off",
                    "Exact match is OFF (wildcards enabled)",
                )
            )

    def _on_toggle_exact_search(self, checked: bool) -> None:
        """Handles the toggling of the exact search action."""
        self._exact_search_enabled = checked
        self._update_exact_search_action_visuals()
        # Re-trigger search with the new exact state (for live updates if text
        # exists).
        self.on_search_term_changed(self.text())

    def on_search_term_changed(self, term: str) -> None:
        """Set the search term in the line edit for live timed updates.

        The function will wait for 500 ms after the user stops typing before
        applying the search term via the callback.
        """
        if self._search_timer is None:
            self._search_timer = QTimer(self)
            self._search_timer.setSingleShot(True)
            self._search_timer.setInterval(500)  # 500ms delay

        self._search_timer.stop()  # Stop any existing timer

        # If term is empty, apply immediately via callback, don't wait for timer
        if not term:
            self._callback("", self._exact_search_enabled)
            return

        # Disconnect previous timeout connection to avoid multiple calls with
        # stale state
        try:
            self._search_timer.timeout.disconnect()
        except TypeError:  # Thrown if no connections exist
            pass

        # Connect with current exact state for the timed callback
        # Using a lambda here to capture current state of term and
        # exact_search_enabled for when the timer fires.
        self._search_timer.timeout.connect(
            lambda: self._callback(self.text(), self._exact_search_enabled)
        )
        self._search_timer.start()

    def leaveEvent(self, e: Optional[QEvent]) -> None:  # type: ignore
        """Handle mouse leaving the header widget.

        This ensures we hide the search line when mouse moves outside the
        header, since mouseMoveEvent won't fire once outside the widget bounds.
        """
        if (
            not self.rect().contains(self.mapFromGlobal(self.cursor().pos()))
            and not self.permanent
        ):
            self.hide_and_cancel_search.emit()
        super().leaveEvent(e)

    def mousePressEvent(self, e: Optional[QMouseEvent]) -> None:  # type: ignore
        """Handle mouse press events."""
        self.permanent = True
        if e:  # Ensure e is not None before calling super
            super().mousePressEvent(e)

    def keyPressEvent(self, e: Optional[QKeyEvent]) -> None:  # type: ignore
        """Handle key press events."""
        self.permanent = True
        if e and e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            new_text = self.text()
            if new_text != self.initial_text:
                # On Enter, finalize search and request to be hidden
                self.hide_and_apply_search.emit(
                    new_text, self._exact_search_enabled
                )
            e.accept()
        elif e and e.key() == Qt.Key.Key_Escape:
            self.hide_and_cancel_search.emit()
        elif e:  # Ensure e is not None before calling super
            super().keyPressEvent(e)

    def focusOutEvent(  # type: ignore
        self,
        event: Optional[QFocusEvent],
    ) -> None:
        """Handle focus out event."""
        new_text = self.text()
        if new_text != self.initial_text:
            # When focus is lost, finalize search and request to be hidden
            self.hide_and_apply_search.emit(
                new_text, self._exact_search_enabled
            )
        # Call super with the event, whether it's None or a QFocusEvent object
        super().focusOutEvent(event)

    def setText(self, text: str) -> None:  # type: ignore
        """Set the text of the search line.

        We keep track of the initial text that was set. If the text does not
        change, we do not emit the search signal.
        """
        super().setText(text)
        self.initial_text = text
