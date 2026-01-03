from typing import TYPE_CHECKING, List, Optional, Tuple, TypedDict, cast

from PyQt5.QtWidgets import QComboBox, QSpinBox, QWidget

from exdrf_qt.controls.task_runner.param_widget import (
    HasParamRunner,
    ParamWidget,
)

if TYPE_CHECKING:
    from exdrf_util.task import TaskParameter

    from exdrf_qt.context import QtContext


class IntConfig(TypedDict, total=False):
    """Configuration for integer parameters.

    Attributes:
        min: The minimum value.
        max: The maximum value.
        unit: The unit of measurement.
        unit_symbol: The symbol for the unit.
        enum_values: List of (value, display_name) tuples.
    """

    min: int
    max: int
    unit: str
    unit_symbol: str
    enum_values: List[Tuple[int, str]]


class IntParam(QSpinBox, ParamWidget):
    """Widget for integer parameters.

    Attributes:
        ctx: The Qt context.
        runner: The task runner that contains this widget.
        param: The task parameter this widget represents.
        _enum_widget: The combo box widget if enum values are configured,
            None otherwise.
    """

    ctx: "QtContext"
    runner: "HasParamRunner"
    param: "TaskParameter"

    _enum_widget: Optional[QComboBox]

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

        config: IntConfig = cast(IntConfig, param.config)

        # Check if enum values are configured.
        enum_values = config.get("enum_values", [])
        if enum_values:
            combo = QComboBox(parent)
            for value, display_name in enum_values:
                combo.addItem(display_name, value)
            if param.value is not None:
                index = combo.findData(param.value)
                if index >= 0:
                    combo.setCurrentIndex(index)
            combo.currentIndexChanged.connect(self._on_enum_value_changed)
            combo.currentIndexChanged.connect(self.runner._on_state_changed)
            self._enum_widget = combo
        else:
            # Configure the spin box with min/max values.
            min_val = config.get("min")
            max_val = config.get("max")
            if min_val is not None:
                self.setMinimum(min_val)
            if max_val is not None:
                self.setMaximum(max_val)
            if param.value is not None:
                self.setValue(param.value)
            self.valueChanged.connect(self._on_value_changed)
            self.valueChanged.connect(self.runner._on_state_changed)
            self._enum_widget = None

    def _on_value_changed(self):
        """Update param.value when value changes."""
        self.param.value = self.value()

    def _on_enum_value_changed(self):
        """Update param.value when enum selection changes."""
        if self._enum_widget is None:
            return
        index = self._enum_widget.currentIndex()
        if index >= 0:
            self.param.value = self._enum_widget.itemData(index)
        else:
            self.param.value = None

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

        config: IntConfig = cast(IntConfig, self.param.config)
        min_val = config.get("min")
        max_val = config.get("max")

        # Check minimum value constraint.
        if min_val is not None and self.param.value < min_val:
            return self.t(
                "task_runner.validation.int_min",
                "Value must be at least {min}",
                min=min_val,
            )

        # Check maximum value constraint.
        if max_val is not None and self.param.value > max_val:
            return self.t(
                "task_runner.validation.int_max",
                "Value must be at most {max}",
                max=max_val,
            )
        return None

    def get_widget(self):
        """Get the actual widget to use.

        Returns:
            The enum widget if configured, otherwise self.
        """
        if self._enum_widget:
            return self._enum_widget
        return self
