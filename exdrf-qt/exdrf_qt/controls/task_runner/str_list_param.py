from typing import TYPE_CHECKING, Optional

from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from exdrf_qt.controls.task_runner.param_widget import ParamWidget

if TYPE_CHECKING:
    from exdrf_util.task import TaskParameter

    from exdrf_qt.context import QtContext
    from exdrf_qt.controls.task_runner.task_runner import TaskRunner


class StrListParam(QWidget, ParamWidget):
    """Widget for string list parameters.

    Attributes:
        ctx: The Qt context.
        runner: The task runner that contains this widget.
        param: The task parameter this widget represents.
        _list: The list widget displaying the string values.
        _line_edit: The line edit for entering new values.
        _add_button: The button to add a value to the list.
        _remove_button: The button to remove the selected value.
    """

    ctx: "QtContext"
    runner: "TaskRunner"
    param: "TaskParameter"

    _list: QListWidget
    _line_edit: QLineEdit
    _add_button: QPushButton
    _remove_button: QPushButton

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

        # Create the main layout.
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create the list widget.
        self._list = QListWidget(self)
        layout.addWidget(self._list)

        # Create the add/remove controls layout.
        add_layout = QHBoxLayout()
        self._line_edit = QLineEdit(self)
        add_layout.addWidget(self._line_edit)

        # Create the add button.
        self._add_button = QPushButton(self.t("task_runner.add", "Add"), self)
        self._add_button.clicked.connect(self._on_add_clicked)
        add_layout.addWidget(self._add_button)

        # Create the remove button.
        self._remove_button = QPushButton(
            self.t("task_runner.remove", "Remove"), self
        )
        self._remove_button.clicked.connect(self._on_remove_clicked)
        add_layout.addWidget(self._remove_button)

        layout.addLayout(add_layout)

        # Populate the list with initial values if provided.
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
        """Handle the add button click event."""
        text = self._line_edit.text()
        if text:
            self._list.addItem(text)
            self._line_edit.clear()
            self._update_value()
            self.runner._on_state_changed()

    def _on_remove_clicked(self):
        """Handle the remove button click event."""
        current_item = self._list.currentItem()
        if current_item:
            self._list.takeItem(self._list.row(current_item))
            self._update_value()
            self.runner._on_state_changed()

    def _update_value(self):
        """Update param.value from the list widget contents."""
        values = []
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item:
                values.append(item.text())
        self.param.value = values
