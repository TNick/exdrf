from typing import List, cast

from exdrf.filter import (
    FieldFilter,
    FilterType,
    FilterVisitor,
    LogicAndType,
    LogicNotType,
    LogicOrType,
    insert_quick_search,
    validate_filter,
)


class TestFilterVisitor(FilterVisitor):
    """Test visitor that collects visited items for verification."""

    def __init__(self, filter: FilterType):
        super().__init__(filter)
        self.visited_and: List[LogicAndType] = []
        self.visited_or: List[LogicOrType] = []
        self.visited_not: List[LogicNotType] = []
        self.visited_field: List[FieldFilter] = []

    def visit_and(self, filter: LogicAndType):
        self.visited_and.append(filter)

    def visit_or(self, filter: LogicOrType):
        self.visited_or.append(filter)

    def visit_not(self, filter: LogicNotType):
        self.visited_not.append(filter)

    def visit_field(self, filter: FieldFilter):
        self.visited_field.append(filter)


def test_field_filter_creation():
    """Test creating a FieldFilter instance."""
    filter = FieldFilter(fld="name", op="eq", vl="test")
    assert filter.fld == "name"
    assert filter.op == "eq"
    assert filter.vl == "test"


def test_simple_field_filter_visitor() -> None:
    """Test visiting a simple field filter."""
    filter: FilterType = [FieldFilter(fld="name", op="eq", vl="test")]
    visitor = TestFilterVisitor(filter)
    visitor.run(filter)

    assert len(visitor.visited_field) == 1
    assert visitor.visited_field[0].fld == "name"
    assert visitor.visited_field[0].op == "eq"
    assert visitor.visited_field[0].vl == "test"


def test_and_filter_visitor() -> None:
    """Test visiting an AND filter."""
    filter: FilterType = cast(
        FilterType,
        [
            "and",
            [
                FieldFilter(fld="id", op="eq", vl=1),
                FieldFilter(fld="name", op="eq", vl="test"),
            ],
        ],
    )
    visitor = TestFilterVisitor(filter)
    visitor.run(filter)

    assert len(visitor.visited_and) == 1
    assert len(visitor.visited_field) == 2
    assert visitor.visited_field[0].fld == "id"
    assert visitor.visited_field[1].fld == "name"


def test_or_filter_visitor() -> None:
    """Test visiting an OR filter."""
    filter: FilterType = cast(
        FilterType,
        [
            "or",
            [
                FieldFilter(fld="id", op="eq", vl=1),
                FieldFilter(fld="name", op="eq", vl="test"),
            ],
        ],
    )
    visitor = TestFilterVisitor(filter)
    visitor.run(filter)

    assert len(visitor.visited_or) == 1
    assert len(visitor.visited_field) == 2
    assert visitor.visited_field[0].fld == "id"
    assert visitor.visited_field[1].fld == "name"


def test_not_filter_visitor() -> None:
    """Test visiting a NOT filter."""
    filter: FilterType = cast(
        FilterType, ["not", FieldFilter(fld="id", op="eq", vl=1)]
    )
    visitor = TestFilterVisitor(filter)
    visitor.run(filter)

    assert len(visitor.visited_not) == 1
    assert len(visitor.visited_field) == 1
    assert visitor.visited_field[0].fld == "id"


def test_nested_filter_visitor() -> None:
    """Test visiting a nested filter structure."""
    filter: FilterType = cast(
        FilterType,
        [
            "and",
            [
                FieldFilter(fld="id", op="eq", vl=1),
                [
                    "or",
                    [
                        FieldFilter(fld="name", op="eq", vl="test"),
                        ["not", FieldFilter(fld="active", op="eq", vl=True)],
                    ],
                ],
            ],
        ],
    )
    visitor = TestFilterVisitor(filter)
    visitor.run(filter)

    assert len(visitor.visited_and) == 1
    assert len(visitor.visited_or) == 1
    assert len(visitor.visited_not) == 1
    assert len(visitor.visited_field) == 3


def test_validate_filter_valid() -> None:
    """Test validation of valid filters."""
    # Test single field filter
    assert validate_filter([FieldFilter(fld="name", op="eq", vl="test")]) == []

    # Test AND filter
    and_filter: FilterType = cast(
        FilterType,
        [
            "and",
            [
                FieldFilter(fld="id", op="eq", vl=1),
                FieldFilter(fld="name", op="eq", vl="test"),
            ],
        ],
    )
    assert validate_filter(and_filter) == []

    # Test OR filter
    or_filter: FilterType = cast(
        FilterType,
        [
            "or",
            [
                FieldFilter(fld="id", op="eq", vl=1),
                FieldFilter(fld="name", op="eq", vl="test"),
            ],
        ],
    )
    assert validate_filter(or_filter) == []

    # Test NOT filter
    not_filter: FilterType = cast(
        FilterType, ["not", FieldFilter(fld="id", op="eq", vl=1)]
    )
    assert validate_filter(not_filter) == []


def test_validate_filter_invalid() -> None:
    """Test validation of invalid filters."""
    # Test invalid field filter
    invalid_filter: FilterType = cast(FilterType, [{"invalid": "field"}])
    assert validate_filter(invalid_filter) == ["invalid_field_filter", "and[0]"]

    # Test invalid logic operator
    assert validate_filter(cast(FilterType, ["invalid", []])) == [
        "unknown_logic_operator"
    ]

    # Test invalid logic argument
    assert validate_filter(cast(FilterType, ["and", "not_a_list"])) == [
        "logic_arg_not_a_list",
        "and",
    ]

    # Test invalid logic group length
    assert validate_filter(cast(FilterType, ["and", []])) == []
    single_filter: FilterType = cast(
        FilterType, ["and", [FieldFilter(fld="id", op="eq", vl=1)]]
    )
    assert validate_filter(single_filter) == []

    # Test invalid filter type
    assert validate_filter(cast(FilterType, 123)) == ["unknown_filter_type"]

    # Test None filter
    assert validate_filter(cast(FilterType, None)) == ["none"]


def test_validate_filter_complex() -> None:
    """Test validation of complex nested filters."""
    complex_filter: FilterType = cast(
        FilterType,
        [
            "and",
            [
                FieldFilter(fld="id", op="eq", vl=1),
                [
                    "or",
                    [
                        FieldFilter(fld="name", op="eq", vl="test"),
                        ["not", FieldFilter(fld="active", op="eq", vl=True)],
                    ],
                ],
            ],
        ],
    )
    assert validate_filter(complex_filter) == []


def test_validate_filter_edge_cases() -> None:
    """Test validation of edge cases."""
    # Empty list is valid
    assert validate_filter([]) == []

    # Empty logic group is valid
    assert validate_filter(cast(FilterType, ["and", []])) == []
    assert validate_filter(cast(FilterType, ["or", []])) == []

    # Single field filter as dict is valid
    dict_filter: FilterType = cast(
        FilterType, {"fld": "id", "op": "eq", "vl": 1}
    )
    assert validate_filter(dict_filter) == []

    # Single field filter as FieldFilter instance is valid
    field_filter: FilterType = cast(
        FilterType, [FieldFilter(fld="id", op="eq", vl=1)]
    )
    assert validate_filter(field_filter) == []


def test_insert_quick_search_basic() -> None:
    """Test basic quick search insertion."""
    # Test with None filter
    result = insert_quick_search("name", "test")
    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], FieldFilter)
    assert result[0].fld == "name"
    assert result[0].op == "ilike"
    assert result[0].vl == "%test%"

    # Test with empty list
    result = insert_quick_search("name", "test", cast(FilterType, []))
    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], FieldFilter)
    assert result[0].fld == "name"
    assert result[0].op == "ilike"
    assert result[0].vl == "%test%"

    # Test with existing filter
    existing_filter = cast(FilterType, [FieldFilter(fld="id", op="eq", vl=1)])
    result = insert_quick_search("name", "test", existing_filter)
    assert isinstance(result, list)
    assert len(result) == 2
    assert existing_filter[0] in result
    assert isinstance(result[0], FieldFilter)
    assert result[0].fld == "name"
    assert result[0].op == "ilike"
    assert result[0].vl == "%test%"


def test_insert_quick_search_exact() -> None:
    """Test exact quick search insertion."""
    # Test exact search
    result = insert_quick_search("name", "test", exact=True)
    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], FieldFilter)
    assert result[0].fld == "name"
    assert result[0].op == "ilike"
    assert result[0].vl == "test"


def test_insert_quick_search_wildcards() -> None:
    """Test quick search with wildcards and spaces."""
    # Test with spaces
    result = insert_quick_search("name", "test value")
    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], FieldFilter)
    assert result[0].vl == "%test%value%"

    # Test with asterisks
    result = insert_quick_search("name", "test*value")
    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], FieldFilter)
    assert result[0].vl == "test%value"

    # Test with mixed wildcards
    result = insert_quick_search("name", "test* value")
    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], FieldFilter)
    assert result[0].vl == "test%value"


def test_insert_quick_search_replace() -> None:
    """Test replacing existing quick searches."""
    # Test replacing existing quick search
    existing_filter = cast(
        FilterType, [FieldFilter(fld="name", op="ilike", vl="%old%")]
    )
    result = insert_quick_search("name", "new", existing_filter)
    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], FieldFilter)
    assert result[0].vl == "%new%"

    # Test replacing in AND group
    and_filter = cast(
        FilterType,
        [
            "and",
            [
                FieldFilter(fld="name", op="ilike", vl="%old%"),
                FieldFilter(fld="id", op="eq", vl=1),
            ],
        ],
    )
    result = insert_quick_search("name", "new", and_filter)
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0] == "and"
    assert isinstance(result[1], list)
    assert len(result[1]) == 2
    field_filter = result[1][0]
    assert isinstance(field_filter, FieldFilter)
    assert field_filter.vl == "%new%"
    id_filter = result[1][1]
    assert isinstance(id_filter, FieldFilter)
    assert id_filter.fld == "id"


def test_insert_quick_search_empty() -> None:
    """Test quick search with empty values."""
    # Test with empty string
    result = insert_quick_search("name", "")
    assert isinstance(result, list)
    assert len(result) == 0

    # Test with whitespace only
    result = insert_quick_search("name", "   ")
    assert isinstance(result, list)
    assert len(result) == 0

    # Test with empty string and existing filter
    existing_filter = cast(FilterType, [FieldFilter(fld="id", op="eq", vl=1)])
    result = insert_quick_search("name", "", existing_filter)
    assert result == existing_filter


def test_insert_quick_search_edge_cases() -> None:
    """Test edge cases for quick search insertion."""
    # Test with None value
    result = insert_quick_search("name", None)  # type: ignore
    assert isinstance(result, list)
    assert len(result) == 0

    # Test with existing quick search in dict form
    dict_filter = cast(
        FilterType, [{"fld": "name", "op": "ilike", "vl": "%old%"}]
    )
    result = insert_quick_search("name", "new", dict_filter)
    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], FieldFilter)
    assert result[0].vl == "%new%"

    # Test with complex nested filter
    complex_filter = cast(
        FilterType,
        [
            "and",
            [
                FieldFilter(fld="name", op="ilike", vl="%old%"),
                [
                    "or",
                    [
                        FieldFilter(fld="id", op="eq", vl=1),
                        FieldFilter(fld="active", op="eq", vl=True),
                    ],
                ],
            ],
        ],
    )
    result = insert_quick_search("name", "new", complex_filter)
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0] == "and"
    assert isinstance(result[1], list)
    assert len(result[1]) == 2
    field_filter = result[1][0]
    assert isinstance(field_filter, FieldFilter)
    assert field_filter.vl == "%new%"
    or_group = result[1][1]
    assert isinstance(or_group, list)
    assert or_group[0] == "or"
