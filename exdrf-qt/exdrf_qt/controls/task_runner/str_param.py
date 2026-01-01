from typing import TYPE_CHECKING, List, Optional, Tuple, TypedDict, cast

from PyQt5.QtWidgets import QLineEdit, QTextEdit

from exdrf_qt.controls.task_runner.param_widget import ParamWidget

if TYPE_CHECKING:
    from exdrf_util.task import TaskParameter

    from exdrf_qt.context import QtContext
    from exdrf_qt.controls.task_runner.task_runner import TaskRunner


class StrConfig(TypedDict, total=False):
    """Configuration for string parameters.

    Attributes:
        multiline: Whether the string can span multiple lines.
        min_length: The minimum length.
        max_length: The maximum length.
        enum_values: List of (value, display_name) tuples.
    """

    multiline: bool
    min_length: int
    max_length: int
    enum_values: List[Tuple[str, str]]


class StrParam(QLineEdit, ParamWidget):
    """Widget for string parameters."""

    def __init__(
        self,
        ctx: "QtContext",
        param: "TaskParameter",
        runner: "TaskRunner",
        parent: Optional[QLineEdit] = None,
    ):
        super().__init__(parent)
        self.ctx = ctx
        self.runner = runner
        self.param = param

        config: StrConfig = cast(StrConfig, param.config)

        if config.get("multiline", False):
            text_edit = QTextEdit(parent)
            text_edit.setPlainText(str(param.value) if param.value else "")
            text_edit.textChanged.connect(self._on_multiline_value_changed)
            text_edit.textChanged.connect(self.runner._on_state_changed)
            self._multiline_widget = text_edit
        else:
            self.setText(str(param.value) if param.value else "")
            self.textChanged.connect(self._on_value_changed)
            self.textChanged.connect(self.runner._on_state_changed)
            self._multiline_widget = None

        enum_values = config.get("enum_values", [])
        if enum_values:
            from PyQt5.QtWidgets import QComboBox

            combo = QComboBox(parent)
            for value, display_name in enum_values:
                combo.addItem(display_name, value)
            if param.value:
                index = combo.findData(param.value)
                if index >= 0:
                    combo.setCurrentIndex(index)
            combo.currentIndexChanged.connect(self._on_enum_value_changed)
            combo.currentIndexChanged.connect(self.runner._on_state_changed)
            self._enum_widget = combo
        else:
            self._enum_widget = None

    def _on_value_changed(self):
        """Update param.value when text changes."""
        self.param.value = self.text()

    def _on_multiline_value_changed(self):
        """Update param.value when multiline text changes."""
        if self._multiline_widget is None:
            return
        self.param.value = self._multiline_widget.toPlainText()

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

        config: StrConfig = cast(StrConfig, self.param.config)
        min_length = config.get("min_length")
        max_length = config.get("max_length")

        value_str = str(self.param.value)
        if min_length is not None and len(value_str) < min_length:
            return self.t(
                "task_runner.validation.str_min_length",
                "String must be at least {min} characters",
                min=min_length,
            )
        if max_length is not None and len(value_str) > max_length:
            return self.t(
                "task_runner.validation.str_max_length",
                "String must be at most {max} characters",
                max=max_length,
            )
        return None

    def get_widget(self):
        """Get the actual widget to use."""
        if self._enum_widget:
            return self._enum_widget
        if self._multiline_widget:
            return self._multiline_widget
        return self
