from typing import TYPE_CHECKING, Literal, Optional, TypedDict, cast

from PyQt5.QtWidgets import QTextEdit

from exdrf_qt.controls.task_runner.param_widget import ParamWidget

if TYPE_CHECKING:
    from exdrf_util.task import TaskParameter

    from exdrf_qt.context import QtContext
    from exdrf_qt.controls.task_runner.task_runner import TaskRunner


class FormattedConfig(TypedDict, total=False):
    """Configuration for formatted parameters.

    Attributes:
        format: The format type.
    """

    format: Literal["json", "html", "xml"]


class FormattedParam(QTextEdit, ParamWidget):
    """Widget for formatted parameters (JSON, HTML, XML)."""

    def __init__(
        self,
        ctx: "QtContext",
        param: "TaskParameter",
        runner: "TaskRunner",
        parent: Optional[QTextEdit] = None,
    ):
        super().__init__(parent)
        self.ctx = ctx
        self.runner = runner
        self.param = param

        config: FormattedConfig = cast(FormattedConfig, param.config)
        format_type = config.get("format", "json")

        if param.value is not None:
            if isinstance(param.value, str):
                self.setPlainText(param.value)
            elif format_type == "html":
                self.setHtml(param.value)
            elif format_type == "xml":
                self.setPlainText(param.value)
            else:
                import json

                self.setPlainText(json.dumps(param.value))
        else:
            self.setPlainText("")

        self.textChanged.connect(self._on_value_changed)
        self.textChanged.connect(self.runner._on_state_changed)

    def _on_value_changed(self):
        """Update param.value when text changes."""
        self.param.value = self.toPlainText()

    def validate_param(self) -> Optional[str]:
        """Validate the current value."""
        error = super().validate_param()
        if error:
            return error
        # Formatted text is always valid if not None (or if nullable).
        return None
