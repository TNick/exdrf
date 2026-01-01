from datetime import date
from typing import TYPE_CHECKING, Optional, TypedDict, cast

from PyQt5.QtCore import QDate
from PyQt5.QtWidgets import QDateEdit

from exdrf_qt.controls.task_runner.param_widget import ParamWidget

if TYPE_CHECKING:
    from exdrf_util.task import TaskParameter

    from exdrf_qt.context import QtContext
    from exdrf_qt.controls.task_runner.task_runner import TaskRunner


class DateConfig(TypedDict, total=False):
    """Configuration for date parameters.

    Attributes:
        min: The minimum date.
        max: The maximum date.
        format: The date format string.
    """

    min: date
    max: date
    format: str


class DateParam(QDateEdit, ParamWidget):
    """Widget for date parameters.

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
        parent: Optional[QDateEdit] = None,
    ):
        """Initialize the date parameter widget.

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

        config: DateConfig = cast(DateConfig, param.config)

        # Set minimum and maximum dates if configured.
        min_val = config.get("min")
        max_val = config.get("max")
        if min_val is not None:
            self.setMinimumDate(
                QDate.fromString(min_val.isoformat(), "yyyy-MM-dd")
            )
        if max_val is not None:
            self.setMaximumDate(
                QDate.fromString(max_val.isoformat(), "yyyy-MM-dd")
            )

        # Set the display format.
        date_format = config.get("format", "DD-MM-YYYY")
        self.setDisplayFormat(date_format)

        # Set the initial date value.
        if param.value is not None:
            if isinstance(param.value, date):
                self.setDate(
                    QDate.fromString(param.value.isoformat(), "yyyy-MM-dd")
                )
            else:
                self.setDate(QDate.currentDate())
        else:
            self.setDate(QDate.currentDate())

        # Connect signals.
        self.dateChanged.connect(self._on_value_changed)
        self.dateChanged.connect(self.runner._on_state_changed)

    def _on_value_changed(self):
        """Update param.value when date changes."""
        qdate = self.date()
        self.param.value = date(qdate.year(), qdate.month(), qdate.day())

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

        config: DateConfig = cast(DateConfig, self.param.config)
        min_val = config.get("min")
        max_val = config.get("max")

        # Check minimum date constraint.
        if min_val is not None and self.param.value < min_val:
            return self.t(
                "task_runner.validation.date_min",
                "Date must be on or after {min}",
                min=min_val.isoformat(),
            )

        # Check maximum date constraint.
        if max_val is not None and self.param.value > max_val:
            return self.t(
                "task_runner.validation.date_max",
                "Date must be on or before {max}",
                max=max_val.isoformat(),
            )
        return None
