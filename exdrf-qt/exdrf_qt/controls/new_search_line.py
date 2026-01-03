import logging
from typing import TYPE_CHECKING, Optional

from PyQt5.QtCore import QTimer, pyqtSignal
from PyQt5.QtWidgets import QAction, QLineEdit, QWidget

from exdrf_qt.context_use import QtUseContext

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext

logger = logging.getLogger(__name__)


class SearchLine(QLineEdit, QtUseContext):
    """A text line that is used to search a model.

    Do not connect to the `textChanged` signal. Use the `searchTermChanged`
    signal instead as it debounces the search term changes.

    Attributes:
        ctx: The context.
        delay: The delay in milliseconds before the search term is applied.

    Signals:
        searchTermChanged: Emitted when the search term changes.
        addButtonClicked: Emitted when the add button is clicked.
    """

    _search_timer: Optional[QTimer]
    _add_action: Optional[QAction]

    searchTermChanged = pyqtSignal(str)
    addButtonClicked = pyqtSignal(str)

    def __init__(
        self,
        ctx: "QtContext",
        parent: Optional[QWidget] = None,
        delay: int = 500,
        add_button: bool = False,
    ):
        logger.log(
            10,
            "SearchLine.__init__(delay=%s)",
            delay,
        )
        super().__init__(parent)
        self.ctx = ctx
        self.delay = delay
        self._search_timer = None

        if add_button:
            self.create_add_action()
        else:
            self._add_action = None
        label = self.t("cmn.search.term", "Enter search term")
        self.setPlaceholderText(label)
        self.setToolTip(label)
        self.setWhatsThis(label)
        self.setClearButtonEnabled(True)

        self.textChanged.connect(self.on_search_term_changed)

    def create_add_action(self):
        """Creates the add action button and adds it to the line edit."""
        self._add_action = QAction(
            self.get_icon("plus"), self.t("cmn.create", "Create"), self
        )
        self._add_action.triggered.connect(
            lambda: self.addButtonClicked.emit(self.text())
        )
        self.addAction(
            self._add_action, QLineEdit.ActionPosition.TrailingPosition
        )

    def on_search_term_changed(self, term: str) -> None:
        """Set the search term in the line edit for live timed updates.

        The function will wait for 500 ms after the user stops typing before
        applying the search term via the callback.
        """
        logger.log(1, "SearchLine on_search_term_changed(%s)", term)

        if self._add_action is not None:
            self._add_action.setVisible(len(term) > 0)

        if self.delay <= 0:
            if self._search_timer is not None:
                self._search_timer.stop()
                self._search_timer.timeout.disconnect()
                self._search_timer.deleteLater()
                self._search_timer = None

            logger.log(1, "SearchLine on_search_term_changed: no delay")
            self.trigger_callback()
            return

        if self._search_timer is None:
            self._search_timer = QTimer(self)
            self._search_timer.setSingleShot(True)
            self._search_timer.setInterval(self.delay)
            logger.log(1, "SearchLine _search_timer created")

        self._search_timer.stop()  # Stop any existing timer

        # If term is empty, apply immediately via callback, don't wait for timer
        if not term:
            logger.log(1, "SearchLine on_search_term_changed: empty term")
            self.trigger_callback()
            return

        # Disconnect previous timeout connection to avoid multiple calls with
        # stale state
        try:
            self._search_timer.timeout.disconnect()
        except TypeError:  # Thrown if no connections exist
            logger.log(1, "SearchLine on_search_term_changed: no connections")

        # Connect with current exact state for the timed callback
        # Using a lambda here to capture current state of term and
        # exact_search_enabled for when the timer fires.
        self._search_timer.timeout.connect(lambda: self.trigger_callback())
        self._search_timer.start()
        logger.log(1, "SearchLine delayed callback started")

    def trigger_callback(self) -> None:
        """Trigger the callback."""
        logger.log(1, "SearchLine trigger_callback")
        try:
            self.searchTermChanged.emit(self.text())
        except Exception as e:
            logger.warning("Search callback failed", exc_info=e)
            self.ctx.show_error(
                title=self.t("cmn.error", "Error"),
                message=self.t(
                    "cmn.error.search_callback_failed",
                    "Search failed: {error}",
                    error=str(e),
                ),
            )
