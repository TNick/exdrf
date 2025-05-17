import pytest
from exdrf.filter_dsl import (
    DSLParser,
    DSLTokenizer,
    ParsedFieldFilter,
    ParsedLogicAnd,
    ParsedLogicOr,
    ParsedLogicNot,
    FltSyntaxError,
    serialize_filter,
)


class TestDSLParser:
    """Main test class for DSLParser."""

    @pytest.fixture
    def parser(self):
        """Create a parser instance for testing."""

        def create_parser(text):
            tokenizer = DSLTokenizer(text)
            tokens = tokenizer.tokenize()
            return DSLParser(tokens=tokens, index=0, src_text=text)

        return create_parser

    class TestCurrent:
        """Tests for the current() method."""

        def test_current_with_tokens(self, parser):
            """Test current() when tokens are available."""
            p = parser("abc")
            assert p.current().value == "abc"

        def test_current_empty(self, parser):
            """Test current() with empty input."""
            p = parser("")
            assert p.current() is None

    class TestMatch:
        """Tests for the match() method."""

        def test_match_success(self, parser):
            """Test successful token matching."""
            p = parser("abc")
            token = p.match("abc")
            assert token.value == "abc"
            assert p.index == 1

        def test_match_case_insensitive(self, parser):
            """Test case-insensitive matching."""
            p = parser("ABC")
            token = p.match("abc")
            assert token.value == "ABC"
            assert p.index == 1

        def test_match_failure(self, parser):
            """Test matching failure."""
            p = parser("abc")
            with pytest.raises(FltSyntaxError) as exc_info:
                p.match("def")
            assert "Expected 'def'" in str(exc_info.value)

        def test_match_end_of_input(self, parser):
            """Test matching at end of input."""
            p = parser("")
            with pytest.raises(FltSyntaxError) as exc_info:
                p.match("abc")
            assert "Expected 'abc'" in str(exc_info.value)

    class TestMatchAny:
        """Tests for the match_any() method."""

        def test_match_any_success(self, parser):
            """Test successful any token matching."""
            p = parser("abc")
            token = p.match_any()
            assert token.value == "abc"
            assert p.index == 1

        def test_match_any_end_of_input(self, parser):
            """Test matching any token at end of input."""
            p = parser("")
            with pytest.raises(AssertionError) as exc_info:
                p.match_any()
            assert "Unexpected end of input" in str(exc_info.value)

    class TestParseValue:
        """Tests for the parse_value() method."""

        def test_parse_string(self, parser):
            """Test parsing string values."""
            p = parser("'hello'")
            assert p.parse_value("'hello'") == "hello"

        def test_parse_list(self, parser):
            """Test parsing list values."""
            p = parser("[1,2,3]")
            assert p.parse_value("[1,2,3]") == ["1", "2", "3"]

        def test_parse_float(self, parser):
            """Test parsing float values."""
            p = parser("123.45")
            assert p.parse_value("123.45") == 123.45

        def test_parse_int(self, parser):
            """Test parsing integer values."""
            p = parser("123")
            assert p.parse_value("123") == 123

    class TestParseFieldExpr:
        """Tests for the parse_field_expr() method."""

        def test_parse_simple_field(self, parser):
            """Test parsing a simple field expression."""
            p = parser("name eq 'John'")
            result = p.parse_field_expr()
            assert isinstance(result, ParsedFieldFilter)
            assert result.fld == "name"
            assert result.op == "eq"
            assert result.vl == "John"

        def test_parse_numeric_field(self, parser):
            """Test parsing a field expression with numeric value."""
            p = parser("age gt 30")
            result = p.parse_field_expr()
            assert isinstance(result, ParsedFieldFilter)
            assert result.fld == "age"
            assert result.op == "gt"
            assert result.vl == 30

    class TestParseLogic:
        """Tests for the parse_logic() method."""

        def test_parse_and(self, parser):
            """Test parsing AND logic."""
            p = parser("AND(name eq 'John', age gt 30)")
            result = p.parse_logic(p.current())
            assert isinstance(result, ParsedLogicAnd)
            assert len(result.items) == 2
            assert result.items[0].fld == "name"
            assert result.items[1].fld == "age"

        def test_parse_or(self, parser):
            """Test parsing OR logic."""
            p = parser("OR(name eq 'John', age gt 30)")
            result = p.parse_logic(p.current())
            assert isinstance(result, ParsedLogicOr)
            assert len(result.items) == 2
            assert result.items[0].fld == "name"
            assert result.items[1].fld == "age"

        def test_parse_nested_logic(self, parser):
            """Test parsing nested logic expressions."""
            p = parser("AND(name eq 'John', OR(age gt 30, status eq 'active'))")
            result = p.parse_logic(p.current())
            assert isinstance(result, ParsedLogicAnd)
            assert len(result.items) == 2
            assert result.items[0].fld == "name"
            assert isinstance(result.items[1], ParsedLogicOr)

    class TestParseNot:
        """Tests for the parse_not() method."""

        def test_parse_not(self, parser):
            """Test parsing NOT logic."""
            p = parser("NOT(name eq 'John')")
            result = p.parse_not()
            assert isinstance(result, ParsedLogicNot)
            assert result.item.fld == "name"
            assert result.item.op == "eq"
            assert result.item.vl == "John"

    class TestParseExpression:
        """Tests for the parse_expression() method."""

        def test_parse_field_expression(self, parser):
            """Test parsing a field expression."""
            p = parser("name eq 'John'")
            result = p.parse_expression()
            assert len(result) == 1
            assert isinstance(result[0], ParsedFieldFilter)
            assert result[0].fld == "name"

        def test_parse_logic_expression(self, parser):
            """Test parsing a logic expression."""
            p = parser("AND(name eq 'John', age gt 30)")
            result = p.parse_expression()
            assert len(result) == 1
            assert isinstance(result[0], ParsedLogicAnd)

        def test_parse_not_expression(self, parser):
            """Test parsing a NOT expression."""
            p = parser("NOT(name eq 'John')")
            result = p.parse_expression()
            assert len(result) == 1
            assert isinstance(result[0], ParsedLogicNot)

    class TestParse:
        """Tests for the parse() method."""

        def test_parse_simple_expression(self, parser):
            """Test parsing a simple expression."""
            p = parser("name eq 'John'")
            result = p.parse()
            assert len(result) == 1
            assert isinstance(result[0], ParsedFieldFilter)

        def test_parse_complex_expression(self, parser):
            """Test parsing a complex expression."""
            p = parser("AND(name eq 'John', OR(age gt 30, status eq 'active'))")
            result = p.parse()
            assert len(result) == 1
            assert isinstance(result[0], ParsedLogicAnd)

        def test_parse_unexpected_token(self, parser):
            """Test parsing with unexpected token."""
            p = parser("name eq 'John' extra")
            with pytest.raises(FltSyntaxError) as exc_info:
                p.parse()
            assert "Unexpected token" in str(exc_info.value)

        def test_parse_empty_input(self, parser):
            """Test parsing empty input."""
            p = parser("")
            with pytest.raises(FltSyntaxError) as exc_info:
                p.parse()
            assert "Unexpected end of input" in str(exc_info.value)

    class TestSerializeFilter:
        """Tests for the serialize_filter function."""

        def test_serialize_field_filter(self, parser):
            """Test serializing a field filter."""
            p = parser("name eq 'John'")
            parsed = p.parse()
            result = serialize_filter(parsed[0])
            assert result == {"fld": "name", "op": "eq", "vl": "John"}

        def test_serialize_and_logic(self, parser):
            """Test serializing AND logic."""
            p = parser("AND(name eq 'John', age gt 30)")
            parsed = p.parse()
            result = serialize_filter(parsed[0])
            expected = [
                "AND",
                [
                    {"fld": "name", "op": "eq", "vl": "John"},
                    {"fld": "age", "op": "gt", "vl": 30},
                ],
            ]
            assert result == expected

        def test_serialize_or_logic(self, parser):
            """Test serializing OR logic."""
            p = parser("OR(name eq 'John', age gt 30)")
            parsed = p.parse()
            result = serialize_filter(parsed[0])
            expected = [
                "OR",
                [
                    {"fld": "name", "op": "eq", "vl": "John"},
                    {"fld": "age", "op": "gt", "vl": 30},
                ],
            ]
            assert result == expected

        def test_serialize_not_logic(self, parser):
            """Test serializing NOT logic."""
            p = parser("NOT(status eq 'inactive')")
            parsed = p.parse()
            result = serialize_filter(parsed[0])
            expected = ["NOT", {"fld": "status", "op": "eq", "vl": "inactive"}]
            assert result == expected

        def test_serialize_complex_nested(self, parser):
            """Test serializing complex nested expressions."""
            expr = (
                "AND(name eq 'John', "
                "OR(age gt 30, NOT(status eq 'inactive')))"
            )
            p = parser(expr)
            parsed = p.parse()
            result = serialize_filter(parsed[0])
            expected = [
                "AND",
                [
                    {"fld": "name", "op": "eq", "vl": "John"},
                    [
                        "OR",
                        [
                            {"fld": "age", "op": "gt", "vl": 30},
                            [
                                "NOT",
                                {"fld": "status", "op": "eq", "vl": "inactive"},
                            ],
                        ],
                    ],
                ],
            ]
            assert result == expected

        def test_serialize_list_of_filters(self, parser):
            """Test serializing a list of filters."""
            p = parser("name eq 'John'")
            parsed = p.parse()
            result = serialize_filter(parsed)
            expected = [{"fld": "name", "op": "eq", "vl": "John"}]
            assert result == expected

        def test_serialize_invalid_type(self):
            """Test serializing an invalid type raises ValueError."""
            with pytest.raises(ValueError) as exc_info:
                serialize_filter(42)
            assert "Unknown object type" in str(exc_info.value)
