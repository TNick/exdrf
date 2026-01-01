from datetime import datetime
from typing import TYPE_CHECKING, Optional, TypedDict, cast

from PyQt5.QtCore import QDateTime
from PyQt5.QtWidgets import QDateTimeEdit

from exdrf_qt.controls.task_runner.param_widget import ParamWidget

if TYPE_CHECKING:
    from exdrf_util.task import TaskParameter

    from exdrf_qt.context import QtContext
    from exdrf_qt.controls.task_runner.task_runner import TaskRunner


class DateTimeConfig(TypedDict, total=False):
    """Configuration for date-time parameters.

    Attributes:
        min: The minimum date-time.
        max: The maximum date-time.
        format: The date-time format string.
    """

    min: datetime
    max: datetime
    format: str


class DateTimeParam(QDateTimeEdit, ParamWidget):
    """Widget for date-time parameters.

    Attributes:
        ctx: The Qt context.
        runner: The task runner that contains this widget.
        param: The task parameter this widget represents.
    """

    ctx: "QtContext"
    runner: "TaskRunner"
    param: "TaskParameter"

    def __init__(
        self,
        ctx: "QtContext",
        param: "TaskParameter",
        runner: "TaskRunner",
        parent: Optional[QDateTimeEdit] = None,
    ):
        """Initialize the date-time parameter widget.

        Args:
            ctx: The Qt context.
            param: The task parameter this widget represents.
            runner: The task runner that contains this widget.
            parent: The parent widget.
        """
        super().__init__(parent)
        self.ctx = ctx
        self.runner = runner
        self.param = param

        config: DateTimeConfig = cast(DateTimeConfig, param.config)

        # Set minimum and maximum date-times if configured.
        min_val = config.get("min")
        max_val = config.get("max")
        if min_val is not None:
            qdt = QDateTime.fromString(
                min_val.isoformat(), "yyyy-MM-ddTHH:mm:ss"
            )
            self.setMinimumDateTime(qdt)
        if max_val is not None:
            qdt = QDateTime.fromString(
                max_val.isoformat(), "yyyy-MM-ddTHH:mm:ss"
            )
            self.setMaximumDateTime(qdt)

        # Set the display format.
        date_format = config.get("format", "DD-MM-YYYY HH:mm:ss")
        self.setDisplayFormat(date_format)

        # Set the initial date-time value.
        if param.value is not None:
            if isinstance(param.value, datetime):
                qdt = QDateTime.fromString(
                    param.value.isoformat(), "yyyy-MM-ddTHH:mm:ss"
                )
                self.setDateTime(qdt)
            else:
                self.setDateTime(QDateTime.currentDateTime())
        else:
            self.setDateTime(QDateTime.currentDateTime())

        # Connect signals.
        self.dateTimeChanged.connect(self._on_value_changed)
        self.dateTimeChanged.connect(self.runner._on_state_changed)

    def _on_value_changed(self):
        """Update param.value when datetime changes."""
        qdt = self.dateTime()
        self.param.value = datetime(
            qdt.date().year(),
            qdt.date().month(),
            qdt.date().day(),
            qdt.time().hour(),
            qdt.time().minute(),
            qdt.time().second(),
        )

    def validate_param(self) -> Optional[str]:
        """Validate the current value.

        Returns:
            An error message if the value is invalid, None if valid.
        """
        error = super().validate_param()
        if error:
            return error
        if self.param.value is None:
            return None

        config: DateTimeConfig = cast(DateTimeConfig, self.param.config)
        min_val = config.get("min")
        max_val = config.get("max")

        # Check minimum date-time constraint.
        if min_val is not None and self.param.value < min_val:
            return self.t(
                "task_runner.validation.datetime_min",
                "DateTime must be on or after {min}",
                min=min_val.isoformat(),
            )

        # Check maximum date-time constraint.
        if max_val is not None and self.param.value > max_val:
            return self.t(
                "task_runner.validation.datetime_max",
                "DateTime must be on or before {max}",
                max=max_val.isoformat(),
            )
        return None
