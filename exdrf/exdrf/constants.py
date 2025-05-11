# Constants for field types
from typing import Any, List, Literal, Union

FIELD_TYPE_BLOB = "blob"
FIELD_TYPE_BOOL = "bool"
FIELD_TYPE_DT = "date-time"
FIELD_TYPE_DATE = "date"
FIELD_TYPE_TIME = "time"
FIELD_TYPE_DURATION = "duration"
FIELD_TYPE_ENUM = "enum"
FIELD_TYPE_FLOAT = "float"
FIELD_TYPE_INTEGER = "integer"
FIELD_TYPE_STRING = "string"
FIELD_TYPE_STRING_LIST = "string-list"
FIELD_TYPE_INT_LIST = "int-list"
FIELD_TYPE_FLOAT_LIST = "float-list"
FIELD_TYPE_FORMATTED = "formatted"
FIELD_TYPE_FILTER = "filter"
FIELD_TYPE_SORT = "sort"
FIELD_TYPE_REF_ONE_TO_MANY = "one-to-many"
FIELD_TYPE_REF_ONE_TO_ONE = "one-to-one"
FIELD_TYPE_REF_MANY_TO_MANY = "many-to-many"
FIELD_TYPE_REF_MANY_TO_ONE = "many-to-one"

# This are the types of relations that we know of.
RelType = Literal["OneToMany", "ManyToOne", "OneToOne", "ManyToMany"]

# A record ID can be an int in the simple case or a list of various types
# when there are multiple primary keys.
RecIdType = Union[int, List[Any]]
