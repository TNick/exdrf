"""Domain-specific language for parsing label expressions.

The expression always starts with an open parenthesis and ends with a close
parenthesis. Nested statements are also surrounded by parentheses. The first
element in the expression is the operator, and the rest are its arguments.
Strings are surrounded by double quotes. Other identifiers are treated as
properties of the SQLAlchemy model instance.

You can use this DSL to associate labels with Resources.

Examples:

```
(concat first_name " " last_name)
(if (upper name) "Yes" "No")
(concat (upper first_name) (lower last_name))
(concat (upper name.first) (lower name.last))
(is_none attrib "Is none" "Is not none")
```
"""

import re
from typing import Any, Dict, List, Literal, Union, cast

from attrs import define, field

ASTNode = Union[
    "ParsedOp", "ParsedLiteral", "ParsedIdentifier", List["ASTNode"]
]

# \s*: This part matches zero or more whitespace characters.
# (\(|\)|\"[^\"]*\"|[^\s()]+): This is the main capturing group, enclosed
# in parentheses (). It uses the | operator (logical OR) to match one of
# four possible patterns:
#   \(: Matches an opening parenthesis (.
#   \): Matches a closing parenthesis ).
#   \"[^\"]*\": Matches a double-quoted string.
#   [^\s()]+: Matches one or more characters that are not whitespace (\s),
#       an opening parenthesis (, or a closing parenthesis ).
#       The + quantifier ensures that at least one such character is matched.
#       This is useful for capturing standalone tokens or words.
token_pattern = re.compile(r"\s*(" r"\(|\)|\"[^\"]*\"|" r"[^\s()]+" ")")

# Simple regex patterns to match integers.
int_pattern = re.compile(r"^\d+$")

# Simple regex patterns to match floats.
float_pattern = re.compile(r"^\d+\.\d+$")


class Null:
    """A class to represent a null value."""


@define(eq=False)
class Parsed:
    """Base class for parsed elements in the AST.

    Attributes:
        value: The string value of the parsed element.
    """

    value: str

    def __str__(self) -> str:
        return self.value

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Parsed):
            return self.value == other.value
        elif isinstance(other, str):
            return self.value == other
        return False


@define(eq=False)
class ParsedOp(Parsed):
    """Parsed operator in the AST.

    This is the first element of an expression and indicates the operation to
    be performed on the subsequent elements.
    """


@define(eq=False)
class ParsedLiteral(Parsed):
    """Parsed literal in the AST.

    Arguments can be either literals (this class) or identifiers. The literals
    can be strings (denoted by double quotes), integers, or floats.

    Attributes:
        type: The type of the literal (string, int, float).
    """

    type: Literal["string", "int", "float"] = field(default="string")

    @property
    def as_string(self) -> str:
        """The value ass it can be used in a string representation.

        Strings are double-quoted, numbers are inserted as they are.
        """
        if self.type == "string":
            return f'"{self.value}"'
        else:
            return self.value

    @property
    def raw_value(self) -> Any:
        """Python value representation.

        Strings are returned as they are (we store strings), numbers
        are converted to integers or reals.
        """
        if self.type == "string":
            return self.value
        elif self.type == "int":
            return int(self.value)
        elif self.type == "float":
            return float(self.value)
        else:
            raise ValueError(f"Unknown type: {self.type}")


@define(eq=False)
class ParsedIdentifier(Parsed):
    """Parsed identifier in the AST.

    The identifier is a type of argument that can retrieve the actual value
    from the resource.
    """

    def retrieve(self, context: Any) -> Any:
        """Retrieve the value of the identifier from the context.

        Args:
            context: The context in which to evaluate the expression.
        """
        parts = self.value.split(".")
        attr = context

        if isinstance(attr, dict):
            for part in parts:
                attr = attr.get(part, Null)
                if attr is Null:
                    raise AttributeError(f"Value `{part}` not found in {attr}")
        else:
            for part in parts:
                attr = getattr(attr, part, Null)
                if attr is Null:
                    raise AttributeError(
                        f"Attribute `{part}` not found in {attr}"
                    )
        return attr


@define
class Operation:
    """Base class for operations in the DSL.

    The ParsedOp will end up an instance of this class, which will be used to
    evaluate the expression.

    Attributes:
        key: The key that identifies the operation.
    """

    key: str

    def evaluate(self, *args) -> str:
        """Evaluate the operation online with the given arguments."""
        raise NotImplementedError("Subclasses should implement this!")

    def to_python(self, *args) -> str:
        """Generate Python code for the operation."""
        raise NotImplementedError("Subclasses should implement this!")

    def to_typescript(self, *args) -> str:
        """Generate TypeScript code for the operation."""
        raise NotImplementedError("Subclasses should implement this!")


@define
class Concat(Operation):
    """Concatenate strings together.

    Example:
        (concat first_name " " last_name) -> "John Doe"
    """

    key: str = field(default="concat", init=False)

    def evaluate(self, *args) -> Any:
        return "".join(map(str, args))

    def to_python(self, *args) -> str:
        return " + ".join(args)

    def to_typescript(self, *args) -> str:
        return " + ".join(args)


@define
class If(Operation):
    """If statement.

    Example:
        (if (upper name) "Yes" "No") -> "Yes" if name is upper, else "No"
    """

    key: str = field(default="if", init=False)

    def evaluate(self, *args) -> Any:
        assert len(args) == 3, "If operation takes three arguments"
        cond, a, b = args
        return a if cond else b

    def to_python(self, *args) -> str:
        assert len(args) == 3, "If operation takes three arguments"
        cond, a, b = args
        return f"({a} if {cond} else {b})"

    def to_typescript(self, *args) -> str:
        assert len(args) == 3, "If operation takes three arguments"
        cond, a, b = args
        return f"({cond} ? {a} : {b})"


@define
class Upper(Operation):
    """Convert string to upper case.

    Example:
        (upper name) -> "JOHN DOE"
    """

    key: str = field(default="upper", init=False)

    def evaluate(self, *args) -> Any:
        assert len(args) == 1, "Upper operation takes one argument"
        (s,) = args
        return str(s).upper()

    def to_python(self, *args) -> str:
        assert len(args) == 1, "Upper operation takes one argument"
        (s,) = args
        return f"str({s}).upper()"

    def to_typescript(self, *args) -> str:
        assert len(args) == 1, "Upper operation takes one argument"
        (s,) = args
        return f"String({s}).toUpperCase()"


@define
class Lower(Operation):
    """Convert string to lower case.

    Example:
        (lower name) -> "john doe"
    """

    key: str = field(default="lower", init=False)

    def evaluate(self, *args) -> Any:
        assert len(args) == 1, "Lower operation takes one argument"
        (s,) = args
        return str(s).lower()

    def to_python(self, *args) -> str:
        assert len(args) == 1, "Lower operation takes one argument"
        (s,) = args
        return f"str({s}).lower()"

    def to_typescript(self, *args) -> str:
        assert len(args) == 1, "Lower operation takes one argument"
        (s,) = args
        return f"String({s}).toLowerCase()"


@define
class IsNone(Operation):
    """Check if the first argument is None.

    Example:
        (is_none attrib "Is none" "Is not none") -> "Is none"
    """

    key: str = field(default="is_none", init=False)

    def evaluate(self, *args) -> Any:
        assert len(args) == 3, "IsNone operation takes three arguments"
        cond, a, b = args
        return a if cond is None else b

    def to_python(self, *args) -> str:
        assert len(args) == 3, "IsNone operation takes three arguments"
        cond, a, b = args
        return f"({a} if {cond} is None else {b})"

    def to_typescript(self, *args) -> str:
        assert len(args) == 3, "IsNone operation takes three arguments"
        cond, a, b = args
        return f"(({cond} == null || {cond} == undefined) ? {a} : {b})"


@define
class Equals(Operation):
    """Check if the first argument is equal to the second.

    Example:
        (= name "John Doe" "Yes" "No") -> "Yes"
    """

    key: str = field(default="=", init=False)

    def evaluate(self, *args) -> Any:
        assert len(args) == 4, "Equals operation takes four arguments"
        cond1, cond2, a, b = args
        return a if cond1 == cond2 else b

    def to_python(self, *args) -> str:
        assert len(args) == 4, "Equals operation takes four arguments"
        cond1, cond2, a, b = args
        return f"({a} if {cond1} == {cond2} else {b})"

    def to_typescript(self, *args) -> str:
        assert len(args) == 4, "Equals operation takes four arguments"
        cond1, cond2, a, b = args
        return f"(({cond1} == {cond2}) ? {a} : {b})"


@define
class DateStr(Operation):
    """Convert date to string using strftime.

    Note that this relies on the existence of a strftime method
    on the date class in javascript, which is not standard.

    Example:
        (date_str date "%Y-%m-%d") -> "2023-10-01"
    """

    key: str = field(default="date_str", init=False)

    def evaluate(self, *args) -> Any:
        assert len(args) == 2, "DateStr operation takes two arguments"
        date, format = args
        return date.strftime(format)

    def to_python(self, *args) -> str:
        assert len(args) == 2, "DateStr operation takes two arguments"
        date, format = args
        return f"({date}.strftime({format}))"

    def to_typescript(self, *args) -> str:
        assert len(args) == 2, "DateStr operation takes two arguments"
        date, format = args
        return f"({date}.strftime({format}))"


@define
class FloatStr(Operation):
    """Convert float to string with specified number of digits.

    Example:
        (float_str number digits) -> "123.45"
    """

    key: str = field(default="float_str", init=False)

    def evaluate(self, *args) -> Any:
        assert len(args) == 2, "FloatStr operation takes two arguments"
        number, digits = args
        return ("{:." + str(digits) + "f}").format(number)

    def to_python(self, *args) -> str:
        assert len(args) == 2, "FloatStr operation takes two arguments"
        number, digits = args
        return (
            '("{:." + str('
            + str(digits)
            + ') + "f}").format('
            + str(number)
            + ")"
        )

    def to_typescript(self, *args) -> str:
        assert len(args) == 2, "FloatStr operation takes two arguments"
        number, digits = args
        return (
            f"({number})."
            "toLocaleString('en-US', { "
            f"minimumFractionDigits: {digits}, "
            f"maximumFractionDigits: {digits}"
            "});"
        )


@define
class IntStr(Operation):
    """Convert int to string with thousands separator.

    Example:
        (int_str number) -> "1,234,567"
    """

    key: str = field(default="int_str", init=False)

    def evaluate(self, *args) -> Any:
        assert len(args) == 1, "IntStr operation takes one argument"
        (number,) = args
        return "{:,}".format(number)

    def to_python(self, *args) -> str:
        assert len(args) == 1, "IntStr operation takes one argument"
        (number,) = args
        return '("{:,}").format({' + str(number) + "})"

    def to_typescript(self, *args) -> str:
        assert len(args) == 1, "IntStr operation takes one argument"
        (number,) = args
        return (
            f"({number})."
            "toLocaleString('en-US', { "
            "minimumFractionDigits: 0, "
            "maximumFractionDigits: 0"
            "});"
        )


ops: Dict[str, Operation] = {
    "concat": Concat(),
    "if": If(),
    "upper": Upper(),
    "lower": Lower(),
    "is_none": IsNone(),
    "=": Equals(),
    "date_str": DateStr(),
    "float_str": FloatStr(),
    "int_str": IntStr(),
}


def parse_expr(expr: str) -> ASTNode:
    """Parses the label expression string into an AST.

    Supports nested expressions like: (if (upper name) "Yes" "No")
    """

    # Tokenize: parentheses, quoted strings, or other tokens
    tokens = re.findall(token_pattern, expr)

    def parse_tokens(tokens):
        if not tokens:
            raise SyntaxError("Unexpected EOF while reading")

        token = tokens.pop(0)

        if token == "(":
            lst = []
            try:
                op_token = tokens.pop(0)
                if not isinstance(op_token, str):
                    raise SyntaxError("Expected operator after `(`")
                lst.append(ParsedOp(op_token))

                while tokens[0] != ")":
                    lst.append(parse_tokens(tokens))
            except IndexError:
                raise SyntaxError("Unexpected EOF while expecting `)`")
            tokens.pop(0)  # Remove ')'
            return lst

        elif token == ")":
            raise SyntaxError("Unexpected )")

        elif token.startswith('"') and token.endswith('"'):
            return ParsedLiteral(token[1:-1])  # Remove surrounding quotes

        elif int_pattern.match(token):
            return ParsedLiteral(token, type="int")

        elif float_pattern.match(token):
            return ParsedLiteral(token, type="float")

        else:
            return ParsedIdentifier(token)

    ast = parse_tokens(tokens)
    if tokens:
        raise SyntaxError("Unexpected tokens after parsing")
    return ast


def _eval_op(op: ParsedOp, args: List[Any]) -> Any:
    """Evaluate the operator with the given arguments.

    Args:
        op: The operator to evaluate.
        args: The arguments to the operator.
    Returns:
        The result of the evaluation.
    """
    if op.value not in ops:
        raise ValueError(f"Unknown operator: {op}")
    return ops[op.value].evaluate(*args)


def evaluate(ast_node: ASTNode, context: Any) -> Any:
    """Evaluate the parsed AST in the context of a Resource instance.

    The context is usually a SQLAlchemy model instance. The function will
    replace identifiers with their values from the context and evaluate the
    expression.

    For example, if the context has a field `name`, and the AST is `["upper",
    "name"]`, the function will return `context.name.upper()`.

    Args:
        ast_node: The parsed AST node.
        context: The context in which to evaluate the expression.

    Returns:
        The result of the evaluation.
    """
    if isinstance(ast_node, ParsedIdentifier):
        return ast_node.retrieve(context)

    elif isinstance(ast_node, ParsedLiteral):
        return ast_node.raw_value

    elif isinstance(ast_node, list):
        op = cast(ParsedOp, ast_node[0])
        assert isinstance(op, ParsedOp), "First element must be an operator"
        args = [evaluate(arg, context) for arg in ast_node[1:]]
        return _eval_op(op, args)


def generate_python_code(ast_node: ASTNode) -> Any:
    """Generate Python code from the AST.

    This function traverses the AST and generates Python code that can be
    used to evaluate the expression.

    Args:
        ast_node: The parsed AST node.

    Returns:
        The generated Python code as a string.
    """
    if isinstance(ast_node, ParsedLiteral):
        return ast_node.as_string

    elif isinstance(ast_node, ParsedIdentifier):
        return f"instance.{ast_node}"

    elif isinstance(ast_node, list):
        op = cast(ParsedOp, ast_node[0])
        args = [generate_python_code(arg) for arg in ast_node[1:]]
        op_class = ops.get(op.value)
        if op_class:
            return op_class.to_python(*args)
        else:
            raise ValueError(f"Unsupported operator: {op}")


def generate_typescript_code(ast_node: ASTNode) -> Any:
    """Generate TypeScript code from the AST.

    Args:
        ast_node: The parsed AST node.

    Returns:
        The generated TypeScript code as a string.
    """
    if isinstance(ast_node, ParsedIdentifier):
        return f"instance.{ast_node}"

    elif isinstance(ast_node, ParsedLiteral):
        return ast_node.as_string

    elif isinstance(ast_node, list):
        op = cast(ParsedOp, ast_node[0])
        args = [generate_typescript_code(arg) for arg in ast_node[1:]]
        op_class = ops.get(op.value)
        if op_class:
            return op_class.to_typescript(*args)
        else:
            raise ValueError(f"Unsupported operator: {op}")


def get_used_fields(ast: ASTNode) -> List[str]:
    """Get the list of fields used in the AST.

    This function traverses the AST and collects all identifiers that are
    valid Python identifiers. It returns a sorted list of these identifiers.

    Args:
        ast: The parsed AST node.

    Returns:
        A sorted list of field names used in the AST.
    """
    fields = set()

    def walk(node):
        if isinstance(node, ParsedIdentifier):
            fields.add(node.value)
        elif isinstance(node, list):
            # skip operator
            for sub in node[1:]:
                walk(sub)

    walk(ast)
    return sorted(fields)
