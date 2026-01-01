from typing import TYPE_CHECKING, Optional, TypedDict, cast

from PyQt5.QtWidgets import QDoubleSpinBox

from exdrf_qt.controls.task_runner.param_widget import ParamWidget

if TYPE_CHECKING:
    from exdrf_util.task import TaskParameter

    from exdrf_qt.context import QtContext
    from exdrf_qt.controls.task_runner.task_runner import TaskRunner


class DurationConfig(TypedDict, total=False):
    """Configuration for duration parameters.

    Attributes:
        min: The minimum duration.
        max: The maximum duration.
    """

    min: float
    max: float


class DurationParam(QDoubleSpinBox, ParamWidget):
    """Widget for duration parameters."""

    def __init__(
        self,
        ctx: "QtContext",
        param: "TaskParameter",
        runner: "TaskRunner",
        parent: Optional[QDoubleSpinBox] = None,
    ):
        super().__init__(parent)
        self.ctx = ctx
        self.runner = runner
        self.param = param

        config: DurationConfig = cast(DurationConfig, param.config)

        min_val = config.get("min")
        max_val = config.get("max")
        if min_val is not None:
            self.setMinimum(min_val)
        if max_val is not None:
            self.setMaximum(max_val)

        if param.value is not None:
            self.setValue(float(param.value))
        self.valueChanged.connect(self._on_value_changed)
        self.valueChanged.connect(self.runner._on_state_changed)

    def _on_value_changed(self):
        """Update param.value when value changes."""
        self.param.value = self.value()

    def validate_param(self) -> Optional[str]:
        """Validate the current value."""
        error = super().validate_param()
        if error:
            return error
        if self.param.value is None:
            return None

        config: DurationConfig = cast(DurationConfig, self.param.config)
        min_val = config.get("min")
        max_val = config.get("max")

        if min_val is not None and self.param.value < min_val:
            return self.t(
                "task_runner.validation.duration_min",
                "Duration must be at least {min}",
                min=min_val,
            )
        if max_val is not None and self.param.value > max_val:
            return self.t(
                "task_runner.validation.duration_max",
                "Duration must be at most {max}",
                max=max_val,
            )
        return None
