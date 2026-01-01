from typing import TYPE_CHECKING, List, Optional, Tuple, TypedDict, cast

from PyQt5.QtWidgets import QComboBox, QSpinBox

from exdrf_qt.controls.task_runner.param_widget import ParamWidget

if TYPE_CHECKING:
    from exdrf_util.task import TaskParameter

    from exdrf_qt.context import QtContext
    from exdrf_qt.controls.task_runner.task_runner import TaskRunner


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
    """Widget for integer parameters."""

    def __init__(
        self,
        ctx: "QtContext",
        param: "TaskParameter",
        runner: "TaskRunner",
        parent: Optional[QSpinBox] = None,
    ):
        super().__init__(parent)
        self.ctx = ctx
        self.runner = runner
        self.param = param

        config: IntConfig = cast(IntConfig, param.config)

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
        """Validate the current value."""
        error = super().validate_param()
        if error:
            return error
        if self.param.value is None:
            return None

        config: IntConfig = cast(IntConfig, self.param.config)
        min_val = config.get("min")
        max_val = config.get("max")

        if min_val is not None and self.param.value < min_val:
            return self.t(
                "task_runner.validation.int_min",
                "Value must be at least {min}",
                min=min_val,
            )
        if max_val is not None and self.param.value > max_val:
            return self.t(
                "task_runner.validation.int_max",
                "Value must be at most {max}",
                max=max_val,
            )
        return None

    def get_widget(self):
        """Get the actual widget to use."""
        if self._enum_widget:
            return self._enum_widget
        return self
