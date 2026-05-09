# Constants for field types
from typing import Any, Final, Iterable, Literal, Union

FIELD_TYPE_BLOB: Final[Literal["blob"]] = "blob"
FIELD_TYPE_BOOL: Final[Literal["bool"]] = "bool"
FIELD_TYPE_DT: Final[Literal["date-time"]] = "date-time"
FIELD_TYPE_DATE: Final[Literal["date"]] = "date"
FIELD_TYPE_TIME: Final[Literal["time"]] = "time"
FIELD_TYPE_DURATION: Final[Literal["duration"]] = "duration"
FIELD_TYPE_ENUM: Final[Literal["enum"]] = "enum"
FIELD_TYPE_FLOAT: Final[Literal["float"]] = "float"
FIELD_TYPE_INTEGER: Final[Literal["integer"]] = "integer"
FIELD_TYPE_STRING: Final[Literal["string"]] = "string"
FIELD_TYPE_STRING_LIST: Final[Literal["string-list"]] = "string-list"
FIELD_TYPE_INT_LIST: Final[Literal["int-list"]] = "int-list"
FIELD_TYPE_FLOAT_LIST: Final[Literal["float-list"]] = "float-list"
FIELD_TYPE_FORMATTED: Final[Literal["formatted"]] = "formatted"
FIELD_TYPE_FILTER: Final[Literal["filter"]] = "filter"
FIELD_TYPE_SORT: Final[Literal["sort"]] = "sort"
FIELD_TYPE_REF_ONE_TO_MANY: Final[Literal["one-to-many"]] = "one-to-many"
FIELD_TYPE_REF_ONE_TO_ONE: Final[Literal["one-to-one"]] = "one-to-one"
FIELD_TYPE_REF_MANY_TO_MANY: Final[Literal["many-to-many"]] = "many-to-many"
FIELD_TYPE_REF_MANY_TO_ONE: Final[Literal["many-to-one"]] = "many-to-one"

# This are the types of relations that we know of.
RelType = Literal["OneToMany", "ManyToOne", "OneToOne", "ManyToMany"]

# A record ID can be an int in the simple case or a list of various types
# when there are multiple primary keys.
RecIdType = Union[int, Iterable[Any]]
