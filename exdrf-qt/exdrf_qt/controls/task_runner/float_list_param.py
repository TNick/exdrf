from typing import TYPE_CHECKING, Optional, cast

from PyQt5.QtWidgets import (
    QDoubleSpinBox,
    QHBoxLayout,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from exdrf_qt.controls.task_runner.float_param import FloatConfig
from exdrf_qt.controls.task_runner.param_widget import ParamWidget

if TYPE_CHECKING:
    from exdrf_util.task import TaskParameter

    from exdrf_qt.context import QtContext
    from exdrf_qt.controls.task_runner.task_runner import TaskRunner


class FloatListParam(QWidget, ParamWidget):
    """Widget for float list parameters."""

    def __init__(
        self,
        ctx: "QtContext",
        param: "TaskParameter",
        runner: "TaskRunner",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.ctx = ctx
        self.runner = runner
        self.param = param

        config: FloatConfig = cast(FloatConfig, param.config)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._list = QListWidget(self)
        layout.addWidget(self._list)

        add_layout = QHBoxLayout()
        self._spin_box = QDoubleSpinBox(self)
        min_val = config.get("min")
        max_val = config.get("max")
        scale = config.get("scale", 1)
        if min_val is not None:
            self._spin_box.setMinimum(min_val)
        if max_val is not None:
            self._spin_box.setMaximum(max_val)
        self._spin_box.setDecimals(scale)
        add_layout.addWidget(self._spin_box)

        self._add_button = QPushButton(self.t("task_runner.add", "Add"), self)
        self._add_button.clicked.connect(self._on_add_clicked)
        add_layout.addWidget(self._add_button)

        self._remove_button = QPushButton(
            self.t("task_runner.remove", "Remove"), self
        )
        self._remove_button.clicked.connect(self._on_remove_clicked)
        add_layout.addWidget(self._remove_button)

        layout.addLayout(add_layout)

        if param.value is not None:
            if isinstance(param.value, list):
                for item in param.value:
                    self._list.addItem(str(item))
            else:
                self._list.addItem(str(param.value))

        self._list.itemChanged.connect(self._on_item_changed)
        self._list.itemChanged.connect(self.runner._on_state_changed)

    def _on_item_changed(self):
        """Update param.value when list item changes."""
        self._update_value()

    def _on_add_clicked(self):
        value = self._spin_box.value()
        self._list.addItem(str(value))
        self._update_value()
        self.runner._on_state_changed()

    def _on_remove_clicked(self):
        current_item = self._list.currentItem()
        if current_item:
            self._list.takeItem(self._list.row(current_item))
            self._update_value()
            self.runner._on_state_changed()

    def _update_value(self):
        values = []
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item:
                try:
                    values.append(float(item.text()))
                except ValueError:
                    pass
        self.param.value = values

    def validate_param(self) -> Optional[str]:
        """Validate the current value."""
        error = super().validate_param()
        if error:
            return error
        if self.param.value is None:
            return None

        # Check if all items are valid floats and within min/max.
        config: FloatConfig = cast(FloatConfig, self.param.config)
        min_val = config.get("min")
        max_val = config.get("max")

        for i, value in enumerate(self.param.value):
            if min_val is not None and value < min_val:
                return self.t(
                    "task_runner.validation.float_list_min",
                    "Item {index} must be at least {min}",
                    index=i + 1,
                    min=min_val,
                )
            if max_val is not None and value > max_val:
                return self.t(
                    "task_runner.validation.float_list_max",
                    "Item {index} must be at most {max}",
                    index=i + 1,
                    max=max_val,
                )
        return None
