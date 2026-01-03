from typing import TYPE_CHECKING, Optional, TypedDict

from PyQt5.QtWidgets import QCheckBox, QWidget

from exdrf_qt.controls.task_runner.param_widget import (
    HasParamRunner,
    ParamWidget,
)

if TYPE_CHECKING:
    from exdrf_util.task import TaskParameter

    from exdrf_qt.context import QtContext


class BoolConfig(TypedDict, total=False):
    """Configuration for boolean parameters.

    Attributes:
        true_str: The string representation of True.
        false_str: The string representation of False.
    """

    true_str: str
    false_str: str


class BoolParam(QCheckBox, ParamWidget):
    """Widget for boolean parameters.

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
        """Initialize the boolean parameter widget.

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

        # Configure tristate mode and connect signals.
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
