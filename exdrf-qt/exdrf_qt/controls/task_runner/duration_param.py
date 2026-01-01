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
    """Widget for duration parameters.

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
        parent: Optional[QDoubleSpinBox] = None,
    ):
        """Initialize the duration parameter widget.

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

        config: DurationConfig = cast(DurationConfig, param.config)

        # Set minimum and maximum values if configured.
        min_val = config.get("min")
        max_val = config.get("max")
        if min_val is not None:
            self.setMinimum(min_val)
        if max_val is not None:
            self.setMaximum(max_val)

        # Set the initial value if provided.
        if param.value is not None:
            self.setValue(float(param.value))

        # Connect signals.
        self.valueChanged.connect(self._on_value_changed)
        self.valueChanged.connect(self.runner._on_state_changed)

    def _on_value_changed(self):
        """Update param.value when value changes."""
        self.param.value = self.value()

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

        config: DurationConfig = cast(DurationConfig, self.param.config)
        min_val = config.get("min")
        max_val = config.get("max")

        # Check minimum duration constraint.
        if min_val is not None and self.param.value < min_val:
            return self.t(
                "task_runner.validation.duration_min",
                "Duration must be at least {min}",
                min=min_val,
            )

        # Check maximum duration constraint.
        if max_val is not None and self.param.value > max_val:
            return self.t(
                "task_runner.validation.duration_max",
                "Duration must be at most {max}",
                max=max_val,
            )
        return None
