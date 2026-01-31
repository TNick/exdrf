"""Code editor widget for template viewer (Jinja+HTML) with line numbers and snippets.

This module provides CodeTextEdit, a QPlainTextEdit with line-number area,
Jinja+HTML syntax highlighting (Pygments), and snippet insertion with
$(name) placeholders navigable by Tab/Shift+Tab. Also defines
LineNumberArea and JinjaHtmlHighlighter.
"""

import logging
import re
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from pygments import lex  # type: ignore
from pygments.lexers import HtmlLexer, get_lexer_by_name  # type: ignore
from pygments.token import Token  # type: ignore
from PyQt5.QtCore import QRect, QSize, Qt
from PyQt5.QtGui import (
    QColor,
    QFocusEvent,
    QFont,
    QKeyEvent,
    QPainter,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextCursor,
    QTextFormat,
)
from PyQt5.QtWidgets import QPlainTextEdit, QTextEdit, QWidget

from exdrf_qt.context_use import QtUseContext

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401

logger = logging.getLogger(__name__)


class LineNumberArea(QWidget):
    """Widget drawn to the left of the editor showing line numbers.

    Delegates size and paint to the parent CodeTextEdit (line_number_area_width
    and line_number_area_paint_event). Used by CodeTextEdit as the margin
    for the line-number gutter.

    Attributes:
        editor: The CodeTextEdit that owns this area and provides width/paint.
    """

    def __init__(self, editor: "CodeTextEdit") -> None:
        """Initialize the line number area with the parent editor.

        Args:
            editor: CodeTextEdit that owns this area and provides
                line_number_area_width and line_number_area_paint_event.
        """
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self) -> QSize:
        """Return the preferred width for the line number area (from editor)."""
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event: Any) -> None:  # type: ignore
        """Paint line numbers by delegating to the editor."""
        self.editor.line_number_area_paint_event(event)


class JinjaHtmlHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for Jinja templates with HTML using Pygments.

    Uses html+jinja lexer when available, else HtmlLexer. When _active
    is false, highlightBlock does nothing. Formats are mapped from
    Pygments token types to QTextCharFormat (colors, bold, italic).

    Attributes:
        formats: Map from Pygments token type to QTextCharFormat.
        lexer: Pygments lexer (html+jinja or HtmlLexer).
        _active: When false, highlighting is skipped.
    """

    _active: bool

    def __init__(self, document: Any, active: bool = True) -> None:
        """Initialize the highlighter with a document and active flag.

        Args:
            document: QTextDocument to attach the highlighter to.
            active: Whether to apply highlighting; default True.
        """
        super().__init__(document)
        self.formats = {}
        self._active = active
        self._init_formats()
        try:
            self.lexer = get_lexer_by_name("html+jinja")
        except Exception:
            logger.log(
                1,
                "html+jinja lexer not available, using HtmlLexer",
                exc_info=True,
            )
            self.lexer = HtmlLexer()

    def _init_formats(self) -> None:
        """Build the token-to-format map for HTML and Jinja token types."""

        def make_format(
            color: str, bold: bool = False, italic: bool = False
        ) -> QTextCharFormat:
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(color))
            if bold:
                fmt.setFontWeight(QFont.Weight.Bold)
            if italic:
                fmt.setFontItalic(True)
            return fmt

        self.formats[Token.Name.Tag] = make_format("#1E90FF", bold=True)
        self.formats[Token.Name.Attribute] = make_format("#FF4500")
        self.formats[Token.Literal.String] = make_format("#008000")
        self.formats[Token.Comment] = make_format("#888888", italic=True)
        self.formats[Token.Operator] = make_format("#AA22FF")
        self.formats[Token.Punctuation] = make_format("#000000")
        self.formats[Token.Text] = make_format("#000000")
        self.formats[Token.Comment.Preproc] = make_format(
            "#B8860B", italic=True
        )
        self.formats[Token.Keyword] = make_format("#B22222", bold=True)
        self.formats[Token.Name.Variable] = make_format("#B22222")
        self.formats[Token.Name.Function] = make_format("#2E8B57")
        self.formats[Token.Literal.Number] = make_format("#2E8B57")
        self.formats[Token.Literal] = make_format("#2E8B57")
        self.formats[Token.Error] = make_format("#FF0000", bold=True)

    def highlightBlock(self, text: str) -> None:
        """Apply syntax highlighting to the current block.

        When _active is false, returns without doing anything. Re-lexes
        the whole document and applies formats to spans that overlap
        this block (Pygments works on full text, not per-block).

        Args:
            text: Plain text of the current block.
        """
        if not self._active:
            return
        doc_obj = self.document()
        if doc_obj is None:
            return
        doc = doc_obj.toPlainText()
        if not doc or not text:
            return
        block_start = self.currentBlock().position()
        block_end = block_start + len(text)
        for token, value in lex(doc, self.lexer):
            if not value:
                continue
            start = doc.find(value, block_start)
            while start != -1 and start < block_end:
                end = start + len(value)
                if start < block_end and end > block_start:
                    relative_start = max(start - block_start, 0)
                    relative_length = min(end, block_end) - max(
                        start, block_start
                    )
                    fmt = self.formats.get(token, QTextCharFormat())
                    self.setFormat(relative_start, relative_length, fmt)
                start = doc.find(value, start + 1)


class CodeTextEdit(QPlainTextEdit, QtUseContext):
    """Plain text editor with line numbers, Jinja+HTML highlighting, and snippets.

    Shows a line-number gutter, highlights Jinja+HTML via Pygments, and
    supports snippet insertion with $(name) placeholders. Tab/Shift+Tab
    cycle through placeholders; Enter/Escape/focus-out clear them.
    highlight_code property toggles syntax highlighting.

    Attributes:
        line_number_area: Widget to the left showing line numbers.
        highlighter: JinjaHtmlHighlighter attached to the document.
        _active_placeholders: List of placeholder dicts (s_cursor, e_cursor, etc.).
        _crt_ph_idx: Index of the currently selected placeholder, or None.
    """

    _active_placeholders: List[Dict[str, Any]]
    _crt_ph_idx: Optional[int]

    def __init__(
        self, ctx: "QtContext", parent: Optional[QWidget] = None
    ) -> None:
        """Initialize the editor with context and optional parent.

        Args:
            ctx: Qt context for translation/settings.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._active_placeholders = []
        self._crt_ph_idx = None
        self.ctx = ctx

        font = self.font()
        font.setFamily("Courier New")
        font.setFixedPitch(True)
        font.setPointSize(12)
        self.setFont(font)

        tab_width = 4 * self.fontMetrics().horizontalAdvance(" ")
        self.setTabStopDistance(tab_width)

        self.line_number_area = LineNumberArea(self)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        self.update_line_number_area_width(0)
        self.highlight_current_line()
        self.highlighter = JinjaHtmlHighlighter(self.document())

    @property
    def highlight_code(self) -> bool:
        """Whether syntax highlighting is active (delegates to highlighter._active)."""
        return self.highlighter._active

    @highlight_code.setter
    def highlight_code(self, value: bool) -> None:
        """Set whether syntax highlighting is active."""
        self.highlighter._active = value

    def line_number_area_width(self) -> int:
        """Return the width in pixels needed for the line number gutter."""
        digits = len(str(max(1, self.blockCount())))
        space = 3 + self.fontMetrics().horizontalAdvance("9") * digits
        return space

    def update_line_number_area_width(self, _: Any) -> None:
        """Update viewport left margin to match line number area width."""
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect: Any, dy: int) -> None:
        """Scroll or repaint the line number area when the editor updates.

        Args:
            rect: Update rect from the editor (may be None).
            dy: Vertical scroll delta; non-zero means scroll the area.
        """
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            if rect is not None:
                self.line_number_area.update(
                    0, rect.y(), self.line_number_area.width(), rect.height()
                )
        vp = self.viewport()
        assert vp is not None
        if (
            rect is not None
            and hasattr(rect, "contains")
            and rect.contains(vp.rect())
        ):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event: Any) -> None:  # type: ignore
        """Resize the line number area to match the left margin height."""
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(
            QRect(
                cr.left(), cr.top(), self.line_number_area_width(), cr.height()
            )
        )

    def set_active_placeholders(
        self, placeholders: List[Dict[str, Any]]
    ) -> None:
        """Set the active placeholders and select the first one.

        Each placeholder dict must have s_cursor and e_cursor (QTextCursor)
        so positions stay correct after document changes.

        Args:
            placeholders: List of placeholder dicts (s_cursor, e_cursor, name,
                etc.); stored as a copy. Empty list clears placeholders.
        """
        self._active_placeholders = list(placeholders)
        if self._active_placeholders:
            self._crt_ph_idx = 0
            self._select_current_placeholder()
        else:
            self._clear_active_placeholders()

    def _clear_active_placeholders(self) -> None:
        """Clear the active placeholders list and current index."""
        self._active_placeholders = []
        self._crt_ph_idx = None

    def _select_current_placeholder(self) -> None:
        """Select the placeholder at _crt_ph_idx and ensure it is visible.

        Uses s_cursor and e_cursor positions (which track document changes).
        If the index is out of range, clears placeholders.
        """
        if self._crt_ph_idx is not None and 0 <= self._crt_ph_idx < len(
            self._active_placeholders
        ):
            placeholder = self._active_placeholders[self._crt_ph_idx]
            current_s_pos = placeholder["s_cursor"].position()
            current_e_pos = placeholder["e_cursor"].position()

            cursor = self.textCursor()
            cursor.setPosition(current_s_pos)
            cursor.setPosition(current_e_pos, QTextCursor.MoveMode.KeepAnchor)
            self.setTextCursor(cursor)
            self.ensureCursorVisible()
        else:
            self._clear_active_placeholders()

    def line_number_area_paint_event(self, event: Any) -> None:
        """Paint line numbers in the gutter for visible blocks.

        Fills the area with light gray and draws block numbers
        (1-based) right-aligned. Called by LineNumberArea.paintEvent.

        Args:
            event: Paint event with rect to update.
        """
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor("lightgray"))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(
            self.blockBoundingGeometry(block)
            .translated(self.contentOffset())
            .top()
        )
        bottom = top + int(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(QColor("black"))
                painter.drawText(
                    0,
                    top,
                    self.line_number_area.width() - 2,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight,
                    number,
                )
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1

    def highlight_current_line(self) -> None:
        """Set extra selection to highlight the current line (when not read-only)."""
        extra_selections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            line_color = QColor("yellow").lighter(160)
            selection.format.setBackground(line_color)
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)
        self.setExtraSelections(extra_selections)

    def keyPressEvent(self, e: Optional[QKeyEvent]) -> None:
        """Handle Tab/Shift+Tab for placeholder navigation; Enter/Escape clear."""
        if e is None:
            super().keyPressEvent(e)
            return

        if not self._active_placeholders or self._crt_ph_idx is None:
            super().keyPressEvent(e)
            return

        key = e.key()
        modifiers = e.modifiers()

        if key == Qt.Key.Key_Tab:
            if modifiers == Qt.KeyboardModifier.NoModifier:
                next_idx = self._crt_ph_idx + 1
                self._crt_ph_idx = next_idx % len(self._active_placeholders)
                self._select_current_placeholder()
                e.accept()
                return
        elif key == Qt.Key.Key_Backtab:
            is_shift_tab = modifiers == Qt.KeyboardModifier.ShiftModifier
            is_shift_tab_keypad = modifiers == (
                Qt.KeyboardModifier.ShiftModifier
                | Qt.KeyboardModifier.KeypadModifier
            )
            if is_shift_tab or is_shift_tab_keypad:
                prev_idx = self._crt_ph_idx - 1
                current_len = len(self._active_placeholders)
                self._crt_ph_idx = (prev_idx + current_len) % current_len
                self._select_current_placeholder()
                e.accept()
                return
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Escape):
            self._clear_active_placeholders()
            super().keyPressEvent(e)
            return

        super().keyPressEvent(e)

    def focusOutEvent(self, e: Optional[QFocusEvent]) -> None:
        """Clear active placeholders when the editor loses focus."""
        if e is None:
            super().focusOutEvent(e)
            return
        self._clear_active_placeholders()
        super().focusOutEvent(e)

    def insert_snippet(self, snippet: str) -> None:
        """Insert a snippet at the cursor; $(name) become navigable placeholders.

        Replaces $(name) with the literal name and builds placeholder
        ranges (s_cursor, e_cursor) for Tab/Shift+Tab navigation.
        Indent of the first line is applied to following lines.

        Args:
            snippet: Text containing $(placeholder_name) markers; newlines
                separate lines; later lines get the same indent as current.
        """
        initial_cursor = self.textCursor()
        insertion_point_doc_pos = initial_cursor.position()

        current_block_text = initial_cursor.block().text()
        indent_level = len(current_block_text) - len(
            current_block_text.lstrip()
        )
        indent_string = current_block_text[:indent_level]

        final_text_to_insert = ""
        placeholder_definitions = []

        placeholder_pattern = re.compile(r"\$\(([^\)]+)\)")
        lines = snippet.split("\n")

        for line_idx, raw_line_content in enumerate(lines):
            line_with_indent_for_matching = raw_line_content
            if line_idx > 0:
                line_with_indent_for_matching = indent_string + raw_line_content

            current_line_start_offset_in_final_text = len(final_text_to_insert)
            processed_line_segment = ""
            last_match_end_in_line = 0

            for match in placeholder_pattern.finditer(
                line_with_indent_for_matching
            ):
                placeholder_name = match.group(1)
                match_start = match.start()
                match_end = match.end()

                text_before_placeholder = line_with_indent_for_matching[
                    last_match_end_in_line:match_start
                ]
                processed_line_segment += text_before_placeholder

                relative_s = current_line_start_offset_in_final_text + len(
                    processed_line_segment
                )
                relative_e = relative_s + len(placeholder_name)

                placeholder_definitions.append(
                    {
                        "name": placeholder_name,
                        "relative_s": relative_s,
                        "relative_e": relative_e,
                        "l-idx": line_idx,
                        "orig_text": match.group(0),
                    }
                )

                processed_line_segment += placeholder_name
                last_match_end_in_line = match_end

            processed_line_segment += line_with_indent_for_matching[
                last_match_end_in_line:
            ]
            final_text_to_insert += processed_line_segment
            if line_idx < len(lines) - 1:
                final_text_to_insert += "\n"

        self.insertPlainText(final_text_to_insert)

        final_active_placeholders = []
        doc = self.document()
        for p_def in placeholder_definitions:
            abs_s = insertion_point_doc_pos + int(p_def["relative_s"])
            abs_e = insertion_point_doc_pos + int(p_def["relative_e"])

            s_cursor = QTextCursor(doc)
            s_cursor.setPosition(abs_s)
            e_cursor = QTextCursor(doc)
            e_cursor.setPosition(abs_e)

            final_active_placeholders.append(
                {
                    "name": p_def["name"],
                    "s_cursor": s_cursor,
                    "e_cursor": e_cursor,
                    "l-idx": p_def["l-idx"],
                    "orig_text": p_def["orig_text"],
                }
            )

        self.set_active_placeholders(final_active_placeholders)
