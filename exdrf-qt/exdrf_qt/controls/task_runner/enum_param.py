from typing import TYPE_CHECKING, List, Optional, Tuple, TypedDict, cast

from PyQt5.QtWidgets import QComboBox

from exdrf_qt.controls.task_runner.param_widget import ParamWidget

if TYPE_CHECKING:
    from exdrf_util.task import TaskParameter

    from exdrf_qt.context import QtContext
    from exdrf_qt.controls.task_runner.task_runner import TaskRunner


class EnumConfig(TypedDict, total=False):
    """Configuration for enum parameters.

    Attributes:
        enum_values: List of (value, display_name) tuples.
    """

    enum_values: List[Tuple[str, str]]


class EnumParam(QComboBox, ParamWidget):
    """Widget for enum parameters.

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
        parent: Optional[QComboBox] = None,
    ):
        """Initialize the enum parameter widget.

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

        config: EnumConfig = cast(EnumConfig, param.config)
        enum_values = config.get("enum_values", [])

        # Populate the combo box with enum values.
        for value, display_name in enum_values:
            self.addItem(display_name, value)

        # Set the initial selection if a value is provided.
        if param.value is not None:
            index = self.findData(param.value)
            if index >= 0:
                self.setCurrentIndex(index)

        # Connect signals.
        self.currentIndexChanged.connect(self._on_value_changed)
        self.currentIndexChanged.connect(self.runner._on_state_changed)

    def _on_value_changed(self):
        """Update param.value when selection changes."""
        index = self.currentIndex()
        if index >= 0:
            self.param.value = self.itemData(index)
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
        # If nullable is False and no item is selected, it's invalid.
        if not self.param.nullable and self.currentIndex() < 0:
            return self.t(
                "task_runner.validation.enum_required",
                "Please select a value",
            )
        return None
