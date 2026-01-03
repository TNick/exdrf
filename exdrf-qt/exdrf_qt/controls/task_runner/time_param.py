from datetime import time
from typing import TYPE_CHECKING, Optional, TypedDict, cast

from PyQt5.QtCore import QTime
from PyQt5.QtWidgets import QTimeEdit, QWidget

from exdrf_qt.controls.task_runner.param_widget import (
    HasParamRunner,
    ParamWidget,
)

if TYPE_CHECKING:
    from exdrf_util.task import TaskParameter

    from exdrf_qt.context import QtContext


class TimeConfig(TypedDict, total=False):
    """Configuration for time parameters.

    Attributes:
        min: The minimum time.
        max: The maximum time.
        format: The time format string.
    """

    min: time
    max: time
    format: str


class TimeParam(QTimeEdit, ParamWidget):
    """Widget for time parameters.

    Attributes:
        ctx: The Qt context.
        runner: The task runner that contains this widget.
        param: The task parameter this widget represents.
    """

    ctx: "QtContext"
    runner: "HasParamRunner"
    param: "TaskParameter"

    def __init__(
        self,
        ctx: "QtContext",
        param: "TaskParameter",
        runner: "HasParamRunner",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.ctx = ctx
        self.runner = runner
        self.param = param

        config: TimeConfig = cast(TimeConfig, param.config)

        # Set minimum and maximum times if configured.
        min_val = config.get("min")
        max_val = config.get("max")
        if min_val is not None:
            self.setMinimumTime(
                QTime.fromString(min_val.isoformat(), "HH:mm:ss")
            )
        if max_val is not None:
            self.setMaximumTime(
                QTime.fromString(max_val.isoformat(), "HH:mm:ss")
            )

        # Set the display format.
        time_format = config.get("format", "HH:mm:ss")
        self.setDisplayFormat(time_format)

        # Set the initial time value.
        if param.value is not None:
            if isinstance(param.value, time):
                self.setTime(
                    QTime.fromString(param.value.isoformat(), "HH:mm:ss")
                )
            else:
                self.setTime(QTime.currentTime())
        else:
            self.setTime(QTime.currentTime())

        # Connect signals.
        self.timeChanged.connect(self._on_value_changed)
        self.timeChanged.connect(self.runner._on_state_changed)

    def _on_value_changed(self):
        """Update param.value when time changes."""
        qtime = self.time()
        self.param.value = time(qtime.hour(), qtime.minute(), qtime.second())

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

        config: TimeConfig = cast(TimeConfig, self.param.config)
        min_val = config.get("min")
        max_val = config.get("max")

        # Check minimum time constraint.
        if min_val is not None and self.param.value < min_val:
            return self.t(
                "task_runner.validation.time_min",
                "Time must be on or after {min}",
                min=min_val.isoformat(),
            )

        # Check maximum time constraint.
        if max_val is not None and self.param.value > max_val:
            return self.t(
                "task_runner.validation.time_max",
                "Time must be on or before {max}",
                max=max_val.isoformat(),
            )
        return None
