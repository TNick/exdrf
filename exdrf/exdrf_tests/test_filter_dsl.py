from typing import Any, cast

import pytest

from exdrf.filter import FieldFilter, FilterType
from exdrf.filter_dsl import (
    DSLParser,
    DSLTokenizer,
    FltSyntaxError,
    ParsedFieldFilter,
    ParsedLogicAnd,
    ParsedLogicNot,
    ParsedLogicOr,
    Token,
    raw_filter_to_text,
    serialize_filter,
)


@pytest.fixture
def parser():
    """Create a parser instance for testing."""

    def create_parser(text):
        tokenizer = DSLTokenizer(text)
        tokens = tokenizer.tokenize()
        return DSLParser(tokens=tokens, index=0, src_text=text)

    return create_parser


class TestDSLParser:
    """Main test class for DSLParser."""

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
            token = p.match_any("expected")
            assert token.value == "abc"
            assert p.index == 1

        def test_match_any_end_of_input(self, parser):
            """Test matching any token at end of input."""
            p = parser("")
            with pytest.raises(FltSyntaxError) as exc_info:
                p.match_any("expected")
            assert "Expected <expected>, but got end of input" in str(
                exc_info.value
            )

    class TestParseValue:
        """Tests for the parse_value() method."""

        def test_parse_string(self, parser):
            """Test parsing string values."""
            p = parser("'hello'")
            tk = Token(value="'hello'", line=1, column=1, index=1)
            assert p.parse_value(tk) == "hello"

        def test_parse_list(self, parser):
            """Test parsing list values."""
            p = parser("[1,2,3]")
            tk = Token(value="[1,2,3]", line=1, column=1, index=1)
            assert p.parse_value(tk) == ["1", "2", "3"]

        def test_parse_float(self, parser):
            """Test parsing float values."""
            p = parser("123.45")
            tk = Token(value="123.45", line=1, column=1, index=1)
            assert p.parse_value(tk) == 123.45

        def test_parse_int(self, parser):
            """Test parsing integer values."""
            p = parser("123")
            tk = Token(value="123", line=1, column=1, index=1)
            assert p.parse_value(tk) == 123

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
            assert "Expected <operator>, but got end of input" in str(
                exc_info.value
            )

        def test_parse_empty_input(self, parser):
            """Test parsing empty input."""
            p = parser("")
            result = p.parse()
            assert result == []

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

        def test_or_with_one_nested(self, parser):
            p = parser(
                "OR (\n" "    id == 1\n" ")\n" "OR (\n" "    id == 2\n" ")\n"
            )
            parsed = p.parse()
            assert isinstance(parsed, list)
            assert len(parsed) == 2
            assert isinstance(parsed[0], ParsedLogicOr)
            assert len(parsed[0].items) == 1
            assert isinstance(parsed[0].items[0], ParsedFieldFilter)
            assert parsed[0].items[0].fld == "id"
            assert parsed[0].items[0].op == "=="
            assert parsed[0].items[0].vl == 1
            assert len(parsed[1].items) == 1
            assert isinstance(parsed[1].items[0], ParsedFieldFilter)
            assert parsed[1].items[0].fld == "id"
            assert parsed[1].items[0].op == "=="
            assert parsed[1].items[0].vl == 2
            result = serialize_filter(parsed)
            expected = [
                ["OR", [{"fld": "id", "op": "==", "vl": 1}]],
                ["OR", [{"fld": "id", "op": "==", "vl": 2}]],
            ]
            assert result == expected


class TestRawFilterToText:
    """Tests for the raw_filter_to_text function."""

    def test_simple_field_filter(self) -> None:
        """Test a simple field filter."""
        filter_data: FieldFilter = cast(
            FieldFilter, {"fld": "name", "op": "eq", "vl": "John"}
        )
        expected_text = "name eq John\n"
        assert raw_filter_to_text(filter_data) == expected_text

    def test_and_logic_direct_processing(self) -> None:
        """Test AND logic as directly processed by do_part."""
        direct_and_filter_data: Any = [
            "and",
            [
                cast(FieldFilter, {"fld": "name", "op": "eq", "vl": "John"}),
                cast(FieldFilter, {"fld": "age", "op": "gt", "vl": 30}),
            ],
        ]
        expected_text_direct_and = "name eq John\nage gt 30\n"
        assert (
            raw_filter_to_text(direct_and_filter_data)
            == expected_text_direct_and
        )

    def test_and_logic_stripping_with_field_filter(self) -> None:
        """Test stripping of outer AND when its content is a FieldFilter."""
        stripped_and_with_field: Any = [
            "AND",  # Uppercase for raw_filter_to_text stripping logic
            cast(FieldFilter, {"fld": "id", "op": "eq", "vl": 1}),
        ]
        expected_stripped_field = "id eq 1\n"
        assert (
            raw_filter_to_text(stripped_and_with_field)
            == expected_stripped_field
        )

    def test_and_logic_stripping_with_another_operation(self) -> None:
        """Test stripping of outer AND when its content is another operation."""
        stripped_and_with_or: Any = [
            "AND",  # Uppercase for stripping
            [  # Inner content is an OR operation
                "or",  # lowercase for do_part processing
                [
                    cast(FieldFilter, {"fld": "c1", "op": "lt", "vl": 0}),
                    cast(FieldFilter, {"fld": "c2", "op": "gt", "vl": 0}),
                ],
            ],
        ]
        expected_stripped_or = "OR (\tc1 lt 0\n\tc2 gt 0\n)\n"
        assert raw_filter_to_text(stripped_and_with_or) == expected_stripped_or

    def test_or_logic(self) -> None:
        """Test OR logic."""
        filter_data: Any = [
            "or",
            [
                cast(FieldFilter, {"fld": "name", "op": "eq", "vl": "John"}),
                cast(FieldFilter, {"fld": "age", "op": "gt", "vl": 30}),
            ],
        ]
        expected_text = "OR (\tname eq John\n\tage gt 30\n)\n"
        assert raw_filter_to_text(filter_data) == expected_text

    def test_not_logic(self) -> None:
        """Test NOT logic."""
        filter_data: Any = [
            "not",
            cast(FieldFilter, {"fld": "status", "op": "eq", "vl": "inactive"}),
        ]
        expected_text = "NOT (\tstatus eq inactive\n)\n"
        assert raw_filter_to_text(filter_data) == expected_text

    def test_nested_logic_with_outer_and_stripping(self) -> None:
        """Test nested logic with outer AND stripping."""
        filter_data_stripped_and: Any = [
            "AND",  # Uppercase for stripping
            [  # Inner content for stripped AND is an "or" operation
                "or",
                [
                    cast(
                        FieldFilter, {"fld": "name", "op": "eq", "vl": "John"}
                    ),
                    [  # This is an inner "not" operation
                        "not",
                        cast(
                            FieldFilter,
                            {"fld": "status", "op": "eq", "vl": "active"},
                        ),
                    ],
                ],
            ],
        ]
        expected_text = (
            "OR (\n"
            "\tname eq John\n"
            "\tNOT (\n"
            "\t\tstatus eq active\n"
            "\t)\n"
            ")\n"
        )
        assert raw_filter_to_text(filter_data_stripped_and) == expected_text

    def test_empty_filter_list(self) -> None:
        """Test an empty list filter (valid FilterType)."""
        filter_data: FilterType = []
        assert raw_filter_to_text(filter_data) == ""

    def test_empty_logic_operator_content(self) -> None:
        """Test an empty logic operator's content list."""
        filter_data_direct_empty_and: Any = ["and", []]
        expected_direct_empty_and = ""
        assert (
            raw_filter_to_text(filter_data_direct_empty_and)
            == expected_direct_empty_and
        )

        # Test stripped "AND" with inner operation that is an empty "and"
        filter_data_strip_empty_inner_and: Any = ["AND", ["and", []]]
        expected_strip_empty_inner_and = "AND (\n)\n"
        assert (
            raw_filter_to_text(filter_data_strip_empty_inner_and)
            == expected_strip_empty_inner_and
        )

    def test_single_item_in_outer_and_is_unwrapped(self) -> None:
        """Test outer AND stripping with a single FieldFilter as content."""
        filter_data_single_dict_in_and: Any = [
            "AND",
            cast(FieldFilter, {"fld": "name", "op": "eq", "vl": "John"}),
        ]
        expected_text_single_dict = "name eq John\n"
        assert (
            raw_filter_to_text(filter_data_single_dict_in_and)
            == expected_text_single_dict
        )

    def test_outer_and_stripping_with_single_inner_operation(self) -> None:
        """Test outer AND stripping with a single inner operation as content."""
        filter_data_inner_op_in_and_corrected: Any = [
            "AND",
            [
                "or",
                # Items for "or" is a list containing one FieldFilter
                [cast(FieldFilter, {"fld": "age", "op": "lt", "vl": 20})],
            ],
        ]
        expected_text_inner_op = "OR (\n" "\tage lt 20\n" ")\n"
        assert (
            raw_filter_to_text(filter_data_inner_op_in_and_corrected)
            == expected_text_inner_op
        )

    def test_outer_and_stripping_error_with_list_of_field_filters(self) -> None:
        """Test error when outer AND content is a direct list of FieldFilters.

        We expect a ValueError to be raised when the outer AND content is a
        direct list of FieldFilters.
        """
        filter_data_list_with_single_dict: Any = [
            "AND",
            cast(FieldFilter, {"fld": "name", "op": "eq", "vl": "John"}),
        ]
        with pytest.raises(ValueError) as exc_info:
            raw_filter_to_text(filter_data_list_with_single_dict)
        expected = "logic operator list expects a list as the second element. "
        assert expected in str(exc_info.value).lower()

    def test_invalid_filter_part_type(self) -> None:
        """Test with an invalid type in filter parts."""
        filter_data: Any = [
            "and",
            [
                cast(FieldFilter, {"fld": "name", "op": "eq", "vl": "John"}),
                123,  # Invalid part
            ],
        ]
        with pytest.raises(ValueError) as exc_info:
            raw_filter_to_text(filter_data)
        assert "Invalid filter part: 123" in str(exc_info.value)

    def test_invalid_logic_operator_name(self) -> None:
        """Test with an invalid logic operator name."""
        filter_data: Any = [
            "XOR",
            [cast(FieldFilter, {"fld": "name", "op": "eq", "vl": "John"})],
        ]
        with pytest.raises(ValueError) as exc_info:
            raw_filter_to_text(filter_data)
        assert "Invalid logic operator: xor" in str(exc_info.value)

    def test_list_with_single_field_filter_item_causes_error(self) -> None:
        """Test a list of a single FieldFilter item causes error."""
        filter_data: Any = [
            cast(FieldFilter, {"xxx": "city", "op": "eq", "vl": "London"})
        ]
        with pytest.raises(KeyError) as exc_info:
            raw_filter_to_text(filter_data)
        error_message = str(exc_info.value).lower()
        assert exc_info.type == KeyError
        assert "fld" in error_message

    def test_logic_op_invalid_arity(self) -> None:
        """Test a logic operator with invalid arity (e.g., list of length 1)."""
        filter_data_and: Any = ["and"]
        with pytest.raises(ValueError) as exc_info_and:
            raw_filter_to_text(filter_data_and)
        expected = "logic operator list expects two elements. Got ['and']"
        assert expected in str(exc_info_and.value)

        filter_data_not: Any = ["not"]
        with pytest.raises(ValueError) as exc_info_not:
            raw_filter_to_text(filter_data_not)
        expected = "logic operator list expects two elements. Got ['not']"
        assert expected in str(exc_info_not.value)

        filter_data_or: Any = ["or"]
        with pytest.raises(ValueError) as exc_info_or:
            raw_filter_to_text(filter_data_or)
        expected = "logic operator list expects two elements. Got ['or']"
        assert expected in str(exc_info_or.value)
