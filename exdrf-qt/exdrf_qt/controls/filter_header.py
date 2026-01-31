import logging
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    List,
    Optional,
    cast,
)

from PyQt5.QtCore import QSize, Qt, QTimer
from PyQt5.QtWidgets import (
    QHeaderView,
    QLineEdit,
    QWidget,
)

from exdrf_qt.context_use import QtUseContext

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext


logger = logging.getLogger(__name__)


class FilterHeader(QHeaderView, QtUseContext):
    """QHeaderView with embedded per-column filter editors.

    Editors are aligned to header sections and follow moves/resizes.
    Filter changes are debounced so the callback runs after typing pauses,
    avoiding a cascade of signals and UI freezes.

    Attributes:
        _editors: The list of editors.
        _placeholder_base: The base placeholder text.
        _on_change: The callback to call when the text changes.
        _filter_height: The height of the filter.
        _debounce_ms: Delay in ms before applying filter after last keystroke.
        _timers: Per-column timers for debouncing; cleared when editors clear.
    """

    _editors: List[QLineEdit]
    _placeholder_base: str
    _on_change: Optional[Callable[[int, str], None]]
    _filter_height: int
    _debounce_ms: int
    _timers: List[Optional[QTimer]]

    def __init__(
        self, ctx: "QtContext", parent: Optional[QWidget] = None
    ) -> None:
        self.ctx = ctx
        super().__init__(Qt.Orientation.Horizontal, parent)
        self._editors = []
        self._placeholder_base = self.t("cmn.filter_placeholder", "Filter")
        self._on_change = None
        self._debounce_ms = 300
        self._timers = []

        # Make room for editors below the header labels
        # Horizontally center the header text while keeping it top-aligned
        self.setDefaultAlignment(
            cast(
                Qt.AlignmentFlag,
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            )
        )
        self.sectionResized.connect(self._adjust_positions)
        self.sectionMoved.connect(lambda *_: self._adjust_positions())
        self._filter_height = 24
        if parent and hasattr(parent, "horizontalScrollBar"):
            parent.horizontalScrollBar().valueChanged.connect(
                self._adjust_positions
            )

    def sizeHint(self) -> QSize:  # type: ignore[override]
        """Get the size hint for the header view."""
        s = super().sizeHint()
        s.setHeight(s.height() + self._filter_height)
        return s

    def init_filters(
        self,
        headers: List[str],
        on_text_changed: Callable[[int, str], None],
        placeholder: Optional[str] = None,
    ) -> None:
        """Initialize the filters.

        Args:
            headers: The headers to initialize the filters for.
            placeholder: The placeholder text to use for the filters.
            on_text_changed: The callback to call when the text changes.
        """
        self._placeholder_base = placeholder or self._placeholder_base
        self._on_change = on_text_changed
        self._clear_editors()
        count = min(self.count(), len(headers))
        self._timers = [None] * count
        for col in range(count):
            ed = QLineEdit(self)
            ed.setClearButtonEnabled(True)
            ed.setPlaceholderText(f"{self._placeholder_base} [{headers[col]}]")
            ed.textChanged.connect(
                lambda text, c=col: self._on_filter_text_changed(c, text)
            )
            self._editors.append(ed)
        self._adjust_positions()

    def _on_filter_text_changed(self, column: int, text: str) -> None:
        """Debounce filter changes: apply immediately when cleared, else after
        a short delay to avoid a cascade of signals while typing.
        """
        if not self._on_change:
            return
        # Apply immediately when filter is cleared so list updates right away
        if not text.strip():
            tmr = self._timers[column] if column < len(self._timers) else None
            if tmr is not None and tmr.isActive():
                tmr.stop()
            self._on_change(column, text)
            return
        # Debounce non-empty text: restart timer for this column
        if column >= len(self._timers):
            return
        if self._timers[column] is not None and self._timers[column].isActive():
            self._timers[column].stop()
        tmr = QTimer(self)
        tmr.setSingleShot(True)
        tmr.timeout.connect(lambda: self._apply_debounced_filter(column))
        self._timers[column] = tmr
        tmr.start(self._debounce_ms)

    def _apply_debounced_filter(self, column: int) -> None:
        """Read current filter text for the column and invoke the callback."""
        if not self._on_change or column >= len(self._editors):
            return
        text = self._editors[column].text()
        self._on_change(column, text)

    def _clear_editors(self) -> None:
        """Clear the editors and their debounce timers."""
        for tmr in self._timers:
            if tmr is not None and tmr.isActive():
                tmr.stop()
        self._timers = []
        for i_ed, ed in enumerate(self._editors):
            try:
                ed.deleteLater()
            except Exception:
                logger.exception("Failed to delete editor %d", i_ed)
        self._editors = []

    def _adjust_positions(self, *args: Any) -> None:
        """Adjust the positions of the editors."""
        y = self.height() - self._filter_height + 1
        for col, ed in enumerate(self._editors):
            if self.isSectionHidden(col):
                ed.hide()
                continue
            try:
                ed.show()
                x = self.sectionViewportPosition(col)
                w = self.sectionSize(col)
                ed.setGeometry(x + 2, y, max(0, w - 4), self._filter_height - 2)
            except Exception:
                continue

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        """Handle the resize event of the header view."""
        super().resizeEvent(event)
        self._adjust_positions()

    def showEvent(self, event) -> None:  # type: ignore[override]
        """Handle the show event of the header view."""
        super().showEvent(event)
        self._adjust_positions()
