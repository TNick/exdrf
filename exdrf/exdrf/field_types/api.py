from exdrf.constants import (
    FIELD_TYPE_BLOB,
    FIELD_TYPE_BOOL,
    FIELD_TYPE_DATE,
    FIELD_TYPE_DT,
    FIELD_TYPE_DURATION,
    FIELD_TYPE_ENUM,
    FIELD_TYPE_FILTER,
    FIELD_TYPE_FLOAT,
    FIELD_TYPE_FLOAT_LIST,
    FIELD_TYPE_FORMATTED,
    FIELD_TYPE_INT_LIST,
    FIELD_TYPE_INTEGER,
    FIELD_TYPE_REF_MANY_TO_MANY,
    FIELD_TYPE_REF_MANY_TO_ONE,
    FIELD_TYPE_REF_ONE_TO_MANY,
    FIELD_TYPE_REF_ONE_TO_ONE,
    FIELD_TYPE_SORT,
    FIELD_TYPE_STRING,
    FIELD_TYPE_STRING_LIST,
    FIELD_TYPE_TIME,
)
from exdrf.field_types.blob_field import BlobField, BlobInfo  # noqa: F401
from exdrf.field_types.bool_field import BoolField, BoolInfo  # noqa: F401
from exdrf.field_types.date_field import DateField, DateInfo  # noqa: F401
from exdrf.field_types.date_time import (  # noqa: F401
    DateTimeField,
    DateTimeInfo,
)
from exdrf.field_types.dur_field import (  # noqa: F401
    DurationField,
    DurationInfo,
)
from exdrf.field_types.enum_field import EnumField, EnumInfo  # noqa: F401
from exdrf.field_types.filter_field import FilterField  # noqa: F401
from exdrf.field_types.float_field import FloatField, FloatInfo  # noqa: F401
from exdrf.field_types.float_list import (  # noqa: F401
    FloatListField,
    FloatListInfo,
)
from exdrf.field_types.formatted import (  # noqa: F401
    FormattedField,
    FormattedInfo,
)
from exdrf.field_types.int_field import IntField, IntInfo  # noqa: F401
from exdrf.field_types.int_list import IntListField, IntListInfo  # noqa: F401
from exdrf.field_types.ref_base import RefBaseField, RelExtraInfo  # noqa: F401
from exdrf.field_types.ref_m2m import RefManyToManyField  # noqa: F401
from exdrf.field_types.ref_m2o import RefManyToOneField  # noqa: F401
from exdrf.field_types.ref_o2m import RefOneToManyField  # noqa: F401
from exdrf.field_types.ref_o2o import RefOneToOneField  # noqa: F401
from exdrf.field_types.sort_field import SortField  # noqa: F401
from exdrf.field_types.str_field import StrField, StrInfo  # noqa: F401
from exdrf.field_types.str_list import StrListField, StrListInfo  # noqa: F401
from exdrf.field_types.time_field import TimeField, TimeInfo  # noqa: F401

field_type_to_class = {
    FIELD_TYPE_BLOB: BlobField,
    FIELD_TYPE_BOOL: BoolField,
    FIELD_TYPE_DATE: DateField,
    FIELD_TYPE_DT: DateTimeField,
    FIELD_TYPE_DURATION: DurationField,
    FIELD_TYPE_ENUM: EnumField,
    FIELD_TYPE_FILTER: FilterField,
    FIELD_TYPE_FLOAT: FloatField,
    FIELD_TYPE_FLOAT_LIST: FloatListField,
    FIELD_TYPE_FORMATTED: FormattedField,
    FIELD_TYPE_INTEGER: IntField,
    FIELD_TYPE_INT_LIST: IntListField,
    FIELD_TYPE_REF_MANY_TO_MANY: RefManyToManyField,
    FIELD_TYPE_REF_MANY_TO_ONE: RefManyToOneField,
    FIELD_TYPE_REF_ONE_TO_MANY: RefOneToManyField,
    FIELD_TYPE_REF_ONE_TO_ONE: RefOneToOneField,
    FIELD_TYPE_SORT: SortField,
    FIELD_TYPE_STRING: StrField,
    FIELD_TYPE_STRING_LIST: StrListField,
    FIELD_TYPE_TIME: TimeField,
}
