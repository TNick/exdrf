from datetime import datetime

import pytest

from exdrf.label_dsl import (
    ParsedIdentifier,
    ParsedLiteral,
    ParsedOp,
    evaluate,
    generate_python_code,
    generate_typescript_code,
    get_used_fields,
    parse_expr,
)


class DummyContext:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


def test_parse_expr_concat():
    expr = '(concat "Hello" "World")'
    ast = parse_expr(expr)
    # Check that the AST is a list starting with an operator
    assert isinstance(ast, list)
    op = ast[0]
    assert isinstance(op, ParsedOp)
    assert op.value == "concat"
    # Remaining tokens should be literals
    lit1 = ast[1]
    lit2 = ast[2]
    assert isinstance(lit1, ParsedLiteral)
    assert lit1.value == "Hello"
    assert isinstance(lit2, ParsedLiteral)
    assert lit2.value == "World"


def test_evaluate_concat_literals():
    expr = '(concat "Hello" " " "World")'
    ast = parse_expr(expr)
    # All arguments are literals so context is not used (pass None)
    result = evaluate(ast, None)
    assert result == "Hello World"


def test_evaluate_identifier_with_upper():
    expr = "(upper name)"
    ast = parse_expr(expr)
    context = DummyContext(name="test")
    result = evaluate(ast, context)
    assert result == "TEST"


def test_generate_python_code():
    expr = '(concat "foo" "bar")'
    ast = parse_expr(expr)
    code = generate_python_code(ast)
    # The generated code should join the literals with a Python plus operator
    assert " + " in code
    assert '"foo"' in code
    assert '"bar"' in code


def test_generate_typescript_code_with_identifier():
    expr = '(concat "foo" bar)'
    ast = parse_expr(expr)
    ts_code = generate_typescript_code(ast)
    assert '("foo" + record.bar)' == ts_code


def test_get_used_fields():
    expr = "(concat first_name last.name)"
    ast = parse_expr(expr)
    fields = get_used_fields(ast)
    # The current implementation collects ParsedOp values, so it returns the
    # operator.
    # This test checks that behavior.
    assert fields == ["first_name", "last.name"]


def test_nested_expression_evaluate():
    expr = "(concat (upper first_name) (lower last_name))"
    ast = parse_expr(expr)
    context = DummyContext(first_name="john", last_name="DOE")
    result = evaluate(ast, context)
    assert result == "JOHNdoe"


def test_eq_same_value_same_class():
    op1 = ParsedOp("test")
    op2 = ParsedOp("test")
    assert op1 == op2
    lit1 = ParsedLiteral("hello")
    lit2 = ParsedLiteral("hello")
    assert lit1 == lit2


def test_eq_same_value_different_subclasses():
    # Even though they are different subclasses of Parsed,
    # equality compares the 'value' attribute only.
    op = ParsedOp("value")
    lit = ParsedLiteral("value")
    ident = ParsedIdentifier("value")
    assert op == lit
    assert op == ident
    assert lit == ident


def test_eq_with_string():
    op = ParsedOp("example")
    lit = ParsedLiteral("example")
    ident = ParsedIdentifier("example")
    assert op == "example"
    assert lit == "example"
    assert ident == "example"


def test_eq_different_values():
    op = ParsedOp("one")
    lit = ParsedLiteral("two")
    ident = ParsedIdentifier("three")
    assert not (op == lit)
    assert not (lit == ident)
    assert not (op == ident)


def test_eq_non_parsed_object():
    op = ParsedOp("data")
    # When comparing with an object that is not an instance of Parsed or str,
    # equality should return False.
    assert not (op == 123)
    assert not (op is None)


def test_if():
    context = DummyContext(name="test")
    expr = '(if name "Yes" "No")'
    ast = parse_expr(expr)
    result = evaluate(ast, context)
    assert result == "Yes"

    py_code = generate_python_code(ast)
    assert '("Yes" if record.name else "No")' in py_code

    ts_code = generate_typescript_code(ast)
    assert '(record.name ? "Yes" : "No")' in ts_code


def test_upper():
    context = DummyContext(name="test")
    expr = "(upper name)"
    ast = parse_expr(expr)
    result = evaluate(ast, context)
    assert result == "TEST"

    py_code = generate_python_code(ast)
    assert "str(record.name).upper()" in py_code

    ts_code = generate_typescript_code(ast)
    assert "String(record.name).toUpperCase()" in ts_code


def test_lower():
    context = DummyContext(name="TEST")
    expr = "(lower name)"
    ast = parse_expr(expr)
    result = evaluate(ast, context)
    assert result == "test"

    py_code = generate_python_code(ast)
    assert "str(record.name).lower()" in py_code

    ts_code = generate_typescript_code(ast)
    assert "String(record.name).toLowerCase()" in ts_code


def test_is_none():
    context = DummyContext(name=None)
    expr = '(is_none name "Yes" "No")'
    ast = parse_expr(expr)
    result = evaluate(ast, context)
    assert result == "Yes"

    py_code = generate_python_code(ast)
    assert '("Yes" if record.name is None else "No")' in py_code

    ts_code = generate_typescript_code(ast)
    assert (
        "(record.name == null || "
        "record.name == undefined) ? "
        '"Yes" : "No"' in ts_code
    )

    context = DummyContext(name="test")
    expr = '(is_none name "Yes" "No")'
    ast = parse_expr(expr)
    result = evaluate(ast, context)
    assert result == "No"


def test_equals():
    context = DummyContext(name="test")
    expr = '(= name "test" "Yes" "No")'
    ast = parse_expr(expr)
    result = evaluate(ast, context)
    assert result == "Yes"

    py_code = generate_python_code(ast)
    assert '("Yes" if record.name == "test" else "No")' in py_code

    ts_code = generate_typescript_code(ast)
    assert '((record.name == "test") ? "Yes" : "No")' in ts_code

    context = DummyContext(name="not")
    expr = '(= name "test" "Yes" "No")'
    ast = parse_expr(expr)
    result = evaluate(ast, context)
    assert result == "No"


def test_date_str():
    context = DummyContext(date=datetime(2023, 10, 1))
    expr = '(date_str date "%Y-%m-%d")'
    ast = parse_expr(expr)
    result = evaluate(ast, context)
    assert result == "2023-10-01"

    py_code = generate_python_code(ast)
    assert 'record.date.strftime("%Y-%m-%d")' in py_code

    ts_code = generate_typescript_code(ast)
    assert 'record.date.strftime("%Y-%m-%d")' in ts_code


if __name__ == "__main__":
    pytest.main()
