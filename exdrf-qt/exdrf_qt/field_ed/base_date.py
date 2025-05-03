from datetime import date, datetime, time
from typing import TYPE_CHECKING, List, TypeVar, Union

from attrs import define, field
from dateutil.relativedelta import relativedelta
from PyQt5.QtWidgets import (
    QAction,
    QCalendarWidget,
    QDialog,
    QDialogButtonBox,
    QVBoxLayout,
)

from exdrf_qt.context_use import QtUseContext
from exdrf_qt.field_ed.base_line import LineBase
from exdrf_qt.validator import ValidationResult

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext

T = TypeVar("T", date, datetime)

labels = {
    "YYYY": ("cmn.year", "Year"),
    "MM": ("cmn.month", "Month"),
    "DD": ("cmn.day", "Day"),
    "HH": ("cmn.hour", "Hour"),
    "mm": ("cmn.minute", "Minute"),
    "ss": ("cmn.second", "Second"),
    "SSS": ("cmn.millisecond", "Millisecond"),
    "literal": ("cmn.literal", "Text"),
}


@define
class Bit:
    """Represents one component of a date/time value.

    Attributes:
        start: The 0-based start index of the component in the date string.
        size: The size of the component in the date string.
        pattern: The string used to detect this component in the format string.
    """

    start: int = field(default=0)
    size: int = field(default=0, init=False)
    pattern: str = field(default="", init=False)

    @property
    def end(self) -> int:
        """Returns the end index of the component."""
        return self.start + self.size

    def set_part(self, value: T, part: str) -> T:
        """Modifies the value with the bit from the part."""
        raise NotImplementedError("Subclasses must implement this method.")

    def get_part(self, value: T) -> str:
        """Returns the value of the component from the given value."""
        raise NotImplementedError("Subclasses must implement this method.")

    def apply_offset(self, value: T, offset: int) -> T:
        """Applies an offset to the component value."""
        raise NotImplementedError("Subclasses must implement this method.")

    def validate(self, value: str) -> bool:
        """Validates the value of the component."""
        raise NotImplementedError("Subclasses must implement this method.")


@define
class YearBit(Bit):
    """Represents the year component of a date."""

    size: int = field(default=4, init=False)
    pattern: str = field(default="YYYY", init=False)

    def set_part(self, value: T, part: str) -> T:
        return value.replace(year=int(part))

    def get_part(self, value: T) -> str:
        return str(value.year)

    def apply_offset(self, value: T, offset: int) -> T:
        return value.replace(year=value.year + offset)

    def validate(self, value: str) -> bool:
        return (
            len(value) == self.size
            and value.isdigit()
            and 1900 <= int(value) <= 2100
        )


@define
class MonthBit(Bit):
    """Represents the month component of a date."""

    size: int = field(default=2, init=False)
    pattern: str = field(default="MM", init=False)

    def set_part(self, value: T, part: str) -> T:
        month = int(part)
        if month < 1 or month > 12:
            raise ValueError("Month must be between 1 and 12.")
        try:
            return value.replace(month=month)
        except ValueError:
            # Handle the case where the day is invalid for the new month
            return value.replace(month=month, day=1)

    def get_part(self, value: T) -> str:
        return str(value.month).zfill(2)

    def apply_offset(self, value: T, offset: int) -> T:
        return value + relativedelta(months=offset)

    def validate(self, value: str) -> bool:
        return (
            len(value) == self.size
            and value.isdigit()
            and 1 <= int(value) <= 12
        )


@define
class DayBit(Bit):
    """Represents the day component of a date."""

    size: int = field(default=2, init=False)
    pattern: str = field(default="DD", init=False)

    def set_part(self, value: T, part: str) -> T:
        day = int(part)
        if day < 1 or day > 31:
            raise ValueError("Day must be between 1 and 31.")
        return value.replace(day=day)

    def get_part(self, value: T) -> str:
        return str(value.day).zfill(2)

    def apply_offset(self, value: T, offset: int) -> T:
        return value + relativedelta(days=offset)

    def validate(self, value: str) -> bool:
        return (
            len(value) == self.size
            and value.isdigit()
            and 1 <= int(value) <= 31
        )


@define
class HourBit(Bit):
    """Represents the hour component of a date."""

    size: int = field(default=2, init=False)
    pattern: str = field(default="HH", init=False)

    def set_part(self, value: T, part: str) -> T:
        if not isinstance(value, datetime) and not isinstance(value, time):
            raise ValueError("HourBit requires a datetime value.")
        hour = int(part)
        if hour < 0 or hour > 23:
            raise ValueError("Hour must be between 0 and 23.")
        if isinstance(value, datetime):
            return value.replace(hour=hour)
        return time(
            hour=hour,
            minute=value.minute,
            second=value.second,
            microsecond=value.microsecond,
        )  # type: ignore[return-value]

    def get_part(self, value: T) -> str:
        if not isinstance(value, datetime) and not isinstance(value, time):
            raise ValueError("HourBit requires a datetime value.")
        return str(value.hour).zfill(2)

    def apply_offset(self, value: T, offset: int) -> T:
        if not isinstance(value, datetime) and not isinstance(value, time):
            raise ValueError("HourBit requires a datetime value.")
        return value + relativedelta(hours=offset)

    def validate(self, value: str) -> bool:
        return (
            len(value) == self.size
            and value.isdigit()
            and 0 <= int(value) <= 23
        )


@define
class MinuteBit(Bit):
    """Represents the minute component of a date."""

    size: int = field(default=2, init=False)
    pattern: str = field(default="mm", init=False)

    def set_part(self, value: T, part: str) -> T:
        if not isinstance(value, datetime) and not isinstance(value, time):
            raise ValueError("MinuteBit requires a datetime value.")
        minute = int(part)
        if minute < 0 or minute > 59:
            raise ValueError("Minute must be between 0 and 59.")
        if isinstance(value, datetime):
            return value.replace(minute=minute)
        return time(
            hour=value.hour,
            minute=minute,
            second=value.second,
            microsecond=value.microsecond,
        )  # type: ignore[return-value]

    def get_part(self, value: T) -> str:
        if not isinstance(value, datetime) and not isinstance(value, time):
            raise ValueError("MinuteBit requires a datetime value.")
        return str(value.minute).zfill(2)

    def apply_offset(self, value: T, offset: int) -> T:
        if not isinstance(value, datetime) and not isinstance(value, time):
            raise ValueError("MinuteBit requires a datetime value.")
        return value + relativedelta(minutes=offset)

    def validate(self, value: str) -> bool:
        return (
            len(value) == self.size
            and value.isdigit()
            and 0 <= int(value) <= 59
        )


@define
class SecondBit(Bit):
    """Represents the second component of a date."""

    size: int = field(default=2, init=False)
    pattern: str = field(default="ss", init=False)

    def set_part(self, value: T, part: str) -> T:
        if not isinstance(value, datetime) and not isinstance(value, time):
            raise ValueError("SecondBit requires a datetime value.")
        second = int(part)
        if second < 0 or second > 59:
            raise ValueError("Second must be between 0 and 59.")
        if isinstance(value, datetime):
            return value.replace(second=second)
        return time(
            hour=value.hour,
            minute=value.minute,
            second=second,
            microsecond=value.microsecond,
        )  # type: ignore[return-value]

    def get_part(self, value: T) -> str:
        if not isinstance(value, datetime) and not isinstance(value, time):
            raise ValueError("SecondBit requires a datetime value.")
        return str(value.second).zfill(2)

    def apply_offset(self, value: T, offset: int) -> T:
        if not isinstance(value, datetime) and not isinstance(value, time):
            raise ValueError("SecondBit requires a datetime value.")
        return value + relativedelta(seconds=offset)

    def validate(self, value: str) -> bool:
        return (
            len(value) == self.size
            and value.isdigit()
            and 0 <= int(value) <= 59
        )


@define
class MillisecondBit(Bit):
    """Represents the millisecond component of a date."""

    size: int = field(default=3, init=False)
    pattern: str = field(default="SSS", init=False)

    def set_part(self, value: T, part: str) -> T:
        if not isinstance(value, datetime) and not isinstance(value, time):
            raise ValueError("MillisecondBit requires a datetime value.")
        millisecond = int(part)
        if millisecond < 0 or millisecond > 999:
            raise ValueError("Millisecond must be between 0 and 999.")
        if isinstance(value, datetime):
            return value.replace(microsecond=millisecond * 1000)
        return time(
            hour=value.hour,
            minute=value.minute,
            second=value.second,
            microsecond=millisecond * 1000,
        )  # type: ignore[return-value]

    def get_part(self, value: T) -> str:
        if not isinstance(value, datetime) and not isinstance(value, time):
            raise ValueError("MillisecondBit requires a datetime value.")
        return str(value.microsecond // 1000).zfill(3)

    def apply_offset(self, value: T, offset: int) -> T:
        if not isinstance(value, datetime) and not isinstance(value, time):
            raise ValueError("MillisecondBit requires a datetime value.")
        return value + relativedelta(microseconds=offset * 1000)

    def validate(self, value: str) -> bool:
        return (
            len(value) == self.size
            and value.isdigit()
            and 0 <= int(value) <= 999
        )


@define
class LiteralBit(Bit):
    """Represents a literal component of a date."""

    value: str = field(default="")

    size: int = field(init=False)

    def __attrs_post_init__(self):
        """Sets the size of the literal component."""
        self.size = len(self.value)

    def set_part(self, value: T, part: str) -> T:
        return value

    def get_part(self, value: T) -> str:
        return self.value


@define
class MomentFormat(QtUseContext):
    """Represents a format string for date/time values.

    The format string is parsed into components, each of which represents a
    part of the date/time value. The components can be literals or specific
    date/time parts (year, month, day, hour, minute, second, millisecond).

    Each bit stores the position in the string where it starts and the size of
    the component. The `length` property returns the total length of the string.
    """

    ctx: "QtContext"
    components: List[Bit] = field(factory=list)

    @property
    def length(self) -> int:
        """Returns the total length of the format string."""
        return sum(component.size for component in self.components)

    def _load_moment(self, value: str, result: T) -> T:
        for component in self.components:
            content = value[component.start : component.end]  # noqa: E203
            if not content:
                raise ValueError(f"Invalid date format: {value}")
            if isinstance(component, LiteralBit):
                if content != component.value:
                    raise ValueError(f"Invalid date format: {value}")
            else:
                result = component.set_part(result, content)
        return result

    def string_to_date(self, value: str) -> date:
        """Parse a string into a date value using the format string.

        Args:
            value: The string to parse.

        Returns:
            A date object representing the parsed date.

        Throws:
            ValueError: If the string cannot be parsed into a date.
        """
        return self._load_moment(value, date.today())

    def string_to_datetime(self, value: str) -> datetime:
        """Parse a string into a date-time value using the format string.

        Args:
            value: The string to parse.

        Returns:
            A datetime object representing the parsed date-time.

        Throws:
            ValueError: If the string cannot be parsed into a date-time.
        """
        return self._load_moment(value, datetime.now())

    def moment_to_string(self, value: T) -> str:
        """Converts a date/time value to a string using the format string."""
        result = ""
        for component in self.components:
            result += component.get_part(value)
        return result

    def bit_at_position(self, position: int, inclusive: bool = False) -> Bit:
        """Returns the component at the given position.

        Args:
            position: The 0-based position in the format string.
        """
        if inclusive:
            for component in self.components:
                if position <= component.end:
                    return component
        else:
            for component in self.components:
                if position < component.end:
                    return component
        raise ValueError(f"No component found at position {position}.")

    def apply_offset(self, value: T, position: int, offset: int) -> T:
        """Applies an offset to the component at the given position.

        Args:
            value: The date or date/time value to modify.
            position: The 0-based position of the bit in the format string.
            offset: The offset to apply to the component.
        """
        component = self.bit_at_position(position, inclusive=True)
        if isinstance(component, LiteralBit):
            return value
        return component.apply_offset(value, offset)

    def validate(self, value: str) -> ValidationResult:
        result = ValidationResult(reason="FORMAT", value=datetime.now())
        expected_size = 0
        for component in self.components:
            expected_size += component.size
            content = value[component.start : component.end]  # noqa: E203
            if isinstance(component, LiteralBit):
                if content == component.value:
                    continue
                result.error = self.t(
                    "cmn.err.date.str",
                    "Expecting '{expect}' ({size}) at position "
                    "{pos} but got `{found}`",
                    expect=component.value,
                    pos=component.start,
                    found=content,
                    size=component.size,
                )
                return result

            if component.validate(content):
                result.value = component.set_part(
                    result.value, content  # type: ignore[assignment]
                )
                continue

            trk, def_lbl = labels[component.pattern]
            result.error = self.t(
                "cmn.err.date.int",
                "Expecting <{expect}> ({size}) at position "
                "{pos} but got `{found}`",
                expect=self.t(trk, def_lbl),
                pos=component.start,
                found=content,
                size=component.size,
            )
            return result

        if len(value) != expected_size:
            result.error = self.t(
                "cmn.err.date.size",
                "Extra characters at the end of the string: {extra}",
                extra=value[expected_size:],
            )
            return result
        return result

    @classmethod
    def from_string(cls, fmt: str, **kwargs) -> "MomentFormat":
        """Parses a format string and returns a MomentFormat object.

        The function accepts the following components:

        - YYYY: Year (4 digits)
        - MM: Month (2 digits)
        - DD: Day (2 digits)
        - HH: Hour (2 digits, 24-hour format)
        - mm: Minute (2 digits)
        - ss: Second (2 digits)
        - SSS: Millisecond (3 digits)

        Anything else is treated as a literal string.

        Args:
            fmt: The format string to parse.
        """
        result = cls(**kwargs)

        accumulator = ""

        def add_component(component: Bit) -> None:
            """Adds a component to the result."""
            nonlocal accumulator

            if len(accumulator) > 0:
                result.components.append(
                    LiteralBit(start=result.length, value=accumulator)
                )
                accumulator = ""

            component.start = result.length
            result.components.append(component)

        while fmt:
            if fmt.startswith("YYYY"):
                add_component(YearBit())
                fmt = fmt[4:]
            elif fmt.startswith("MM"):
                add_component(MonthBit())
                fmt = fmt[2:]
            elif fmt.startswith("DD"):
                add_component(DayBit())
                fmt = fmt[2:]
            elif fmt.startswith("HH"):
                add_component(HourBit())
                fmt = fmt[2:]
            elif fmt.startswith("mm"):
                add_component(MinuteBit())
                fmt = fmt[2:]
            elif fmt.startswith("ss"):
                add_component(SecondBit())
                fmt = fmt[2:]
            elif fmt.startswith("SSS"):
                add_component(MillisecondBit())
                fmt = fmt[3:]
            else:
                accumulator += fmt[0]
                fmt = fmt[1:]

        return result


class CalendarPopup(QDialog):
    """A dialog that shows a calendar widget for selecting a date."""

    calendar: QCalendarWidget
    bbox: QDialogButtonBox

    def __init__(self, current_date: T, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Date")

        # Create the calendar widget and set the selected date.
        self.calendar = QCalendarWidget(self)
        self.calendar.setGridVisible(True)
        self.calendar.setSelectedDate(current_date)

        # Add a button box with OK and Cancel buttons.
        self.bbox = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self
        )
        self.bbox.accepted.connect(self.accept)
        self.bbox.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.calendar)
        layout.addWidget(self.bbox)

    def selected_date(self) -> date:
        """Returns the selected date."""
        return self.calendar.selectedDate().toPyDate()


class DateBase(LineBase):
    """Base for classes that deal with date and time."""

    formatter: MomentFormat

    def __init__(
        self, format: Union[str, MomentFormat], parent=None, **kwargs
    ) -> None:
        super().__init__(parent, **kwargs)

        if isinstance(format, str):
            self.formatter = MomentFormat.from_string(format, ctx=self.ctx)
        else:
            self.formatter = format

        if self.nullable:
            self.add_clear_to_null_action()
        self.textChanged.connect(self._on_text_changed)

    def wheelEvent(self, event):  # type: ignore[override]
        if self.field_value is None:
            self.change_field_value(datetime.now())
        else:
            delta = event.angleDelta().y() // 120
            result = self.formatter.validate(self.text())
            if result.is_invalid:
                return
            prev_pos = self.cursorPosition()
            assert result.value is not None
            new_value = self.formatter.apply_offset(
                result.value, prev_pos, delta
            )
            self.change_field_value(new_value)
            self.setCursorPosition(prev_pos)

    def create_calendar_action(self):
        """Creates a calendar action for the line edit."""
        action = QAction(
            self.get_icon("calendar"),
            self.t("cmn.open_calendar", "Open Calendar"),
            self,
        )
        action.triggered.connect(self.open_calendar)
        self.ac_upload = action
        return action

    def open_calendar(self):
        """Opens a calendar dialog."""
        text = self.text()
        result = self.formatter.validate(text)
        if result.is_invalid:
            current_date = datetime.now()
        else:
            current_date = result.value

        calendar_dialog = CalendarPopup(
            current_date, self  # type: ignore[call-arg]
        )
        if calendar_dialog.exec_() == QDialog.Accepted:
            cal_date = calendar_dialog.selected_date()
            if isinstance(self.field_value, datetime):
                cal_date = datetime(
                    cal_date.year,
                    cal_date.month,
                    cal_date.day,
                    self.field_value.hour,
                    self.field_value.minute,
                    self.field_value.second,
                    self.field_value.microsecond,
                )
            self.change_field_value(cal_date)

    def _on_text_changed(self, text: str) -> None:
        """Handles text changes in the line edit."""
        if len(text) == 0:
            self.set_line_empty()
            return

        result = self.formatter.validate(text)
        if result.is_invalid:
            assert result.error is not None
            self.set_line_error(result.error)
        else:
            self.set_line_normal()

    def on_editing_finished(self) -> None:
        """Handles the editing finished signal."""
        text = self.text()
        if len(text) == 0:
            self.set_line_empty()
            return

        result = self.formatter.validate(text)
        if result.is_invalid:
            assert result.error is not None
            self.set_line_error(result.error)
        else:
            self.set_line_normal()

    def set_line_null(self):
        """Sets the value of the control to NULL.

        If the control does not support null values, the control will enter
        the error state.
        """
        self.field_value = None
        self.set_line_empty()
        if self.nullable:
            self.ac_clear.setEnabled(False)
