from typing import Any, Dict, Optional

import humanize
from attrs import define, field
from exdrf.api import (
    BlobField,
    BoolField,
    DateField,
    DateTimeField,
    DurationField,
    EnumField,
    FilterField,
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
    SortField,
    StrField,
    StrListField,
    TimeField,
)
from exdrf.constants import RecIdType
from exdrf.moment import MomentFormat
from PyQt5.QtCore import Qt

from exdrf_qt.models.field import DBM, QtField


@define(slots=False)
class QtBlobField(BlobField, QtField[DBM]):
    pass


@define
class QtBoolField(BoolField, QtField[DBM]):
    pass


@define
class QtDateTimeField(DateTimeField, QtField[DBM]):

    formatter: Optional[MomentFormat] = field(default=None)

    def values(self, item: DBM) -> Dict[Qt.ItemDataRole, Any]:
        value = getattr(item, self.name)
        if value is None:
            return self.expand_value(None)

        if self.formatter is None:
            self.formatter = MomentFormat.from_string(self.format)

        display = self.formatter.moment_to_string(value)
        return self.expand_value(
            value=value,
            DisplayRole=display,
            EditRole=value,
            ToolTipRole=humanize.naturaltime(value),
        )


@define
class QtDateField(DateField, QtField[DBM]):
    pass


@define
class QtTimeField(TimeField, QtField[DBM]):
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
    show_n_labels: int = field(default=4)

    def values(self, item: DBM) -> Dict[Qt.ItemDataRole, Any]:
        """Compute the values for each role for this field.

        As this is a field that has multiple values, we ask the implementation
        to provide to helper methods to compute the ID and label for each
        of the items.

        The resulted edit role will have the list of IDs and the display role
        will have a comma-separated list of the labels. If the list is
        longer than `show_n_labels`, the last label will be "...",
        with the full list shown in the tooltip.
        """
        items = getattr(item, self.name)
        if items is None:
            return self.expand_value(None)

        labels = []
        ids = []
        for item in items:
            labels.append(self.part_label(item))
            ids.append(self.part_id(item))

        display_labels = (
            labels
            if len(labels) <= self.show_n_labels
            else (labels[: self.show_n_labels] + ["..."])
        )
        tooltip = "\\n".join(labels)
        display = ", ".join(display_labels)

        return self.expand_value(
            value=display,
            EditRole=ids,
            ToolTipRole=tooltip,
        )

    def part_id(self, item: Any) -> RecIdType:
        """Compute the ID for one of the components of the field."""
        raise NotImplementedError(
            "part_id is not implemented for QtRefOneToManyField"
        )

    def part_label(self, item: Any) -> str:
        """Compute the label for one of the components of the field."""
        raise NotImplementedError(
            "part_label is not implemented for QtRefOneToManyField"
        )


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
