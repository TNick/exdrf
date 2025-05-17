import logging
import re
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Generic,
    List,
    Optional,
    Tuple,
    Union,
    cast,
)

from exdrf.filter import FilterType
from exdrf.filter_dsl import (
    DSLParserWithValidation,
    DSLTokenizer,
    FieldValidator,
    FltErrCode,
    FltSyntaxError,
    Token,
    raw_filter_to_text,
    serialize_filter,
)
from PyQt5.QtCore import QStringListModel, Qt, pyqtSignal
from PyQt5.QtGui import (
    QColor,
    QFont,
    QKeyEvent,
    QTextCharFormat,
    QTextCursor,
)
from PyQt5.QtWidgets import QCompleter, QLabel, QPlainTextEdit

from exdrf_qt.context_use import QtUseContext

# Alias to avoid confusion if QtField is used elsewhere
from exdrf_qt.models.field import QtField as ExdrfQtField
from exdrf_qt.models.model import DBM, QtModel  # noqa: F401

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401
    from exdrf_qt.controls.filter_dlg.filter_dlg import FilterDlg

logger = logging.getLogger(__name__)


class FilterEditor(QPlainTextEdit, QtUseContext, Generic[DBM]):
    """Rich text editor for the filter DSL with inline syntax highlighting.

    Attributes:
        all_field_names_cache: Cache for all field names for completion. These
            are the fields reported by the model to be filterable.
        completer_model: The model for the QCompleter.
        completer: The QCompleter for autocompletion.
        l_error: The error label that gets updated with the error message.
        parser: The parser for the filter DSL.
        qt_model: The Qt model that contains the fields and where we will
            apply the filter.
        tokenizer: The tokenizer for the filter DSL.
        validator: The validator for the filter DSL.
    """

    all_field_names_cache: List[str]
    completer_model: QStringListModel
    completer: QCompleter
    l_error: Optional[QLabel]
    parser: Optional[DSLParserWithValidation]
    qt_model: "QtModel[DBM]"
    tokenizer: Optional[DSLTokenizer]
    validator: Optional[FieldValidator]

    errorChanged = pyqtSignal(bool)

    def __init__(
        self,
        ctx: "QtContext",
        parent: "FilterDlg",
    ) -> None:
        """Initialize the editor.

        Args:
            ctx: The Qt context.
            parent: The parent widget.
            qt_model: The Qt model that contains the fields and where we will
                apply the filter.
        """
        super().__init__(parent)
        self.ctx = ctx
        self.qt_model = None  # type: ignore
        self.validator = None
        self.l_error = None
        self.err_start = -1
        self.parser: Optional[DSLParserWithValidation] = None
        self.tokenizer: Optional[DSLTokenizer] = None
        self.all_field_names_cache = []

        # Setup formats
        self._setup_formats()

        # Setup completer
        self._setup_completer()

        # Connect text changed signal
        self.textChanged.connect(self._on_text_changed)

        # Setup tab stop distance
        metrics = self.fontMetrics()
        self.setTabStopDistance(4 * metrics.horizontalAdvance(" "))

    def prepare(
        self,
        validator: FieldValidator,
        l_error: QLabel,
        qt_model: "QtModel[DBM]",
    ) -> None:
        self.set_validator(validator)
        self.l_error = l_error
        self.qt_model = qt_model

        suggestions = self._generate_suggestions("FIELD", "", {})
        self.completer_model.setStringList(suggestions)

        self.load_filter(self.qt_model.filters)

    def load_filter(self, filter: FilterType) -> None:
        """Load a filter into the editor.

        Args:
            filter: The filter to load.
        """
        self.setPlainText(raw_filter_to_text(filter))

    def set_validator(self, validator: FieldValidator) -> None:
        """Set the field validator and update field cache for completer."""
        self.validator = validator
        if self.qt_model:
            self.all_field_names_cache = sorted(
                [f.name for f in self.qt_model.filter_fields]
            )

    def insert_completion(self, completion_text: str) -> None:
        """Insert the selected completion text.

        The completer popup is a QCompleter that is set up to work with the
        FilterEditor. When a completion is selected, this method is called to
        insert the selected text at the cursor position.

        The method calculates how many characters of the prefix to remove,
        moves the cursor to the start of the prefix, selects the prefix text,
        and then inserts the full completion text, replacing the prefix.

        Args:
            completion_text: The text to insert.
        """
        tc = self.textCursor()

        # Calculate how many characters of the prefix to remove.
        prefix_len = len(self.completer.completionPrefix())

        # Move cursor back to the start of the prefix
        tc.movePosition(
            QTextCursor.MoveOperation.Left,
            QTextCursor.MoveMode.MoveAnchor,
            prefix_len,
        )

        # Select the prefix text
        tc.movePosition(
            QTextCursor.MoveOperation.Right,
            QTextCursor.MoveMode.KeepAnchor,
            prefix_len,
        )

        # Insert the full completion, replacing the prefix
        tc.insertText(completion_text)
        self.setTextCursor(tc)

    def _get_token_semantic_type(
        self, token: Token, all_field_names: List[str]
    ) -> str:
        """Determine the semantic type of a token for completion context.

        The method determines the semantic type of a token for completion
        context. It checks if the token is a logic operator, operator, field
        name, value string, or value number.

        Args:
            token: The token to determine the semantic type of.
            all_field_names: The list of all field names for completion.

        Returns:
            The semantic type of the token: "LOGIC_OP", "OPERATOR",
            "FIELD_NAME", "VALUE_STRING", or "VALUE_NUMBER".
        """
        value_upper = token.value.upper()
        if value_upper in ("AND", "OR", "NOT"):
            return "LOGIC_OP"

        if value_upper in ("==", "!=", ">", ">=", "<", "<="):
            return "OPERATOR"

        if token.value in all_field_names:
            return "FIELD_NAME"

        if value_upper.startswith("'") and value_upper.endswith("'"):
            return "VALUE_STRING"

        if value_upper.isdigit() or (
            "." in value_upper
            and all(c.isdigit() or c == "." for c in value_upper)
        ):
            try:
                float(value_upper)
                return "VALUE_NUMBER"
            except ValueError:
                pass
        return "FIELD_NAME"

    def _determine_suggestion_context(
        self, cursor_pos: int
    ) -> Tuple[str, str, Dict[str, Any]]:
        """Determines the context for autocompletion.

        The method determines the context for autocompletion based on the
        current cursor position. It returns a tuple containing the suggestion
        type, the current typing prefix, and context data.

        Args:
            cursor_pos: The position of the cursor.

        Returns:
            The suggestion type, the current typing prefix, and context data.
        """
        full_text = self.toPlainText()
        current_typing_prefix = ""
        suggestion_type = "FIELD"
        context_data: Dict[str, Any] = {}

        # Calculate the current typing prefix.
        start_prefix_pos = cursor_pos
        delimiters_for_prefix = " \t\n\r(),=:!<>"
        while (
            start_prefix_pos > 0
            and full_text[start_prefix_pos - 1] not in delimiters_for_prefix
        ):
            start_prefix_pos -= 1
        current_typing_prefix = full_text[start_prefix_pos:cursor_pos]

        # Calculate the text before the prefix start.
        text_before_prefix_start = full_text[:start_prefix_pos].rstrip()
        last_meaningful_token: Optional[Token] = None

        # Prioritize using the main parser's tokens if they are fresh and
        # relevant.
        if self.parser and self.parser.tokens:
            candidate_token = None
            for token in self.parser.tokens:
                if (
                    token.index <= start_prefix_pos
                ):  # Token ends before or at the start of the current prefix
                    candidate_token = token
                else:
                    break

            # Ensure the candidate_token is immediately before the current
            # prefix (or very close). Allows for 0 or 1 char (e.g. space)
            if (
                candidate_token
                and (start_prefix_pos - candidate_token.index) <= 1
            ):
                last_meaningful_token = candidate_token

        if (
            not last_meaningful_token and text_before_prefix_start
        ):  # Fallback to temporary tokenization
            try:
                temp_tokenizer = DSLTokenizer(text_before_prefix_start)
                temp_tokens = temp_tokenizer.tokenize()
                if temp_tokens:
                    last_meaningful_token = temp_tokens[-1]
            except FltSyntaxError:
                pass

        # If there is a last meaningful token, determine the semantic type.
        if last_meaningful_token:
            field_names = self.all_field_names_cache
            token_type = self._get_token_semantic_type(
                last_meaningful_token, field_names
            )
            val_upper = last_meaningful_token.value.upper()

            # Determine the suggestion type based on the token type.
            if token_type == "LOGIC_OP" or val_upper in ("(", ","):
                suggestion_type = "FIELD"
            elif token_type == "FIELD_NAME":
                suggestion_type = "OPERATOR"
                field_obj = next(
                    (
                        f
                        for f in self.qt_model.filter_fields
                        if f.name == last_meaningful_token.value
                    ),
                    None,
                )
                context_data["field"] = field_obj
            elif token_type == "OPERATOR":
                suggestion_type = "VALUE"
                # Attempt to find the preceding field token from
                # self.parser.tokens
                if self.parser and self.parser.tokens:
                    try:
                        # Find the index of the operator token
                        # (last_meaningful_token)
                        op_idx = -1
                        for i, t in enumerate(self.parser.tokens):
                            # Match by object identity if possible, or value
                            # and position for robustness
                            if t is last_meaningful_token or (
                                t.value == last_meaningful_token.value
                                and t.index == last_meaningful_token.index
                            ):
                                op_idx = i
                                break
                        if op_idx > 0:
                            field_token_candidate = self.parser.tokens[
                                op_idx - 1
                            ]
                            if (
                                self._get_token_semantic_type(
                                    field_token_candidate, field_names
                                )
                                == "FIELD_NAME"
                            ):
                                field_obj = next(
                                    (
                                        f
                                        for f in self.qt_model.filter_fields
                                        if f.name == field_token_candidate.value
                                    ),
                                    None,
                                )
                                context_data["field"] = field_obj
                                context_data["operator"] = (
                                    last_meaningful_token.value
                                )
                            else:
                                suggestion_type = "FIELD"
                        else:
                            suggestion_type = "FIELD"
                    except (ValueError, IndexError):
                        suggestion_type = "FIELD"
                else:
                    suggestion_type = "FIELD"
            elif token_type.startswith("VALUE") or val_upper == ")":
                suggestion_type = "LOGIC"
            else:
                suggestion_type = "FIELD"
        else:
            suggestion_type = "FIELD"
            if (
                current_typing_prefix.upper() in ("AND", "OR", "NOT")
                and len(current_typing_prefix) > 1
            ):
                suggestion_type = "LOGIC"
        return suggestion_type, current_typing_prefix, context_data

    def _generate_suggestions(
        self, suggestion_type: str, prefix: str, context_data: Dict[str, Any]
    ) -> List[str]:
        """Generates a list of suggestions based on context.

        The method generates a list of suggestions based on the context data.
        It checks if the suggestion type is "FIELD", "OPERATOR", "VALUE", or
        "LOGIC" and generates suggestions accordingly.

        Args:
            suggestion_type: The type of suggestion to generate.
            prefix: The current typing prefix.
            context_data: The context data.

        Returns:
            A list of suggestions.
        """
        if not self.all_field_names_cache and self.qt_model:
            self.all_field_names_cache = sorted(
                [f.name for f in self.qt_model.filter_fields]
            )

        # Generate suggestions based on the suggestion type.
        if suggestion_type == "FIELD":
            suggestions = [
                name
                for name in self.all_field_names_cache
                if name.lower().startswith(prefix.lower())
            ]
            if not prefix or prefix.isspace():
                logic_ops = ["AND ", "OR ", "NOT "]
                # Only add logic ops if they also match the prefix (e.g. user
                # types 'A')
                suggestions.extend(
                    [
                        op
                        for op in logic_ops
                        if op.lower().startswith(prefix.lower())
                    ]
                )

        elif suggestion_type == "OPERATOR":
            # Generate operator suggestions based on the field type.
            field: Optional[ExdrfQtField] = context_data.get("field")
            ops: List[str] = []
            if field:
                field_type_str = getattr(field, "type", "").lower()
                numeric_ex_types = [
                    "integer",
                    "float",
                    "numeric",
                    "date",
                    "datetime",
                    "int",
                ]
                string_ex_types = ["string", "text", "str"]
                boolean_ex_types = ["boolean", "bool"]
                if any(t in field_type_str for t in numeric_ex_types):
                    ops = [
                        "== ",
                        "!= ",
                        "> ",
                        ">= ",
                        "< ",
                        "<= ",
                    ]  # Add trailing space
                elif any(t in field_type_str for t in string_ex_types):
                    ops = ["== ", "!= "]
                elif any(t in field_type_str for t in boolean_ex_types):
                    ops = ["== ", "!= "]
                else:
                    ops = ["== ", "!= ", "> ", ">= ", "< ", "<= "]
            else:
                ops = ["== ", "!= ", "> ", ">= ", "< ", "<= "]

            # Compare without trailing space for prefix match
            suggestions = [op for op in ops if op.strip().startswith(prefix)]

        elif suggestion_type == "VALUE":
            # Generate value suggestions based on the field type.
            fld: Optional[ExdrfQtField] = context_data.get("field")
            vals: List[str] = []
            if fld:
                field_type_str = getattr(fld, "type", "").lower()
                boolean_ex_types = ["boolean", "bool"]
                if any(t in field_type_str for t in boolean_ex_types):
                    # Add trailing space
                    vals = ["'true' ", "'false' ", "1 ", "0 "]
            suggestions = [
                val
                for val in vals
                if val.lower().strip().startswith(prefix.lower())
            ]

        elif suggestion_type == "LOGIC":
            # Generate logic operator suggestions.
            logic_ops = ["AND ", "OR ", "NOT "]
            suggestions = [
                op for op in logic_ops if op.lower().startswith(prefix.lower())
            ]
            if not prefix:
                suggestions.extend(
                    [
                        name
                        for name in self.all_field_names_cache
                        if name.lower().startswith(prefix.lower())
                    ]
                )
        else:
            raise ValueError(f"Invalid suggestion type: {suggestion_type}")

        return sorted(list(set(suggestions)))

    def _update_completer_popup(self) -> None:
        """Update and show the completer popup.

        The method updates the completer popup with the current typing prefix
        and generates suggestions based on the current context. It then shows
        the popup if there are suggestions and a non-whitespace prefix.
        """
        cursor_pos = self.textCursor().position()
        suggestion_type, prefix, context_data = (
            self._determine_suggestion_context(cursor_pos)
        )
        self.completer.setCompletionPrefix(prefix)
        suggestions = self._generate_suggestions(
            suggestion_type, prefix, context_data
        )
        self.completer_model.setStringList(suggestions)

        popup = self.completer.popup()
        if suggestions:
            # Only show if there are suggestions
            if popup:  # Check if popup exists
                scb = popup.verticalScrollBar()
                assert scb is not None
                cr = self.cursorRect()
                cr.setWidth(popup.sizeHintForColumn(0) + scb.sizeHint().width())
                self.completer.complete(cr)
        elif popup:  # Hide if no suggestions or empty prefix
            popup.hide()

    def keyPressEvent(self, e: Optional[QKeyEvent] = None) -> None:
        """Handle key presses.

        The tab key is used for indentation. The shift+tab key is used for
        un-indentation.

        The enter key is used to accept the filter. The escape key is used to
        cancel the filter. The up and down keys are used to navigate the
        completer popup.

        The control+space key is used to show the completer popup.

        Args:
            e: The key event.
        """
        assert e is not None
        popup = self.completer.popup()

        k = e.key()
        m = e.modifiers()

        # Handle completer popup interaction first.
        if popup and popup.isVisible():
            if k in (
                Qt.Key.Key_Enter,
                Qt.Key.Key_Return,
                Qt.Key.Key_Escape,
                Qt.Key.Key_Up,
                Qt.Key.Key_Down,
                Qt.Key.Key_Tab,
                Qt.Key.Key_Backtab,
            ):
                e.ignore()
                popup.keyPressEvent(e)
                if k == Qt.Key.Key_Escape:
                    popup.hide()
                return

        is_shortcut = (
            m == Qt.KeyboardModifier.ControlModifier and k == Qt.Key.Key_Space
        )
        if is_shortcut:
            self._update_completer_popup()
            e.accept()
            return

        # Handle Return/Enter to maintain indentation level
        if k in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            cursor = self.textCursor()
            block = cursor.block()
            text = block.text()

            # Count leading tabs
            leading_tabs = 0
            for char in text:
                if char == "\t":
                    leading_tabs += 1
                else:
                    break

            # Insert newline with same indentation
            cursor.insertText("\n" + "\t" * leading_tabs)
            e.accept()
            return

        # Handle Tab for indentation if text is selected.
        if k == Qt.Key.Key_Tab and self.textCursor().hasSelection():
            doc = self.document()
            assert doc is not None

            cursor = self.textCursor()
            start = cursor.selectionStart()
            end = cursor.selectionEnd()

            cursor.setPosition(start)
            start_block = cursor.blockNumber()

            cursor.setPosition(end)
            end_block = cursor.blockNumber()

            cursor.beginEditBlock()

            if m == Qt.KeyboardModifier.ShiftModifier:
                # Shift+Tab unindents
                for line_num in range(start_block, end_block + 1):
                    line_cursor = QTextCursor(doc.findBlockByNumber(line_num))
                    line_cursor.movePosition(
                        QTextCursor.MoveOperation.StartOfLine
                    )
                    if line_cursor.block().text().startswith("\t"):
                        line_cursor.deletePreviousChar()
            else:
                # Tab indents
                for line_num in range(start_block, end_block + 1):
                    # Create a new cursor for each line modification
                    line_cursor = QTextCursor(doc.findBlockByNumber(line_num))
                    line_cursor.movePosition(
                        QTextCursor.MoveOperation.StartOfLine
                    )
                    line_cursor.insertText("\t")

            cursor.endEditBlock()
            e.accept()
            return

        super().keyPressEvent(e)  # Default handling for other keys

        # Update completer after text might have changed by
        # super().keyPressEvent(). Only update if a non-empty prefix is being
        # typed for completion.
        if not is_shortcut and self.completer.completionPrefix().strip():
            self._update_completer_popup()

    def _setup_completer(self) -> None:
        """Setup the completer."""
        self.completer = QCompleter(self)
        self.completer_model = QStringListModel(self)
        self.completer.setModel(self.completer_model)
        self.completer.setWidget(self)
        self.completer.setCompletionMode(
            QCompleter.CompletionMode.PopupCompletion
        )
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.activated.connect(self.insert_completion)

    def _setup_formats(self) -> None:
        """Initialize text formats for different token types."""
        no_error_bk = QColor("#FFFFFF")
        default_font_size = 10  # Or get from self.font().pointSize()

        self.logic_format = QTextCharFormat()
        self.logic_format.setForeground(QColor("#0000FF"))
        self.logic_format.setFontWeight(QFont.Weight.Bold)
        self.logic_format.setBackground(no_error_bk)
        self.logic_format.setFontPointSize(default_font_size)

        self.field_format = QTextCharFormat()
        self.field_format.setForeground(QColor("#2E7D32"))
        self.field_format.setBackground(no_error_bk)
        self.field_format.setFontPointSize(default_font_size)

        self.op_format = QTextCharFormat()
        self.op_format.setForeground(QColor("#9C27B0"))
        self.op_format.setBackground(no_error_bk)
        self.op_format.setFontPointSize(default_font_size)

        self.value_format = QTextCharFormat()
        self.value_format.setForeground(QColor("#A52A2A"))  # Brown for values
        self.value_format.setBackground(no_error_bk)
        self.value_format.setFontItalic(True)
        self.value_format.setFontPointSize(default_font_size)

        self.error_format = QTextCharFormat()
        self.error_format.setBackground(QColor("#FFEBEE"))
        self.error_format.setFontPointSize(default_font_size)

        self.valid_format = QTextCharFormat()
        self.valid_format.setBackground(QColor("#E8F5E9"))
        self.valid_format.setFontPointSize(default_font_size)

        self.default_format = QTextCharFormat()
        self.default_format.setBackground(QColor("#FFFFFF"))
        self.default_format.setFontPointSize(default_font_size)

    def _on_text_changed(self) -> None:
        """Handle text changes and update highlighting."""
        self.check_document()
        self.update_highlighting()

    def check_document(self) -> Union[FilterType, None]:
        """Parse and validate the current document text."""
        full_text = self.toPlainText()
        if not self.all_field_names_cache and self.qt_model:
            self.all_field_names_cache = sorted(
                [
                    f.name
                    for f in self.qt_model.filter_fields  # Access as property
                ]
            )

        assert self.l_error is not None

        if not full_text or not full_text.strip():
            self.errorChanged.emit(False)
            self.l_error.setText("")
            self.parser = None
            self.tokenizer = None
            self.err_start = -1
            popup = self.completer.popup()
            if popup and popup.isVisible():
                popup.hide()
            return []

        current_tokenizer = DSLTokenizer(text=full_text)
        _validator = (
            self.validator
            if self.validator
            else FieldValidator(
                ctx=self.ctx,
                qt_model=self.qt_model,
            )
        )

        self.parser = DSLParserWithValidation(
            src_text=full_text,
            tokens=[],
            index=0,
            validator=_validator,
        )
        self.tokenizer = current_tokenizer

        try:
            self.parser.tokens = self.tokenizer.tokenize()
            result = self.parser.parse()
            self.errorChanged.emit(False)
            self.l_error.setText("")
            self.err_start = -1
            return cast(FilterType, ["AND", serialize_filter(result)])
        except FltSyntaxError as exc:
            self.handle_syntax_error(exc)
            return None

    def handle_syntax_error(self, exc: FltSyntaxError) -> None:
        """Handle syntax errors during parsing/tokenizing."""
        assert self.l_error is not None
        assert exc.offset is not None
        assert exc.lineno is not None
        assert exc.source is not None

        # logger.error("Syntax error", exc_info=exc)
        self.err_start = exc.offset
        msg_key_prefix = "cmn.filter.error."
        default_msg_template = "Error on line {line} at column {column}: {err}"
        err_code_str = exc.code.value if exc.code else "unknown_error"

        msg_data = exc.as_dict()
        specific_msg = ""

        if exc.code == FltErrCode.UNEXPECTED_END_OF_INPUT:
            specific_msg = self.t(
                f"{msg_key_prefix}unexpected_end_of_input",
                "Unexpected end of input on line {line} at column {column}",
                **msg_data,
            )
        elif exc.code == FltErrCode.EXPECTED_TOKEN:
            specific_msg = self.t(
                f"{msg_key_prefix}expected_token",
                "Expected {expected} on line {line} at column "
                "{column} but got {value}",
                **msg_data,
            )
        elif exc.code == FltErrCode.UNTERMINATED_STRING:
            specific_msg = self.t(
                f"{msg_key_prefix}unterminated_string",
                "Unterminated string on line {line} at column "
                "{column}: {value}",
                **msg_data,
            )
        elif exc.code == FltErrCode.UNMATCHED_BRACKETS:
            specific_msg = self.t(
                f"{msg_key_prefix}unmatched_brackets",
                "Unmatched brackets on line {line} at column {column}",
                **msg_data,
            )
        elif exc.code == FltErrCode.UNEXPECTED_CHAR:
            specific_msg = self.t(
                f"{msg_key_prefix}unexpected_char",
                "Unexpected character on line {line} at column "
                "{column}: {value}",
                **msg_data,
            )
        elif exc.code == FltErrCode.INVALID_INT_VALUE:
            specific_msg = self.t(
                f"{msg_key_prefix}invalid_int_value",
                # Truncated for brevity
                "Invalid integer value: {value} ...",
                **msg_data,
            )
        elif exc.code == FltErrCode.INVALID_FLOAT_VALUE:
            specific_msg = self.t(
                f"{msg_key_prefix}invalid_float_value",
                # Truncated for brevity
                "Invalid float value: {value} ...",
                **msg_data,
            )
        else:
            msg_data["err"] = str(exc)  # Ensure 'err' key for default template
            specific_msg = self.t(
                f"{msg_key_prefix}{err_code_str}",
                default_msg_template,
                **msg_data,
            )
        self.l_error.setText(specific_msg)
        self.errorChanged.emit(True)

    def update_highlighting(self) -> None:
        """Update the text highlighting based on current parser state."""
        self.blockSignals(True)
        cursor = self.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.setCharFormat(self.default_format)
        cursor.clearSelection()

        if self.parser is None or self.err_start != -1:
            if self.err_start != -1:
                error_cursor = QTextCursor(self.document())
                error_cursor.setPosition(self.err_start)
                error_cursor.movePosition(
                    QTextCursor.MoveOperation.End,
                    QTextCursor.MoveMode.KeepAnchor,
                )
                error_cursor.setCharFormat(self.error_format)

                valid_cursor = QTextCursor(self.document())
                valid_cursor.setPosition(self.err_start)
                valid_cursor.movePosition(
                    QTextCursor.MoveOperation.Start,
                    QTextCursor.MoveMode.KeepAnchor,
                )
                valid_cursor.setCharFormat(self.valid_format)
        else:
            if self.parser.tokens:
                for token in self.parser.tokens:
                    token_cursor = QTextCursor(self.document())
                    token_cursor.setPosition(token.start_index)
                    token_cursor.setPosition(
                        token.start_index + len(token.value),
                        QTextCursor.MoveMode.KeepAnchor,
                    )
                    token_cursor.setCharFormat(self._get_token_format(token))
        self.blockSignals(False)

    def _get_token_format(self, token: Token) -> QTextCharFormat:
        """Get the format for a specific token type."""
        value = token.value.upper()
        # Ensure field cache is populated for accurate field identification
        if not self.all_field_names_cache and self.qt_model:
            self.all_field_names_cache = sorted(
                [f.name for f in self.qt_model.filter_fields]
            )

        is_field_from_cache = token.value in self.all_field_names_cache

        if value in ("AND", "OR", "NOT"):
            return self.logic_format
        elif value in ("==", "!=", ">", ">=", "<", "<="):
            return self.op_format
        elif (
            value.startswith("'")
            and value.endswith("'")
            or value.isdigit()
            or (value.count(".") == 1 and value.replace(".", "").isdigit())
        ):  # Number or quoted string
            return self.value_format
        elif is_field_from_cache:  # Known field name from cache
            return self.field_format
        else:  # Fallback for potential undeclared fields or general identifiers
            # Check if it has characteristics of an identifier (not keyword,
            # not operator, not literal value)
            if re.match(r"^[a-zA-Z_][a-zA-Z0-9_.]*$", token.value) and not (
                value.isdigit()
                or (value.startswith("'") and value.endswith("'"))
            ):
                return (
                    self.field_format
                )  # Treat as potential field if it looks like one
            return self.default_format  # True fallback for unrecognized tokens

    @property
    def filter(self) -> Union[FilterType, None]:
        """Return the filter as a dictionary."""
        return self.check_document()
