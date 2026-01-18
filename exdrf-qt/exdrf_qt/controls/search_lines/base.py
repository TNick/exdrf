import logging
from typing import TYPE_CHECKING, Callable, Optional, Union

from attrs import define
from exdrf.filter import SearchType
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtWidgets import QAction, QLineEdit, QMenu, QWidget

from exdrf_qt.context_use import QtUseContext
from exdrf_qt.utils.tlh import top_level_handler

if TYPE_CHECKING:
    from PyQt5.QtGui import QKeyEvent

    from exdrf_qt.context import QtContext

logger = logging.getLogger(__name__)

INSTANT_TRIGGER = 0
NEVER_TRIGGER = -1


@define(slots=True, kw_only=True)
class SearchData:
    term: str
    search_type: "SearchType"


class BasicSearchLine(QLineEdit, QtUseContext):
    """A general-purpose search line.

    Attributes:
        delay: The delay in milliseconds before the search term is applied.
            You can also use the constants INSTANT_TRIGGER (
            the signal is generated as soon as the user types) and NEVER_TRIGGER
            (the signal is never generated; you may want to use this with the
            enter_triggers option).
        timer_search: The timer that is used to delay the search.
        ac_clear: The action that is used to clear the search term.
        ac_settings: The action that is used to show the settings menu.
        ac_add: The action that is used to add a new item to the list.
        search_data: The data that is used to store the search term and
            search type.

    Signals:
        searchDataChanged: The signal that is emitted when the search data
            changes. Arguments: search_data (SearchData) includes the term and
            search type.
        returnPressed: The signal that is emitted when the user presses Enter.
        escapePressed: The signal that is emitted when the user presses Escape.
    """

    delay: int
    enter_triggers: bool
    timer_search: Optional[QTimer]
    add_callback: Optional[Callable[[], None]]

    ac_clear: Optional[QAction]
    ac_settings: Optional[QAction]
    ac_add: Optional[QAction]

    search_data: SearchData

    searchDataChanged = pyqtSignal(object)
    returnPressed = pyqtSignal()
    escapePressed = pyqtSignal()

    def __init__(
        self,
        ctx: "QtContext",
        parent: Optional["QWidget"] = None,
        clear_button: bool = True,
        settings_button: bool = True,
        add_button: Union[bool, Callable[[], None]] = False,
        search_data: Optional[SearchData] = None,
        delay: int = 1000,
        enter_triggers: Optional[bool] = None,
    ) -> None:
        """Initializes the search line.

        Args:
            ctx: The context.
            parent: The parent widget.
            clear_button: Whether to show the clear button. We're using a
                custom button, consistent with the rest of the UI.
            settings_button: Whether to show the settings button. If enabled,
                it shows a menu beneath the settings button with the search type
                options.
            add_button: Whether to show the add button. Defaults to False.
                If a callable is provided, it is called when the add button is
                clicked.
            search_data: The data structure that stores the current state of
                the search line. If None a new SearchData object is created
                with the SIMPLE search type and an empty term.
            delay: The delay in milliseconds before the search term is applied.
                You can also use the constants INSTANT_TRIGGER ( the signal is
                generated as soon as the user types) and NEVER_TRIGGER (the
                signal is never generated; you may want to use this with the
                enter_triggers option).
            enter_triggers: Whether to trigger the search term changed signal
                when the user presses Enter. If None, enter_triggers becomes
                True if delay is NEVER_TRIGGER and false otherwise.
        """
        if enter_triggers is None:
            enter_triggers = delay == NEVER_TRIGGER

        self.ctx = ctx
        self.delay = delay
        self.timer_search = None
        self.enter_triggers = enter_triggers
        self.add_callback = (
            add_button if not isinstance(add_button, bool) else None
        )
        super().__init__(parent)

        label = self.t("cmn.search.term", "Enter search term")
        self.setPlaceholderText(label)
        self.setToolTip(label)
        self.setWhatsThis(label)

        # We provide our own action for clearing the contents.
        super().setClearButtonEnabled(False)

        # Create the actions.
        self.ac_clear = self.create_clear_action() if clear_button else None
        self.ac_settings = (
            self.create_settings_action() if settings_button else None
        )
        self.ac_add = self.create_add_action() if add_button else None

        self.textChanged.connect(self.on_search_term_changed)

        # Initialize if data was provided.
        if search_data is not None:
            self.search_data = search_data
            if self.search_data.term:
                self.setText(self.search_data.term)
        else:
            self.search_data = SearchData(
                term="", search_type=SearchType.SIMPLE
            )

    def create_clear_action(self) -> QAction:
        """Creates an action that allows the user to clear the contents of the
        search line.
        """
        action = QAction(self)
        action.setIcon(self.get_icon("clear_to_null"))
        action.triggered.connect(self.clear)
        self.addAction(action, QLineEdit.ActionPosition.LeadingPosition)
        return action

    def create_settings_action(self) -> QAction:
        """Creates an action that allows the user to show the settings menu."""
        action = QAction(self)
        action.setIcon(self.get_icon("wrench"))
        action.triggered.connect(self.on_show_settings)
        self.addAction(action, QLineEdit.ActionPosition.TrailingPosition)
        return action

    def create_add_action(self) -> QAction:
        """Creates an action that allows the user to add a new item to the list."""
        action = QAction(self)
        action.setIcon(self.get_icon("plus"))
        action.triggered.connect(self.on_add)
        self.addAction(action, QLineEdit.ActionPosition.TrailingPosition)
        return action

    def stop_timer(self) -> None:
        """Stops the search timer."""
        if self.timer_search is not None:
            self.timer_search.stop()
            self.timer_search.timeout.disconnect()
            self.timer_search.deleteLater()
            self.timer_search = None

    def create_timer(self) -> "QTimer":
        """Creates the search timer."""
        if self.timer_search is None:
            assert (
                self.delay > 0
            ), f"Delay must be greater than 0, is {self.delay}"
            self.timer_search = QTimer(self)
            self.timer_search.setSingleShot(True)
            self.timer_search.setInterval(self.delay)
            logger.log(1, "timer created")
        return self.timer_search

    def change_search_term(self, term: str, emit: bool = True) -> None:
        """Changes the search term."""
        crt_text = self.text() or ""
        term = term or ""
        vrt_text = self.search_data.term or ""

        if vrt_text == term:
            # No change needed, except if vrt_text is not in sync with crt_text
            if crt_text != vrt_text:
                self.blockSignals(True)
                try:
                    super().setText(vrt_text)
                finally:
                    self.blockSignals(False)
            return

        # The values are different, update the search data and the text.
        self.blockSignals(True)
        try:
            self.search_data.term = term
            super().setText(term)
        finally:
            self.blockSignals(False)

        if emit:
            self.searchDataChanged.emit(self.search_data)

    def change_search_data(
        self, search_data: "SearchData", emit: bool = True
    ) -> None:
        """Changes the search data."""
        self.search_data = search_data
        crt_text = self.text()
        if not (
            self.search_data.term != crt_text
            and bool(self.search_data.term) != bool(crt_text)
        ):
            return

        self.blockSignals(True)
        try:
            super().setText(self.search_data.term)
        finally:
            self.blockSignals(False)

        if emit:
            self.searchDataChanged.emit(self.search_data)

    @top_level_handler
    def on_search_term_changed(self, term: str) -> None:
        """Called when the search term changes.

        The function will wait for some ms after the user stops typing before
        applying the search term via the callback if delay is greater than 0.
        """
        logger.log(1, "on_search_term_changed(%s)", term)

        # Only show the add new button if the term is not empty.
        if self.ac_add is not None:
            self.ac_add.setVisible(len(term) > 0)

        if self.delay <= 0:
            self.stop_timer()

            logger.log(1, "SearchLine on_search_term_changed: no delay")
            if self.delay == INSTANT_TRIGGER:
                self.trigger_callback(term)
            return

        # Make sure the timer exists and is stopped.
        timer = self.create_timer()
        timer.stop()

        # If term is empty, apply immediately via callback, don't wait for timer
        if not term:
            logger.log(1, "SearchLine on_search_term_changed: empty term")
            self.trigger_callback(term)
            return

        # Disconnect previous timeout connection to avoid multiple calls with
        # stale state
        try:
            timer.timeout.disconnect()
        except TypeError:  # Thrown if no connections exist
            logger.log(1, "SearchLine on_search_term_changed: no connections")

        # Connect with current exact state for the timed callback
        # Using a lambda here to capture current state of term and
        # exact_search_enabled for when the timer fires.
        timer.timeout.connect(lambda: self.trigger_callback(term))
        timer.start()
        logger.log(1, "SearchLine delayed callback started")

    def trigger_callback(self, term: str) -> None:
        """Trigger the callback."""
        logger.log(1, "SearchLine trigger_callback")
        self.search_data.term = term
        self.searchDataChanged.emit(self.search_data)

    @top_level_handler
    def on_show_settings(self) -> None:
        """Called when the user clicks the settings button."""
        from exdrf_qt.utils.search_actions import (
            apply_search_action,
            create_search_actions,
        )

        menu = QMenu(self)

        # Create the actions for the search type menu.
        ac_group_search = create_search_actions(
            self.ctx, self.search_data.search_type, parent=menu
        )
        if ac_group_search is None:
            return
        for action in ac_group_search.actions():
            menu.addAction(action)

        # Show the menu beneath the settings button.
        menu_pos = self.mapToGlobal(self.rect().bottomRight())
        menu_size = menu.sizeHint()
        menu_pos.setX(menu_pos.x() - menu_size.width())
        menu.exec_(menu_pos)

        # Apply changes to the search type.
        search_type = apply_search_action(ac_group_search)
        if search_type is not None:
            if search_type != self.search_data.search_type:
                self.search_data.search_type = search_type
                self.searchDataChanged.emit(self.search_data)

        menu.deleteLater()
        ac_group_search.deleteLater()

    def on_add(self) -> None:
        """Called when the user clicks the add button."""
        if self.add_callback is not None:
            self.add_callback()
        else:
            raise NotImplementedError(
                "on_add needs to be implemented in the subclass or "
                "add_callback must be set to a callable."
            )

    def isClearButtonEnabled(self) -> bool:
        """Returns whether the clear button is enabled.

        As we're using our own clear button, we need to override the default
        implementation.
        """
        return self.ac_clear is not None

    def setClearButtonEnabled(self, enable: bool) -> None:
        """Sets whether the clear button is enabled.

        As we're using our own clear button, we need to override the default
        implementation.
        """
        if enable:
            if self.ac_clear is None:
                self.ac_clear = self.create_clear_action()
            self.ac_clear.setVisible(len(self.text()) > 0)
        else:
            if self.ac_clear is not None:
                self.ac_clear.deleteLater()
                self.ac_clear = None

    def setText(self, text: str) -> None:  # type: ignore
        """Sets the text of the search line."""
        self.change_search_term(text, emit=True)

    def keyPressEvent(self, e: Optional["QKeyEvent"]) -> None:  # type: ignore
        """Handle key press events."""

        if e and e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self.enter_triggers:
                self.trigger_callback(self.text())
            self.returnPressed.emit()
            e.accept()
        elif e and e.key() == Qt.Key.Key_Escape:
            self.escapePressed.emit()
            e.accept()
        elif e:
            super().keyPressEvent(e)
