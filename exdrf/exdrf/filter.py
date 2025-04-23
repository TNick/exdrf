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

from typing import Any, List, Literal, Tuple, Union

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
