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

import logging
from typing import Any, List, Literal, Optional, Tuple, TypedDict, Union, cast

from attrs import define

logger = logging.getLogger(__name__)


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


class FieldFilterDict(TypedDict):
    """A dictionary type that has the same keys as FieldFilter."""

    fld: str  # field name
    op: str  # operation type (e.g., "eq", "ne", "ilike", etc.)
    vl: Any  # value to filter by


LogicAndType = Tuple[Literal["and"], "FilterType"]
LogicOrType = Tuple[Literal["or"], "FilterType"]
LogicNotType = Tuple[Literal["not"], FieldFilter]
FilterType = List[
    Union[FieldFilter, FieldFilterDict, LogicAndType, LogicOrType, LogicNotType]
]


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

    def visit_field(self, filter: FieldFilter):
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
                    if not isinstance(filter[1], list):
                        self.run(filter[1])
                        return
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
            self.visit_field(FieldFilter(**filter))
        elif isinstance(filter, FieldFilter):
            self.visit_field(filter)
        else:
            raise ValueError(f"Unknown filter type: {type(filter)}")


def validate_filter(filter: FilterType) -> List[str]:
    """Validate the filter expression.

    Error codes:
    - invalid_field_filter: The individual field filter is invalid. This occurs
      when the individual field filter is represented as a dictionary and
      a FieldFilter instance could not be constructed out of it.
    - logic_arg_not_a_list: AND and OR require a list with two elements:
      the keyword and a list of arguments. When this code is returned the
      second item in the logic group/top list is not a list..
    - logic_arg_not_2_items: AND, OR and NOT definition is called a logic group.
      It consists of the keyword and a list of arguments. In this case the
      logic group does not contain two items.
    - unknown_logic_operator: The logic operator is unknown. Known operators
      are 'and', 'or' and 'not'.
    - unknown_arg_type: The argument type is unknown. Valid component items
      are: an individual field filter (either in class form or in dictionary
      form), a logic group (a list with two items: the logic operator and
      a list of arguments), and NOT groups (a list with two items: the 'not'
      keyword and a single item).
    - unknown_filter_type: Same as unknown_arg_type but at the top level. At
      the top level a single field filter is allowed. Otherwise, the filter
      is assumed to be the arguments of an implicit AND group so it should
      be a list.
    - none: The top level filter is None.

    Args:
        filter: The filter to validate.

    Returns:
        A list of error information. First item is the error code, the rest
        is the path to the invalid item.
    """

    def validate_logic_arg_bit(item: Any) -> List[str]:  # type: ignore
        if isinstance(item, FieldFilter):
            # A single item in class form is acceptable.
            return []
        elif isinstance(item, dict):
            # A single item in dictionary form is acceptable if it has
            # the correct keys.
            try:
                FieldFilter(**item)
            except Exception as exc:
                logger.error("Invalid field filter %s: %s", item, exc)
                return ["invalid_field_filter"]
        elif isinstance(item, list):
            if len(item) == 0:
                # Empty list is allowed.
                return []

            # A nested list means the start of a new logic group.
            # Logic groups always have length 2:
            # - The first item is the logic operator.
            # - The second item is the list of arguments.
            if len(item) != 2:
                return ["logic_arg_not_2_items"]

            if not isinstance(item[0], str) or item[0].lower() not in [
                "and",
                "or",
                "not",
            ]:
                return ["unknown_logic_operator"]

            # Not consists of the 'not' keyword and an item.
            if item[0] == "not":
                return validate_logic_arg_bit(item[1])

            # And and or consist of a list of arguments.
            return validate_and_or_arg(item[0], item[1])

        else:
            return ["unknown_arg_type"]

    def validate_and_or_arg(op: str, arg: Any) -> List[str]:
        if not isinstance(arg, list):
            return ["logic_arg_not_a_list", op]

        if len(arg) == 0:
            # Empty list is allowed.
            return []

        # Go through each item that should be and-ed or or-ed.
        for i, item in enumerate(arg):
            tmp = validate_logic_arg_bit(item)
            if tmp:
                tmp.insert(1, f"{op}[{i}]")
                return tmp

        return []

    if filter is None:
        # The filter should never be None.
        return ["none"]
    elif isinstance(filter, list):
        if len(filter) == 0:
            # Empty list is allowed.
            return []

        # Logic group.
        if len(filter) == 2 and isinstance(filter[0], str):
            return validate_logic_arg_bit(filter)

        # A list at the top level means an implicit and.
        return validate_and_or_arg("and", filter)
    elif isinstance(filter, FieldFilter):
        # A single field filter is acceptable.
        return []
    elif isinstance(filter, dict):
        # The dictionary at the top level indicates that there is a single
        # filter item.
        try:
            FieldFilter(**filter)
        except Exception as exc:
            logger.error("Invalid field filter %s: %s", filter, exc)
            return ["invalid_field_filter"]
    else:
        return ["unknown_filter_type"]
    return []


def insert_quick_search(
    field_name: str,
    value: str,
    filter: Optional[FilterType] = None,
    exact: bool = False,
) -> FilterType:
    """Insert a quick search into the filter.

    Args:
        field_name: The name of the field to search.
        value: The value to search for.
        filter: The filter to insert the quick search into.
        exact: Whether the search should be exact.

    Returns:
        The filter with the quick search inserted.
    """
    value = value.strip() if value else ""
    if value and not exact:
        if "*" not in value:
            if "%" not in value:
                value = f"%{value}%"
        else:
            value = value.replace("*", "%")
        value = value.replace(" ", "%").replace("%%", "%")

    # Compute the value to insert.
    inserted = (
        FieldFilter(fld=field_name, op="ilike", vl=value) if value else None
    )

    if filter is None:
        return [inserted] if inserted else []
    elif isinstance(filter, list):
        if len(filter) == 0:
            return [inserted] if inserted else []

        # Logic group.
        if len(filter) == 2 and isinstance(filter[0], str):
            if filter[0] == "and":
                if not isinstance(filter[1], list):
                    raise ValueError(f"AND argument is not a list: {filter[1]}")

                new_and_value: List[Any] = [inserted] if inserted else []
                for part in filter[1]:
                    if (
                        isinstance(part, FieldFilter)
                        and part.fld == field_name
                        and part.op == "ilike"
                    ):
                        continue
                    if (
                        isinstance(part, dict)
                        and part["fld"] == field_name
                        and part["op"] == "ilike"
                    ):
                        continue
                    new_and_value.append(part)
                return cast(FilterType, ["and", new_and_value])

        new_and_value = [inserted] if inserted else []
        for part in filter:
            if (
                isinstance(part, FieldFilter)
                and part.fld == field_name
                and part.op == "ilike"
            ):
                continue
            if (
                isinstance(part, dict)
                and part["fld"] == field_name  # type: ignore
                and part["op"] == "ilike"  # type: ignore
            ):
                continue
            new_and_value.append(part)

        # A list at the top level means an implicit and.
        return new_and_value
    elif isinstance(filter, FieldFilter):
        if filter.fld == field_name and filter.op == "ilike":
            # Get rid of the previous value.
            return [inserted] if inserted else []
    elif isinstance(filter, dict):
        if filter["fld"] == field_name and filter["op"] == "ilike":
            # Get rid of the previous value.
            return [inserted] if inserted else []
    else:
        raise ValueError(f"Unknown filter type: {type(filter)}")

    # We give up searching for the field. The old value of the filter
    # will be AND-ed together with the new value.
    return [filter, inserted] if filter and inserted else []  # type: ignore
