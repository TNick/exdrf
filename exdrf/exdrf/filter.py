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
                "AND",
                [
                    {"fld": "id", "op": "eq", "vl": 0},
                    {"fld": "id", "op": "ne", "vl": 0},
                    {"fld": "name", "op": "eq", "vl": "This is a string"},
                    {"fld": "name", "op": "ne", "vl": "This is a string"},
                    [
                        "OR",
                        [
                            ["NOT", {"fld": "id", "op": "eq", "vl": 0}],
                            ["NOT", {"fld": "id", "op": "ne", "vl": 0}],
                            [
                                "NOT",
                                {
                                    "fld": "name",
                                    "op": "eq",
                                    "vl": "This is a string",
                                },
                            ],
                            [
                                "NOT",
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
from enum import StrEnum
from typing import (
    Any,
    Iterator,
    List,
    Literal,
    Optional,
    Tuple,
    TypedDict,
    Union,
    cast,
)

from attrs import define, field
from unidecode import unidecode

logger = logging.getLogger(__name__)


@define(slots=True, kw_only=True)
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

    _no_dia: Optional[Tuple[str, str]] = field(
        default=None, repr=False, init=False
    )

    def __getitem__(self, key: str) -> Any:
        if key == "fld":
            return self.fld
        elif key == "op":
            return self.op
        elif key == "vl":
            return self.vl
        else:
            raise KeyError(f"Unknown field: {key}")

    def __setitem__(self, key: str, value: Any):
        if key == "fld":
            self.fld = value
        elif key == "op":
            self.op = value
        elif key == "vl":
            self.vl = value
        else:
            raise KeyError(f"Unknown field: {key}")

    def __iter__(self) -> Iterator[Any]:
        yield "fld", self.fld
        yield "op", self.op
        yield "vl", self.vl

    def __len__(self) -> int:
        return 3

    def __contains__(self, key: str) -> bool:
        return key in ("fld", "op", "vl") or False

    @property
    def unidecoded(self) -> str:
        if self.vl is None:
            return ""
        if self._no_dia is None:
            ud = unidecode(self.vl)
            self._no_dia = (self.vl, ud)
            return ud
        else:
            old_vl, ud = self._no_dia
            if old_vl == self.vl:
                return ud
            else:
                ud = unidecode(self.vl)
                self._no_dia = (self.vl, ud)
                return ud


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


class SearchType(StrEnum):
    """Used with selectors to indicate the type of search to perform.

    EXACT: Exact search. The = operator is used, so the value must match
        exactly, including case.
    SIMPLE: Partial search. The ilike operator is used, and the input is
        not altered in any way. The user can use the % wildcard to match any
        number of characters.
    EXTENDED: Extended search. The input is altered in the following ways:
        - All spaces are replaced with %
        - All * are replaced with %
        - If the input contains no wildcards (%, *), then % is added to the
          beginning and end of the input.
    PATTERN: Pattern search. The input is considered to be a regular expression
        pattern. It is not altered in any way.
    """

    EXACT = "exact"
    SIMPLE = "partial"
    EXTENDED = "extended"
    PATTERN = "pattern"

    def prepare_input(self, value: str) -> str:
        """Prepare the input for the search.

        Args:
            input: The input to prepare.

        Returns:
            The prepared input.
        """
        if self == SearchType.EXTENDED:
            if "%" not in value:
                if "*" not in value:
                    value = f"%{value}%"
            else:
                value = value.replace("*", "%")
            value = value.replace(" ", "%")
        return value

    def create_filter(self, field: str, value: str) -> "FieldFilterDict":
        """Create a filter for the search.

        Args:
            field: The field to filter on.
            value: The value to filter on.

        Returns:
            A filter for the search.
        """
        value = self.prepare_input(value)
        if self == SearchType.EXACT:
            return {"fld": field, "op": "eq", "vl": value}
        elif self == SearchType.SIMPLE:
            return {"fld": field, "op": "ilike", "vl": value}
        elif self == SearchType.EXTENDED:
            return {"fld": field, "op": "ilike", "vl": value}
        elif self == SearchType.PATTERN:
            return {"fld": field, "op": "regex", "vl": value}
        else:
            raise ValueError(f"Invalid search type: {self}")


def create_field_filters(
    field_names: List[str],
    term: str,
    search_type: "SearchType",
) -> List[FieldFilter]:
    """Create filters for multiple fields with the same search term.

    Args:
        field_names: The list of field names to create filters for.
        term: The search term to use.
        search_type: The type of search to perform.

    Returns:
        A list of FieldFilter objects, one for each field.
    """
    filters = []
    for field_name in field_names:
        filter_dict = search_type.create_filter(field_name, term)
        filters.append(
            FieldFilter(
                fld=filter_dict["fld"],
                op=filter_dict["op"],
                vl=filter_dict["vl"],
            )
        )
    return filters


def extract_field_filters(filter_obj: Any) -> List[FieldFilter]:
    """Extract all FieldFilter objects from a filter structure.

    Args:
        filter_obj: The filter structure to extract filters from. Can be
            FilterType or any component of it.

    Returns:
        A list of all FieldFilter objects found in the structure.
    """
    result: List[FieldFilter] = []

    if isinstance(filter_obj, FieldFilter):
        result.append(filter_obj)
    elif isinstance(filter_obj, dict):
        try:
            result.append(FieldFilter(**filter_obj))
        except Exception:
            logger.error("Invalid field filter %s", filter_obj)
    elif isinstance(filter_obj, list):
        if len(filter_obj) == 0:
            pass
        elif len(filter_obj) == 2 and isinstance(filter_obj[0], str):
            # Logic group (and/or/not)
            if filter_obj[0].lower() in ("and", "or"):
                if isinstance(filter_obj[1], list):
                    for item in filter_obj[1]:
                        result.extend(extract_field_filters(item))
            elif filter_obj[0].lower() == "not":
                result.extend(extract_field_filters(filter_obj[1]))
        else:
            # Implicit AND list
            for item in filter_obj:
                result.extend(extract_field_filters(item))

    return result


def create_multi_field_or_filter(
    field_names: List[str],
    term: str,
    search_type: "SearchType",
) -> FilterType:
    """Create an OR filter for multiple fields with the same search term.

    Args:
        field_names: The list of field names to create filters for.
        term: The search term to use.
        search_type: The type of search to perform.

    Returns:
        A filter with OR logic combining filters for all fields. Returns
        an empty list if no field names are provided or if the term is empty.
    """
    term = term.strip() if term else ""
    if not term or not field_names:
        return []

    filters = create_field_filters(field_names, term, search_type)
    if len(filters) == 0:
        return []
    if len(filters) == 1:
        return [filters[0]]  # type: ignore
    return ["or", filters]  # type: ignore


def insert_quick_search(
    field_name: str,
    term: str,
    existing_filter: Optional[FilterType] = None,
    search_type: "SearchType" = SearchType.EXACT,
) -> FilterType:
    """Insert a quick search into the filter.

    Args:
        field_name: The name of the field to search.
        term: The search term to search for.
        existing_filter: The existing filter to insert the quick search into.
        search_type: The type of search to perform.

    Returns:
        The filter with the quick search inserted.
    """
    term = term.strip() if term else ""
    if not term:
        inserted = None
    else:
        # Use helper function to create the filter
        filters = create_field_filters([field_name], term, search_type)
        inserted = filters[0] if filters else None

    if existing_filter is None:
        return [inserted] if inserted else []
    elif isinstance(existing_filter, list):
        if len(existing_filter) == 0:
            return [inserted] if inserted else []

        # Logic group.
        if len(existing_filter) == 2 and isinstance(existing_filter[0], str):
            if existing_filter[0] == "and":
                if not isinstance(existing_filter[1], list):
                    raise ValueError(
                        f"AND argument is not a list: {existing_filter[1]}"
                    )

                new_and_value: List[Any] = [inserted] if inserted else []
                for part in existing_filter[1]:
                    # Remove any existing filter for the same field
                    if isinstance(part, FieldFilter) and part.fld == field_name:
                        continue
                    if (
                        isinstance(part, dict)
                        and part.get("fld") == field_name  # type: ignore
                    ):
                        continue
                    new_and_value.append(part)
                return cast(FilterType, ["and", new_and_value])

        new_and_value = [inserted] if inserted else []
        for part in existing_filter:
            # Remove any existing filter for the same field
            if isinstance(part, FieldFilter) and part.fld == field_name:
                continue
            if (
                isinstance(part, dict)
                and part.get("fld") == field_name  # type: ignore
            ):
                continue
            new_and_value.append(part)

        # A list at the top level means an implicit and.
        return new_and_value
    elif isinstance(existing_filter, FieldFilter):
        if existing_filter.fld == field_name:
            # Get rid of the previous value.
            return [inserted] if inserted else []
    elif isinstance(existing_filter, dict):
        if existing_filter.get("fld") == field_name:  # type: ignore
            # Get rid of the previous value.
            return [inserted] if inserted else []
    else:
        raise ValueError(f"Unknown filter type: {type(existing_filter)}")

    # We give up searching for the field. The old value of the filter
    # will be AND-ed together with the new value.
    return (
        [existing_filter, inserted]
        if existing_filter and inserted
        else []  # type: ignore
    )
