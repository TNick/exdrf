from typing import TYPE_CHECKING, Optional

from PyQt5.QtCore import QTimer, pyqtSignal
from PyQt5.QtWidgets import QLineEdit

from exdrf_qt.context_use import QtUseContext

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QAction, QWidget  # noqa: F401

    from exdrf_qt.context import QtContext  # noqa: F401

# Delay in milliseconds before the search is triggered after typing stops.
TYPING_DELAY = 500


class SearchLine(QLineEdit, QtUseContext):
    """A search line."""

    ac_settings: "QAction"
    timer: Optional[QTimer] = None

    searchChanged = pyqtSignal(str, set)

    def __init__(self, ctx: "QtContext", parent: Optional["QWidget"] = None):
        super().__init__(parent)
        self.ctx = ctx
        self.setPlaceholderText(self.t("ex.common.search", "Search..."))

        # Action for choosing the fields to search.
        self.ac_settings = self.addAction(  # type: ignore[assignment]
            self.get_icon("wrench"),
            QLineEdit.LeadingPosition,
        )
        self.ac_settings.triggered.connect(self.on_show_config)

        # Typing triggers a timer.
        self.textChanged.connect(self.on_text_changed)

        # Connect our signal to the model.
        # self.searchChanged.connect(self.model.apply_simple_search)

    def on_show_config(self):
        """Show the search configuration dialog."""

    def cancel_timer(self):
        """Cancel the internal timer if it exists."""
        if self.timer is None:
            return
        self.timer.stop()
        self.timer.deleteLater()
        self.timer = None

    def on_text_changed(self):
        """Handle the text change by scheduling an event in some time.

        The previous event, if any, is canceled.
        """
        # Get rid of the timer if it exists.
        self.cancel_timer()

        # Create a single-shot timer
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._emit_search)
        self.timer.start(TYPING_DELAY)

    def _emit_search(self):
        """Emit the searchChanged signal."""
        self.searchChanged.emit(self.text(), self.field_selection)
