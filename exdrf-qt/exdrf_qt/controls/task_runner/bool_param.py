from typing import TYPE_CHECKING, Optional, TypedDict

from PyQt5.QtWidgets import QCheckBox

from exdrf_qt.controls.task_runner.param_widget import ParamWidget

if TYPE_CHECKING:
    from exdrf_util.task import TaskParameter

    from exdrf_qt.context import QtContext
    from exdrf_qt.controls.task_runner.task_runner import TaskRunner


class BoolConfig(TypedDict, total=False):
    """Configuration for boolean parameters.

    Attributes:
        true_str: The string representation of True.
        false_str: The string representation of False.
    """

    true_str: str
    false_str: str


class BoolParam(QCheckBox, ParamWidget):
    """Widget for boolean parameters."""

    def __init__(
        self,
        ctx: "QtContext",
        param: "TaskParameter",
        runner: "TaskRunner",
        parent: Optional[QCheckBox] = None,
    ):
        super().__init__(parent)
        self.ctx = ctx
        self.runner = runner
        self.param = param

        self.setTristate(param.nullable)
        self.stateChanged.connect(self._on_value_changed)
        self.stateChanged.connect(self.runner._on_state_changed)

    def _on_value_changed(self):
        """Update param.value when state changes."""
        state = self.checkState()
        if state == 2:  # Qt.CheckState.PartiallyChecked
            self.param.value = None
        else:
            self.param.value = state == 1  # Qt.CheckState.Checked

    def validate_param(self) -> Optional[str]:
        """Validate the current value."""
        error = super().validate_param()
        if error:
            return error
        # Boolean values are always valid if not None (or if nullable).
        return None
