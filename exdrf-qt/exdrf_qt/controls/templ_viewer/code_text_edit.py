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


class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):  # type: ignore
        self.editor.line_number_area_paint_event(event)


class JinjaHtmlHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for Jinja templates with HTML using Pygments."""

    def __init__(self, document):
        super().__init__(document)
        # Define formats for different token types
        self.formats = {}
        self._init_formats()
        # Use the HTML+Jinja lexer
        try:
            self.lexer = get_lexer_by_name("html+jinja")
        except Exception:
            self.lexer = HtmlLexer()

    def _init_formats(self):
        def make_format(color, bold=False, italic=False):
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(color))
            if bold:
                fmt.setFontWeight(QFont.Weight.Bold)
            if italic:
                fmt.setFontItalic(True)
            return fmt

        # HTML
        self.formats[Token.Name.Tag] = make_format("#1E90FF", bold=True)
        self.formats[Token.Name.Attribute] = make_format("#FF4500")
        self.formats[Token.Literal.String] = make_format("#008000")
        self.formats[Token.Comment] = make_format("#888888", italic=True)
        self.formats[Token.Operator] = make_format("#AA22FF")
        self.formats[Token.Punctuation] = make_format("#000000")
        self.formats[Token.Text] = make_format("#000000")
        # Jinja
        self.formats[Token.Comment.Preproc] = make_format(
            "#B8860B", italic=True
        )
        self.formats[Token.Keyword] = make_format("#B22222", bold=True)
        self.formats[Token.Name.Variable] = make_format("#B22222")
        self.formats[Token.Name.Function] = make_format("#2E8B57")
        self.formats[Token.Literal.Number] = make_format("#2E8B57")
        self.formats[Token.Literal] = make_format("#2E8B57")
        self.formats[Token.Error] = make_format("#FF0000", bold=True)

    def highlightBlock(self, text):
        # Pygments lexers work on the whole document, so we need to re-lex the
        # whole text and cache the results for each block. For simplicity,
        # re-lex the whole document here. For large documents, a more efficient
        # approach may be needed.
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
    """A custom text editor to handle snippet placeholder navigation."""

    _active_placeholders: List[Dict[str, Any]]
    _crt_ph_idx: Optional[int]

    def __init__(self, ctx: "QtContext", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._active_placeholders = []
        self._crt_ph_idx = None

        self.ctx = ctx

        font = self.font()
        font.setFamily("Courier New")
        font.setFixedPitch(True)
        font.setPointSize(12)
        self.setFont(font)

        # Set tab width to 4 characters
        tab_width = 4 * self.fontMetrics().horizontalAdvance(" ")
        self.setTabStopDistance(tab_width)

        self.line_number_area = LineNumberArea(self)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        self.update_line_number_area_width(0)
        self.highlight_current_line()
        # Attach syntax highlighter
        self.highlighter = JinjaHtmlHighlighter(self.document())

    def line_number_area_width(self):
        digits = len(str(max(1, self.blockCount())))
        space = 3 + self.fontMetrics().horizontalAdvance("9") * digits
        return space

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
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

    def resizeEvent(self, event):  # type: ignore
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(
            QRect(
                cr.left(), cr.top(), self.line_number_area_width(), cr.height()
            )
        )

    def set_active_placeholders(self, placeholders: List[Dict[str, Any]]):
        """
        Sets the active placeholders. The placeholder positions ('s', 'e')
        are expected to be absolute document positions.
        """
        self._active_placeholders = list(placeholders)  # Store a copy
        if self._active_placeholders:
            self._crt_ph_idx = 0
            self._select_current_placeholder()
        else:
            self._clear_active_placeholders()

    def _clear_active_placeholders(self):
        """Clears the active placeholders and selection index."""
        self._active_placeholders = []
        self._crt_ph_idx = None

    def _select_current_placeholder(self):
        """Selects the placeholder at the current index in the editor."""
        if self._crt_ph_idx is not None and 0 <= self._crt_ph_idx < len(
            self._active_placeholders
        ):
            placeholder = self._active_placeholders[self._crt_ph_idx]

            # Get current positions from stored cursors. These are dynamic
            # and reflect document changes since snippet insertion.
            current_s_pos = placeholder["s_cursor"].position()
            current_e_pos = placeholder["e_cursor"].position()

            # If placeholder content was altered, s_pos might be >= e_pos.
            # Selecting such a range typically moves cursor to s_pos.

            cursor = self.textCursor()
            cursor.setPosition(current_s_pos)
            cursor.setPosition(current_e_pos, QTextCursor.MoveMode.KeepAnchor)
            self.setTextCursor(cursor)
            self.ensureCursorVisible()
        else:
            # If index is invalid, clear placeholders as a safety measure
            self._clear_active_placeholders()

    def line_number_area_paint_event(self, event):
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

    def highlight_current_line(self):
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

    def keyPressEvent(self, e: Optional[QKeyEvent]):
        """Handles key presses for placeholder navigation and lifecycle."""
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
        elif key == Qt.Key.Key_Backtab:  # Shift+Tab
            is_shift_tab = modifiers == Qt.KeyboardModifier.ShiftModifier
            is_shift_tab_keypad = modifiers == (
                Qt.KeyboardModifier.ShiftModifier
                | Qt.KeyboardModifier.KeypadModifier
            )  # KeypadModifier for num-lock
            if is_shift_tab or is_shift_tab_keypad:
                prev_idx = self._crt_ph_idx - 1
                current_len = len(self._active_placeholders)
                self._crt_ph_idx = (prev_idx + current_len) % current_len
                self._select_current_placeholder()
                e.accept()
                return
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Escape):
            self._clear_active_placeholders()
            # Let the event propagate for normal editor behavior (e.g., newline)
            super().keyPressEvent(e)
            return

        super().keyPressEvent(e)

    def focusOutEvent(self, e: Optional[QFocusEvent]):
        """Clears active placeholders when the editor loses focus."""
        if e is None:
            super().focusOutEvent(e)
            return
        self._clear_active_placeholders()
        super().focusOutEvent(e)

    def insert_snippet(self, snippet: str):
        """Inserts a snippet into the editor."""
        initial_cursor = self.textCursor()
        insertion_point_doc_pos = initial_cursor.position()

        current_block_text = initial_cursor.block().text()
        indent_level = len(current_block_text) - len(
            current_block_text.lstrip()
        )
        indent_string = current_block_text[:indent_level]

        final_text_to_insert = ""
        # Stores {name, relative_s, relative_e, l-idx, orig_text}
        placeholder_definitions = []

        placeholder_pattern = re.compile(r"\$\(([^\)]+)\)")
        lines = snippet.split("\n")

        for line_idx, raw_line_content in enumerate(lines):
            line_with_indent_for_matching = raw_line_content
            if line_idx > 0:
                line_with_indent_for_matching = indent_string + raw_line_content

            # Offset where this new line's content will start
            # in final_text_to_insert
            current_line_start_offset_in_final_text = len(final_text_to_insert)

            # Builds the current line with $(name) -> name
            processed_line_segment = ""
            last_match_end_in_line = 0

            for match in placeholder_pattern.finditer(
                line_with_indent_for_matching
            ):
                placeholder_name = match.group(1)
                match_start = match.start()
                match_end = match.end()

                # Append text before this placeholder
                text_before_placeholder = line_with_indent_for_matching[
                    last_match_end_in_line:match_start
                ]
                processed_line_segment += text_before_placeholder

                # Calculate relative start/end of placeholder_name
                # within final_text_to_insert
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

                # Append the placeholder NAME itself
                processed_line_segment += placeholder_name
                last_match_end_in_line = match_end

            # Append remaining part of the line
            processed_line_segment += line_with_indent_for_matching[
                last_match_end_in_line:
            ]

            final_text_to_insert += processed_line_segment
            if line_idx < len(lines) - 1:
                final_text_to_insert += "\n"

        # Insert the fully processed text
        self.insertPlainText(final_text_to_insert)

        # Now, create actual cursors and store them
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
