import re
from bisect import bisect_right
from collections import namedtuple
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Generic, List, Optional, Union, cast

from attrs import define, field
from exdrf_qt.context_use import QtUseContext
from exdrf_qt.models.model import DBM, QtModel  # noqa: F401

from exdrf.filter import FieldFilter, FilterType

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401


class FltErrCode(StrEnum):
    UNTERMINATED_STRING = "unterminated_string"
    UNMATCHED_BRACKETS = "unmatched_brackets"
    UNEXPECTED_CHAR = "unexpected_char"
    EXPECTED_TOKEN = "expected_token"
    UNEXPECTED_END_OF_INPUT = "unexpected_end_of_input"
    INVALID_INT_VALUE = "invalid_int_value"
    INVALID_FLOAT_VALUE = "invalid_float_value"
    UNKNOWN_FIELD = "unknown_field"
    UNKNOWN_OPERATION = "unknown_operation"
    INVALID_VALUE_TYPE = "invalid_value_type"


class FltSyntaxError(Exception):
    """A syntax error in the DSL.

    Attributes:
        code: The error code.
        lineno: The 1-based line number.
        column: The 1-based column number inside the line.
        offset: The 0-based offset from thee start of the string.
        end_offset: The 0-based end offset.
        text: The text.
    """

    code: FltErrCode
    lineno: int
    offset: int
    end_offset: int
    text: str
    value: Optional[str] = None
    expected: Optional[str] = None

    def __init__(
        self,
        msg: str,
        code: FltErrCode,
        text: str,
        lineno: int,
        column: int,
        offset: int,
        end_offset: int = -1,
        value: Optional[str] = None,
        expected: Optional[str] = None,
    ):
        super().__init__(msg)
        self.code = code
        self.source = text
        self.lineno = lineno
        self.column = column
        self.offset = offset
        self.end_offset = (
            end_offset if end_offset != -1 else (len(text) - offset)
        )
        self.value = value
        self.expected = expected

    def as_dict(self) -> dict:
        return {
            "code": self.code,
            "source": self.source,
            "line": self.lineno,
            "column": self.column,
            "offset": self.offset,
            "end": self.end_offset,
            "value": self.value,
            "expected": self.expected,
        }


@define
class Token:
    """A token from the DSL.

    A token can have one of these values:
    - `AND`, `OR`, `NOT` - these are the logic operators,
    - `(` and `)` - these are the grouping operators,
    - a field name consisting of parts separated by dots,
    - a comparison operator: `==`, `!=`, `>`, `>=`, `<`, `<=`,
    - a field value.

    Attributes:
        value: The value of the token.
        line: The 0-based line number of the token.
        column: The 0-based column number of the token.
        index: The 0-based index of the end of the token in the original string.
    """

    value: str
    line: int
    column: int
    index: int

    @property
    def start_index(self) -> int:
        """The 0-based index of the start of the token in the original string.

        Returns:
            The 0-based index of the start of the token in the original string.
        """
        return self.index - len(self.value)


@define
class ParsedElement:
    """A parsed element.

    This is the common base class for logic operators and field filters.
    """


@define
class ParsedFieldFilter(FieldFilter, ParsedElement):
    """A parsed field filter.

    Attributes:
        fld: The field to filter by.z
        op: The operation to perform.
        vl: The value to compare against.
        tk_fld: The token for the field name.
        tk_op: The token for the operation.
        tk_val: The token for the value.
    """

    tk_fld: Token
    tk_op: Token
    tk_val: Token


@define
class ParsedLogic(ParsedElement):
    """Base class for parsed logic operators.

    Attributes:
        tk_op: The token for the operation.
    """

    tk_op: Token


@define
class ParsedLogicAnd(ParsedLogic):
    """A parsed logic and.

    Attributes:
        op: The operation to perform.
        items: The items to perform the operation on.
    """

    items: List[ParsedFieldFilter]


@define
class ParsedLogicOr(ParsedLogic):
    """A parsed logic or.

    Attributes:
        op: The operation to perform.
        items: The items to perform the operation on.
    """

    items: List[ParsedFieldFilter]


@define
class ParsedLogicNot(ParsedLogic):
    """A parsed logic not.

    Attributes:
        op: The operation to perform.
        items: The items to perform the operation on.
    """

    item: ParsedFieldFilter


@define
class DSLTokenizer:
    """A tokenizer for the DSL.

    Attributes:
        text: The text to tokenize.
        pos: The current position in the text.
        line: The current line number.
        col: The current column number.
    """

    text: str
    pos: int = 0
    line: int = 1
    col: int = 1

    def _advance(self, count: int = 1):
        """Advance the position by the given count.

        Args:
            count: The number of characters to advance.
        """

        for _ in range(count):
            if self.pos < len(self.text):
                if self.text[self.pos] == "\n":
                    self.line += 1
                    self.col = 1
                else:
                    self.col += 1
                self.pos += 1

    def _match(self, pattern: str) -> Optional[re.Match]:
        """Match a pattern at the current position.

        Args:
            pattern: The pattern to match.

        Returns:
            The match if found, otherwise None.
        """
        return re.match(pattern, self.text[self.pos :])  # noqa: E203

    def _skip_whitespace(self):
        """Skip whitespace at the current position.

        This is a helper method for the `next_token` method.
        """

        while self.pos < len(self.text) and self.text[self.pos].isspace():
            self._advance()

    def next_token(self) -> Optional[Token]:
        """Get the next token from the text.

        Returns:
            The next token, or None if the end of the text is reached.
        """

        # Skip whitespace.
        self._skip_whitespace()

        # If we've reached the end of the text, return None
        if self.pos >= len(self.text):
            return None

        # Get the current character
        ch = self.text[self.pos]
        start_line, start_col = self.line, self.col

        # If the current character is a parenthesis or comma, return a token
        if ch in "(),":
            self._advance()
            return Token(ch, start_line, start_col, self.pos)

        # If the current character is a single quote, return a string token
        if ch == "'":
            end_pos = self.pos + 1
            while end_pos < len(self.text) and self.text[end_pos] != "'":
                if self.text[end_pos] == "\\" and end_pos + 1 < len(self.text):
                    end_pos += 2
                else:
                    end_pos += 1
            if end_pos >= len(self.text) or self.text[end_pos] != "'":
                raise FltSyntaxError(
                    msg=(
                        f"Unterminated string at line {start_line} "
                        f"col {start_col}"
                    ),
                    code=FltErrCode.UNTERMINATED_STRING,
                    text=self.text,
                    lineno=start_line,
                    column=start_col,
                    offset=self.pos,
                    end_offset=end_pos,
                    value=self.text[self.pos : end_pos + 1],  # noqa: E203
                )
            token_value = self.text[self.pos : end_pos + 1]  # noqa: E203
            self._advance(len(token_value))
            return Token(token_value, start_line, start_col, self.pos)

        # If the current character is a bracket, return a bracket token.
        if ch == "[":
            end_pos = self.pos
            bracket_level = 0
            while end_pos < len(self.text):
                if self.text[end_pos] == "[":
                    bracket_level += 1
                elif self.text[end_pos] == "]":
                    bracket_level -= 1
                    if bracket_level == 0:
                        break
                end_pos += 1
            if bracket_level != 0:
                raise FltSyntaxError(
                    msg=(
                        f"Unmatched brackets at line {start_line} "
                        f"col {start_col}"
                    ),
                    code=FltErrCode.UNMATCHED_BRACKETS,
                    text=self.text,
                    lineno=start_line,
                    column=start_col,
                    offset=self.pos,
                    end_offset=end_pos,
                    value=self.text[self.pos : end_pos + 1],  # noqa: E203
                )
            token_value = self.text[self.pos : end_pos + 1]  # noqa: E203
            self._advance(len(token_value))
            return Token(token_value, start_line, start_col, self.pos)

        # If the current character is a letter, number, or underscore, return a
        # word token.
        match = self._match(r"[A-Za-z_][A-Za-z0-9_.]*")
        if match:
            token_value = match.group(0)
            self._advance(len(token_value))
            return Token(token_value, start_line, start_col, self.pos)

        # If the current character is a number, return a number token
        match = self._match(r"\d+(\.\d+)?")
        if match:
            token_value = match.group(0)
            self._advance(len(token_value))
            return Token(token_value, start_line, start_col, self.pos)

        # See if this is an operation
        match = self._match(r"==|!=|>=|<=|>|<")
        if match:
            token_value = match.group(0)
            self._advance(len(token_value))
            return Token(token_value, start_line, start_col, self.pos)

        raise FltSyntaxError(
            msg=(
                f"Unexpected character '{ch}' at line {start_line} "
                f"col {start_col}"
            ),
            code=FltErrCode.UNEXPECTED_CHAR,
            text=self.text,
            lineno=start_line,
            column=start_col,
            offset=self.pos,
            value=ch,
        )

    def tokenize(self) -> List[Token]:
        """Tokenize the text.

        Returns:
            A list of tokens.
        """

        tokens = []
        while self.pos < len(self.text):
            token = self.next_token()
            if token:
                tokens.append(token)
        return tokens


def infer_value_type(value: Any) -> str:
    """Infer the type of a value.

    Args:
        value: The value to infer the type of.

    Returns:
        The type of the value.
    """
    if isinstance(value, str):
        return "string"
    elif isinstance(value, bool):
        return "unknown"
    elif isinstance(value, (int, float)):
        return "number"
    elif isinstance(value, list):
        return "list"
    return "unknown"


@define
class FieldValidator(QtUseContext, Generic[DBM]):
    """Validate fields in the DSL.

    Attributes:
        field_map: A dictionary of fields.
    """

    ctx: "QtContext"
    qt_model: "QtModel[DBM]"

    def validate(
        self,
        parser: "DSLParser",
        field: ParsedFieldFilter,
        token: Optional[Token] = None,
    ):
        """Validate a field.

        Args:
            field: The field to validate.
            token: The token.
        """
        for fld in self.qt_model.filter_fields:
            if fld.name == field.fld:
                return
        raise FltSyntaxError(
            msg=f"Unknown field: {field.fld}",
            code=FltErrCode.UNKNOWN_FIELD,
            text=parser.src_text,
            lineno=token.line if token else 0,
            column=token.column if token else 0,
            offset=token.index if token else 0,
            end_offset=(token.index + len(field.fld)) if token else 0,
            value=field.fld,
            expected=", ".join([f.name for f in self.qt_model.filter_fields]),
        )


@define
class DSLParser:
    """Parse the DSL.

    Attributes:
        tokens: The tokens to parse.
        index: The current index in the tokens.
    """

    src_text: str
    tokens: List[Token]
    index: int
    last_error: Optional[FltSyntaxError] = field(default=None, init=False)

    @property
    def last_token(self) -> Optional[Token]:
        """Get the last token.

        Returns:
            The last token, or None if there are no tokens.
        """
        return self.tokens[-1] if self.tokens else None

    @property
    def last_line(self) -> int:
        """Get the last line number.

        Returns:
            The last line number.
        """
        if len(self.tokens) == 0:
            return 0
        return self.tokens[-1].line

    def current(self) -> Optional[Token]:
        """Get the current token.

        Returns:
            The current token, or None if the end of the tokens is reached.
        """
        return (
            self.tokens[self.index] if self.index < len(self.tokens) else None
        )

    def match(self, expected: str) -> Token:
        """Match the expected token.

        Args:
            expected: The expected token.

        Returns:
            The matched token.
        """
        tok = self.current()
        if not tok:
            last = self.last_token
            raise FltSyntaxError(
                msg=(f"Expected '{expected}', but got end of input"),
                code=FltErrCode.EXPECTED_TOKEN,
                text=self.src_text,
                lineno=self.last_line,
                column=last.column if last else 0,
                offset=last.index if last else 0,
                expected=expected,
            )
        if tok.value.lower() != expected.lower():
            raise FltSyntaxError(
                msg=(f"Expected '{expected}', but got '{tok.value}'"),
                code=FltErrCode.EXPECTED_TOKEN,
                text=self.src_text,
                lineno=tok.line,
                column=tok.column,
                offset=tok.index,
                value=expected,
                expected=expected,
            )
        self.index += 1
        return tok

    def match_any(self, expected: str) -> Token:
        """Match any token.

        Returns:
            The matched token.
        """
        tok = self.current()
        if tok is None:
            last = self.last_token
            err = FltSyntaxError(
                msg=(f"Expected <{expected}>, but got end of input"),
                code=FltErrCode.EXPECTED_TOKEN,
                text=self.src_text,
                lineno=self.last_line,
                column=last.column if last else 0,
                offset=last.index if last else 0,
            )
            self.last_error = err
            raise err
        self.index += 1
        return tok

    def parse(self) -> List[Union[ParsedFieldFilter, ParsedLogic]]:
        """Parse the DSL.

        Returns:
            The parsed filter.
        """
        self.last_error = None  # Clear previous error
        result = []
        tok = self.current()
        while tok:
            try:
                result.extend(self.parse_expression())
            except FltSyntaxError as e:
                self.last_error = e
                raise e
            tok = self.current()
            if tok and tok.value == ",":
                self.index += 1
        return result

    def parse_expression(self) -> List[Union[ParsedFieldFilter, ParsedLogic]]:
        """Parse an expression.

        Returns:
            The parsed filter.
        """
        tok = self.current()
        if tok is None:
            last = self.last_token
            raise FltSyntaxError(
                msg=("Unexpected end of input"),
                code=FltErrCode.UNEXPECTED_END_OF_INPUT,
                text=self.src_text,
                lineno=self.last_line,
                column=last.column if last else 0,
                offset=last.index if last else 0,
            )
        value = tok.value.upper()
        if value in ("AND", "OR"):
            return [self.parse_logic(tok)]
        elif value == "NOT":
            return [self.parse_not()]
        else:
            return [self.parse_field_expr()]

    def parse_logic(self, op: Token) -> ParsedLogic:
        """Parse a logic expression.

        Args:
            op: The operator.

        Returns:
            The parsed filter.
        """
        op_str = op.value.upper()
        self.match(op_str)
        self.match("(")
        items = []
        while True:
            tok = self.current()
            if not tok:
                break
            if tok.value == ")":
                break
            items.extend(self.parse_expression())
            tok = self.current()
            if tok and tok.value == ",":
                self.match(",")
        self.match(")")
        if op_str == "AND":
            return ParsedLogicAnd(
                tk_op=op, items=cast(List[ParsedFieldFilter], items)
            )
        elif op_str == "OR":
            return ParsedLogicOr(
                tk_op=op, items=cast(List[ParsedFieldFilter], items)
            )
        else:
            raise ValueError(f"Unknown operator: {op}")

    def parse_not(self) -> ParsedLogic:
        """Parse a not expression.

        Returns:
            The parsed filter.
        """
        op = self.match("NOT")
        self.match("(")
        expr = self.parse_field_expr()
        self.match(")")
        return ParsedLogicNot(tk_op=op, item=expr)

    def parse_field_expr(self) -> ParsedFieldFilter:
        """Parse a field expression.

        Returns:
            The parsed filter.
        """
        fld_tok = self.match_any("identifier")
        op_tok = self.match_any("operator")
        val_tok = self.match_any("value")
        val = self.parse_value(val_tok)
        ff = ParsedFieldFilter(
            fld=fld_tok.value,
            op=op_tok.value,
            vl=val,
            tk_fld=fld_tok,
            tk_op=op_tok,
            tk_val=val_tok,
        )
        return ff

    def parse_value(self, tok: Token) -> Any:
        """Parse a value.

        Args:
            raw: The raw value.

        Returns:
            The parsed value.
        """
        raw = tok.value
        if raw.startswith("'") and raw.endswith("'"):
            return raw[1:-1]
        elif raw.startswith("[") and raw.endswith("]"):
            items = raw[1:-1].split(",")
            return [item.strip().strip("'") for item in items if item.strip()]
        elif "." in raw:
            try:
                return float(raw)
            except ValueError:
                err = FltSyntaxError(
                    msg=(
                        f"Invalid float value: {raw} (expected because "
                        "string has decimal point)"
                    ),
                    code=FltErrCode.INVALID_FLOAT_VALUE,
                    text=self.src_text,
                    lineno=tok.line,
                    column=tok.column,
                    offset=tok.index,
                    end_offset=tok.index,
                    value=raw,
                )
                self.last_error = err
                raise err
        else:
            try:
                return int(raw)
            except ValueError:
                err = FltSyntaxError(
                    msg=(
                        f"Invalid integer value: {raw} (expected because "
                        "this is the last valid choice)"
                    ),
                    code=FltErrCode.INVALID_INT_VALUE,
                    text=self.src_text,
                    lineno=tok.line,
                    column=tok.column,
                    offset=tok.index,
                    end_offset=tok.index,
                    value=raw,
                )
                self.last_error = err
                raise err


@define
class DSLParserWithValidation(DSLParser):
    """Parse the DSL with validation.

    Attributes:
        validator: The validator.
    """

    validator: FieldValidator

    def parse_field_expr(self) -> ParsedFieldFilter:
        """Parse a field expression.

        Returns:
            The parsed filter.
        """
        fld_tok = self.match_any("identifier")
        op_tok = self.match_any("operator")
        val_tok = self.match_any("value")
        val = self.parse_value(val_tok)
        ff = ParsedFieldFilter(
            fld=fld_tok.value,
            op=op_tok.value,
            vl=val,
            tk_fld=fld_tok,
            tk_op=op_tok,
            tk_val=val_tok,
        )
        self.validator.validate(self, ff, fld_tok)
        return ff


def serialize_filter(obj: Any) -> FilterType:
    """Serialize a filter.

    Args:
        obj: The filter to serialize.

    Returns:
        The serialized filter.
    """
    if isinstance(obj, ParsedFieldFilter):
        return cast(
            FilterType,
            {"fld": obj.fld, "op": obj.op, "vl": obj.vl},
        )

    elif isinstance(obj, ParsedLogic):
        if obj.tk_op.value == "NOT":
            obj = cast(ParsedLogicNot, obj)
            return cast(
                FilterType,
                [obj.tk_op.value, serialize_filter(obj.item)],
            )
        else:
            obj = cast(ParsedLogicAnd, obj)
            return cast(
                FilterType,
                [obj.tk_op.value, [serialize_filter(e) for e in obj.items]],
            )

    elif isinstance(obj, list):
        return cast(
            FilterType,
            [serialize_filter(e) for e in obj],
        )

    else:
        raise ValueError(f"Unknown object type: {type(obj)}")


def raw_filter_to_text(filter: Union[FilterType, FieldFilter]) -> str:
    """Convert a raw filter to a text string.

    Args:
        filter: The filter to convert.

    Returns:
        The filter as a string.
    """
    result = ""

    def do_part(part: Any, indent=0) -> None:
        nonlocal result
        prefix = "\t" * indent
        if isinstance(part, list):
            if len(part) == 0:
                return

            if isinstance(part[0], str):
                op_name = part[0].lower()
                if len(part) != 2:
                    raise ValueError(
                        f"The logic operator list expects two elements. "
                        f"Got {part}"
                    )
                if not isinstance(part[1], list):
                    raise ValueError(
                        f"The logic operator list expects a list as the second "
                        f"element. Got {part}"
                    )
                op_name = part[0].lower()
                if op_name == "and":
                    result += prefix + "AND (\n"
                elif op_name == "or":
                    result += prefix + "OR (\n"
                elif op_name == "not":
                    result += prefix + "NOT (\n"
                else:
                    raise ValueError(f"Invalid logic operator: {op_name}")

                do_part(part[1:], indent + 1)

                result += prefix + ")\n"
                return

            for item in part:
                do_part(item, indent)
        elif isinstance(part, dict):
            result += prefix + f"{part['fld']} {part['op']} {part['vl']}\n"
        else:
            raise ValueError(f"Invalid filter part: {part}")

    # Get rid of the outer AND layer if present.
    if (
        isinstance(filter, list)
        and len(filter) == 2
        and isinstance(filter[0], str)
        and filter[0].upper() == "AND"
        and isinstance(filter[1], list)
    ):
        do_part(cast(FilterType, filter)[1])
    else:
        do_part(filter)
    return result


# Define a namedtuple for our index entries.
IndexEntry = namedtuple("IndexEntry", ["start", "end", "element"])


@define
class Index:
    """An index of parsed elements.

    Attributes:
        index: The index.
    """

    index: List[IndexEntry] = field(factory=list)

    def add_to_index(self, token: Token, element: ParsedElement):
        self.index.append(IndexEntry(token.start_index, token.index, element))

    def build_index(self, element: Union[ParsedElement, List[ParsedElement]]):
        if isinstance(element, ParsedFieldFilter):
            for token in (element.tk_fld, element.tk_op, element.tk_val):
                self.add_to_index(token, element)

        elif isinstance(element, ParsedLogicNot):
            self.add_to_index(element.tk_op, element)
            self.build_index(element.item)

        elif isinstance(element, (ParsedLogicAnd, ParsedLogicOr)):
            self.add_to_index(element.tk_op, element)
            for item in element.items:
                self.build_index(item)

        elif isinstance(element, list):
            for item in cast(list, element):
                self.build_index(item)

    def find_element(self, position):
        i = bisect_right(self.index, position, key=lambda x: x.start) - 1
        if i >= 0 and self.index[i].start <= position < self.index[i].end:
            return self.index[i].element
        return None

    @classmethod
    def create(cls, parsed: Union[ParsedElement, List[ParsedElement]]):
        result = cls()
        result.build_index(parsed)

        # Sort the index by start position
        result.index.sort(key=lambda x: x.start)

        return result
