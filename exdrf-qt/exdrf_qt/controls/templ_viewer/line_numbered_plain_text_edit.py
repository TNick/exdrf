from typing import TYPE_CHECKING

from pygments import lex
from pygments.lexers import HtmlLexer, get_lexer_by_name
from pygments.token import Token
from PyQt5.QtCore import QRect, QSize, Qt
from PyQt5.QtGui import (
    QColor,
    QFont,
    QPainter,
    QSyntaxHighlighter,
    QTextCharFormat,
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

    def paintEvent(self, event):
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


class LineNumberedPlainTextEdit(QPlainTextEdit, QtUseContext):
    """A plain text edit that displays line numbers.

    Attributes:
        ctx: The context of the editor.
    """

    def __init__(self, ctx: "QtContext", parent=None):
        super().__init__(parent)
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

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(
            QRect(
                cr.left(), cr.top(), self.line_number_area_width(), cr.height()
            )
        )

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
