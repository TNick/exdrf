from attrs import define
from exdrf.api import (
    BlobField,
    BoolField,
    DateField,
    DateTimeField,
    DurationField,
    EnumField,
    FloatField,
    FloatListField,
    FormattedField,
    IntField,
    IntListField,
    RefBaseField,
    RefManyToManyField,
    RefManyToOneField,
    RefOneToManyField,
    RefOneToOneField,
    StrField,
    StrListField,
    FilterField,
    SortField,
)

from exdrf_qt.models.field import DBM, QtField


@define(slots=False)
class QtBlobField(BlobField, QtField[DBM]):
    pass


@define
class QtBoolField(BoolField, QtField[DBM]):
    pass


@define
class QtDateTimeField(DateTimeField, QtField[DBM]):
    pass


@define
class QtDateField(DateField, QtField[DBM]):
    pass


@define
class QtDurationField(DurationField, QtField[DBM]):
    pass


@define
class QtEnumField(EnumField, QtField[DBM]):
    pass


@define
class QtFloatField(FloatField, QtField[DBM]):
    pass


@define
class QtIntegerField(IntField, QtField[DBM]):
    pass


@define
class QtStringField(StrField, QtField[DBM]):
    pass


@define
class QtStringListField(StrListField, QtField[DBM]):
    pass


@define
class QtIntListField(IntListField, QtField[DBM]):
    pass


@define
class QtFloatListField(FloatListField, QtField[DBM]):
    pass


@define
class QtFormattedField(FormattedField, QtField[DBM]):
    pass


@define
class QtRefBaseField(RefBaseField, QtField[DBM]):
    pass


@define
class QtRefManyToOneField(RefManyToOneField, QtField[DBM]):
    pass


@define
class QtRefOneToManyField(RefOneToManyField, QtField[DBM]):
    pass


@define
class QtRefOneToOneField(RefOneToOneField, QtField[DBM]):
    pass


@define
class QtRefManyToManyField(RefManyToManyField, QtField[DBM]):
    pass


@define
class QtFilterField(FilterField, QtField[DBM]):
    pass


@define
class QtSortField(SortField, QtField[DBM]):
    pass
