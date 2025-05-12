import logging
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
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QBrush

from exdrf_qt.models.field import (
    DBM,
    QtField,
    italic_font,
    light_grey,
    regular_font,
)

logger = logging.getLogger(__name__)


@define(slots=False)
class QtBlobField(BlobField, QtField[DBM]):
    def values(self, record: DBM) -> Dict[Qt.ItemDataRole, Any]:
        value = getattr(record, self.name)
        if value is None:
            return self.expand_value(None)

        label = self.t("cmn.blob", "BLOB")
        description = self.t(
            "cmn.blob_tip",
            "Binary data ({sz} bytes, {mime})",
            sz=len(value),
            mime=self.mime_type or "application/octet-stream",
        )
        return self.expand_value(
            value,
            FontRole=italic_font,
            ForegroundRole=light_grey,
            AccessibleTextRole=label,
            DisplayRole=label,
            ToolTipRole=description,
            StatusTipRole=description,
            TextAlignmentRole=(
                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
            ),
            SizeHintRole=QSize(24, 24),
        )


@define
class QtBoolField(BoolField, QtField[DBM]):
    def values(self, record: DBM) -> Dict[Qt.ItemDataRole, Any]:
        value = getattr(record, self.name)
        if value is None:
            return self.expand_value(None)
        return self.expand_value(
            value=value,
            DisplayRole=self.true_str if value else self.false_str,
            EditRole=value,
            ForegroundRole=QBrush(
                Qt.GlobalColor.blue if value else Qt.GlobalColor.red
            ),
        )


@define
class QtDateTimeField(QtField[DBM], DateTimeField):  # type: ignore
    formatter: Optional[MomentFormat] = field(default=None)

    def values(self, record) -> Dict[Qt.ItemDataRole, Any]:
        value = getattr(record, self.name)  # type: ignore[assignment]
        if value is None:
            return self.expand_value(None)  # type: ignore[no-untyped-call]

        if self.formatter is None:
            self.formatter = MomentFormat.from_string(
                self.format
            )  # type: ignore[assignment]

        display = self.formatter.moment_to_string(value)
        return self.expand_value(  # type: ignore[no-untyped-call]
            value=value,
            DisplayRole=display,
            EditRole=value,
            ToolTipRole=humanize.naturaltime(value),
        )


@define
class QtDateField(DateField, QtField[DBM]):
    formatter: Optional[MomentFormat] = field(default=None)

    def values(self, record) -> Dict[Qt.ItemDataRole, Any]:
        value = getattr(record, self.name)  # type: ignore[assignment]
        if value is None:
            return self.expand_value(None)  # type: ignore[no-untyped-call]

        if self.formatter is None:
            self.formatter = MomentFormat.from_string(
                self.format
            )  # type: ignore[assignment]

        display = self.formatter.moment_to_string(value)
        return self.expand_value(  # type: ignore[no-untyped-call]
            value=value,
            DisplayRole=display,
            EditRole=value,
            ToolTipRole=humanize.naturaldate(value),
        )


@define
class QtTimeField(TimeField, QtField[DBM]):
    formatter: Optional[MomentFormat] = field(default=None)

    def values(self, record) -> Dict[Qt.ItemDataRole, Any]:
        value = getattr(record, self.name)  # type: ignore[assignment]
        if value is None:
            return self.expand_value(None)  # type: ignore[no-untyped-call]

        if self.formatter is None:
            self.formatter = MomentFormat.from_string(
                self.format
            )  # type: ignore[assignment]

        display = self.formatter.moment_to_string(value)
        return self.expand_value(  # type: ignore[no-untyped-call]
            value=value,
            DisplayRole=display,
            EditRole=value,
            ToolTipRole=str(value),
        )


@define
class QtDurationField(DurationField, QtField[DBM]):
    def values(self, record) -> Dict[Qt.ItemDataRole, Any]:
        return self.not_implemented_values(record)


@define
class QtEnumField(EnumField, QtField[DBM]):
    def values(self, record) -> Dict[Qt.ItemDataRole, Any]:
        value = getattr(record, self.name)
        if value is None:
            return self.expand_value(None)

        if hasattr(value, "name"):
            # If the value is an Enum, we need to get its name
            value = value.name
        for k, v in self.enum_values:
            if k == value:
                return self.expand_value(
                    value=value,
                    DisplayRole=v,
                )

        logger.error(
            "EnumField %s got value %s that was not found in enum_values: %s",
            self.name,
            value,
            self.enum_values,
        )
        return self.expand_value(None)  # type: ignore[no-untyped-call]


@define
class QtFloatField(FloatField, QtField[DBM]):
    def values(self, record) -> Dict[Qt.ItemDataRole, Any]:
        value = getattr(record, self.name)  # type: ignore[assignment]
        if value is None:
            return self.expand_value(None)  # type: ignore[no-untyped-call]

        display = f"{(value * self.scale):.{self.precision}f}"
        if self.unit_symbol:
            display = f"{display} {self.unit_symbol}"

        tip = f"{(value * self.scale):.{self.precision}f}"
        if self.unit:
            tip = f"{tip} {self.unit}"

        color = Qt.GlobalColor.black

        if self.min:
            tip = f"{(self.min * self.scale):.{self.precision}f} <= {tip}"
            if value < self.min:
                color = Qt.GlobalColor.red
        if self.max:
            tip = f"{tip} <= {(self.max * self.scale):.{self.precision}f}"
            if value > self.max:
                color = Qt.GlobalColor.red

        return self.expand_value(
            value=value,
            DisplayRole=display,
            ToolTipRole=tip,
            StatusTipRole=tip,
            EditRole=value,
            ForegroundRole=QBrush(color),
            TextAlignmentRole=(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            ),
        )


@define
class QtIntegerField(IntField, QtField[DBM]):
    def values(self, record) -> Dict[Qt.ItemDataRole, Any]:
        value = getattr(record, self.name)  # type: ignore[assignment]
        if value is None:
            return self.expand_value(None)  # type: ignore[no-untyped-call]

        display = f"{value:,}"
        if self.unit_symbol:
            display = f"{display} {self.unit_symbol}"

        tip = f"{value:,}"
        if self.unit:
            tip = f"{tip} {self.unit}"

        color = Qt.GlobalColor.black

        if self.min:
            tip = f"{self.min} <= {tip}"
            if value < self.min:
                color = Qt.GlobalColor.red

        if self.max:
            tip = f"{tip} <= {self.max}"
            if value > self.max:
                color = Qt.GlobalColor.red

        return self.expand_value(
            value=value,
            DisplayRole=display,
            ToolTipRole=tip,
            StatusTipRole=tip,
            EditRole=value,
            ForegroundRole=QBrush(color),
            TextAlignmentRole=(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            ),
        )


@define
class QtStringField(StrField, QtField[DBM]):
    def values(self, record) -> Dict[Qt.ItemDataRole, Any]:
        value = getattr(record, self.name)  # type: ignore[assignment]
        if value is None:
            return self.expand_value(None)  # type: ignore[no-untyped-call]

        display = str(value).replace("\n", "\\n")
        if len(display) > 50:
            display = f"{display[:50]}..."

        tip = value
        if self.max_length:
            label = self.t("cmn.max_length", "Maximum length")
            tip = f"{label} = {self.max_length}\n{tip}"

        if self.min_length:
            label = self.t("cmn.min_length", "Minimum length")
            tip = f"{label} = {self.min_length}\n{tip}"

        return self.expand_value(
            value=value,
            DisplayRole=display,
            EditRole=value,
            ToolTipRole=value,
            StatusTipRole=value,
            TextAlignmentRole=(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            ),
            FontRole=italic_font if self.multiline else regular_font,
        )


@define
class QtStringListField(StrListField, QtField[DBM]):
    def values(self, record) -> Dict[Qt.ItemDataRole, Any]:
        value = getattr(record, self.name)  # type: ignore[assignment]
        if value is None:
            return self.expand_value(None)  # type: ignore[no-untyped-call]

        if len(value) == 0:
            display = "[]"
            tip = self.t("cmn.empty_list", "Empty list")
        else:
            display = f"[ {', '.join(value)} ]"
            tip = "\n".join(value)

        if len(display) > 50:
            display = f"{display[:50]}..."
        return self.expand_value(
            value=value,
            DisplayRole=display,
            EditRole=value,
            ToolTipRole=tip,
            StatusTipRole=tip,
        )


@define
class QtIntListField(IntListField, QtField[DBM]):
    def values(self, record) -> Dict[Qt.ItemDataRole, Any]:
        value = getattr(record, self.name)
        if value is None:
            return self.expand_value(None)

        if len(value) == 0:
            display = "[]"
            tip = self.t("cmn.empty_list", "Empty list")
        else:

            display = ", ".join([f"{v:,}" for v in value])
            tip = "\n".join([f"{v:,}{self.unit_symbol or ''}" for v in value])
        if len(display) > 50:
            display = f"{display[:50]}..."
        return self.expand_value(
            value=value,
            DisplayRole=display,
            EditRole=value,
            ToolTipRole=tip,
            StatusTipRole=tip,
        )


@define
class QtFloatListField(FloatListField, QtField[DBM]):
    def values(self, record) -> Dict[Qt.ItemDataRole, Any]:
        return self.not_implemented_values(record)


@define
class QtFormattedField(FormattedField, QtField[DBM]):
    def values(self, record) -> Dict[Qt.ItemDataRole, Any]:
        return self.not_implemented_values(record)


@define
class QtRefBaseField(RefBaseField, QtField[DBM]):
    def values(self, record) -> Dict[Qt.ItemDataRole, Any]:
        return self.not_implemented_values(record)


@define
class QtRefManyToOneField(RefManyToOneField, QtField[DBM]):
    def values(self, record) -> Dict[Qt.ItemDataRole, Any]:
        return self.not_implemented_values(record)


@define
class QtRefOneToManyField(RefOneToManyField, QtField[DBM]):
    show_n_labels: int = field(default=4)

    def values(self, record: DBM) -> Dict[Qt.ItemDataRole, Any]:
        """Compute the values for each role for this field.

        As this is a field that has multiple values, we ask the implementation
        to provide to helper methods to compute the ID and label for each
        of the items.

        The resulted edit role will have the list of IDs and the display role
        will have a comma-separated list of the labels. If the list is
        longer than `show_n_labels`, the last label will be "...",
        with the full list shown in the tooltip.
        """
        items = getattr(record, self.name)
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

    def part_id(self, record: Any) -> RecIdType:
        """Compute the ID for one of the components of the field."""
        raise NotImplementedError(
            "part_id is not implemented for QtRefOneToManyField"
        )

    def part_label(self, record: Any) -> str:
        """Compute the label for one of the components of the field."""
        raise NotImplementedError(
            "part_label is not implemented for QtRefOneToManyField"
        )


@define
class QtRefOneToOneField(RefOneToOneField, QtField[DBM]):
    def values(self, record) -> Dict[Qt.ItemDataRole, Any]:
        return self.not_implemented_values(record)


@define
class QtRefManyToManyField(RefManyToManyField, QtField[DBM]):
    def values(self, record) -> Dict[Qt.ItemDataRole, Any]:
        return self.not_implemented_values(record)


@define
class QtFilterField(FilterField, QtField[DBM]):
    def values(self, record) -> Dict[Qt.ItemDataRole, Any]:
        return self.not_implemented_values(record)


@define
class QtSortField(SortField, QtField[DBM]):
    def values(self, record) -> Dict[Qt.ItemDataRole, Any]:
        return self.not_implemented_values(record)
