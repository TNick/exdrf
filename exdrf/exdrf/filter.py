"""Filter support.

This is how the filter is imagined to show in JSON format:
```json
    {
        "filter": [
            {"fld": "id", "op": "eq", "vl": 0},
            {"fld": "id", "op": "ne", "vl": 0},
            {"fld": "name", "op": "eq", "vl": "This is a string"},
            {"fld": "name", "op": "ne", "vl": "This is a string"},
            [
                "and",
                [
                    {"fld": "id", "op": "eq", "vl": 0},
                    {"fld": "id", "op": "ne", "vl": 0},
                    {"fld": "name", "op": "eq", "vl": "This is a string"},
                    {"fld": "name", "op": "ne", "vl": "This is a string"},
                    [
                        "or",
                        [
                            ["not", {"fld": "id", "op": "eq", "vl": 0}],
                            ["not", {"fld": "id", "op": "ne", "vl": 0}],
                            [
                                "not",
                                {
                                    "fld": "name",
                                    "op": "eq",
                                    "vl": "This is a string",
                                },
                            ],
                            [
                                "not",
                                {
                                    "fld": "name",
                                    "op": "ne",
                                    "vl": "This is a string",
                                },
                            ],
                        ],
                    ],
                ],
            ],
            [
                "or",
                [
                    {"fld": "id", "op": "eq", "vl": 0},
                    {"fld": "id", "op": "ne", "vl": 0},
                    {"fld": "name", "op": "eq", "vl": "This is a string"},
                    {"fld": "name", "op": "ne", "vl": "This is a string"},
                ],
            ],
            ["not", {"fld": "id", "op": "eq", "vl": 0}],
            ["not", {"fld": "id", "op": "ne", "vl": 0}],
            ["not", {"fld": "name", "op": "eq", "vl": "This is a string"}],
            ["not", {"fld": "name", "op": "ne", "vl": "This is a string"}],
        ]
    }
```
"""

from typing import Any, List, Literal, Tuple, Union, cast

from attrs import define


@define
class FieldFilter:
    """Describes how the results should be filtered by one of the fields.

    Attributes:
        fld: The field to filter by. This is the unique string key of the field
            in the resource.
        op: The operation to perform. This is the unique string key of the
            operation.
        vl: The value to compare against. Its meaning depends on the operation.
    """

    fld: str
    op: str
    vl: Any


LogicAndType = Tuple[Literal["and"], "FilterType"]
LogicOrType = Tuple[Literal["or"], "FilterType"]
LogicNotType = Tuple[Literal["not"], FieldFilter]
FilterType = List[Union[FieldFilter, LogicAndType, LogicOrType, LogicNotType]]


@define
class FilterVisitor:
    """A visitor for the filter.

    This is a visitor for the filter that allows to visit the filter and
    perform some action on each element.

    Attributes:
        filter: The filter to visit.
    """

    filter: FilterType

    def visit_and(self, filter: LogicAndType):
        """Visit an and filter.

        Args:
            filter: The and filter to visit.
        """

    def visit_or(self, filter: LogicOrType):
        """Visit an or filter.

        Args:
            filter: The or filter to visit.
        """

    def visit_not(self, filter: LogicNotType):
        """Visit a not filter.

        Args:
            filter: The not filter to visit.
        """

    def visit_logic(self, filter: LogicAndType | LogicOrType | LogicNotType):
        """Visit a logic filter.

        Args:
            filter: The logic filter to visit.
        """

    def visit_field(self, filter: dict):
        """Visit a field filter.

        Args:
            filter: The field filter to visit.
        """

    def run(self, filter: Any):
        """Run the visitor on the filter.

        Args:
            filter: The filter to visit.
        """
        if isinstance(filter, list):
            if len(filter) == 0:
                return

            item = filter[0]
            if isinstance(item, str):
                if len(filter) != 2:
                    raise ValueError(
                        f"Logic operator {item} must be followed by a "
                        "filter list"
                    )
                item = item.lower()
                if item == "and":
                    self.visit_and(cast(LogicAndType, filter))
                elif item == "or":
                    self.visit_or(cast(LogicOrType, filter))
                elif item == "not":
                    self.visit_not(cast(LogicNotType, filter))
                else:
                    raise ValueError(f"Unknown logic operator: {item}")
                self.visit_logic(
                    cast(LogicAndType | LogicOrType | LogicNotType, filter)
                )

                for item in cast(List[FilterType], filter[1]):
                    self.run(item)
                return

            for sub_item in cast(List[FilterType], filter):
                self.run(sub_item)
        elif isinstance(filter, dict):
            self.visit_field(cast(FieldFilter, filter))
        else:
            raise ValueError(f"Unknown filter type: {type(filter)}")
