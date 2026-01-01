from typing import TYPE_CHECKING, Optional, TypedDict

from PyQt5.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)

from exdrf_qt.controls.task_runner.param_widget import ParamWidget

if TYPE_CHECKING:
    from exdrf_util.task import TaskParameter

    from exdrf_qt.context import QtContext
    from exdrf_qt.controls.task_runner.task_runner import TaskRunner


class BlobConfig(TypedDict, total=False):
    """Configuration for blob parameters.

    Attributes:
        mime_type: The MIME type of the data.
    """

    mime_type: str


class BlobParam(QWidget, ParamWidget):
    """Widget for blob parameters."""

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

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._label = QLabel(self)
        self._label.setText(
            self.t("task_runner.no_file_selected", "No file selected")
        )
        layout.addWidget(self._label)

        self._button = QPushButton(
            self.t("task_runner.browse", "Browse..."), self
        )
        self._button.clicked.connect(self._on_browse_clicked)
        layout.addWidget(self._button)

        if param.value is not None:
            if isinstance(param.value, str):
                self._label.setText(param.value)
            else:
                self._label.setText(
                    self.t("task_runner.file_selected", "File selected")
                )

    def _on_browse_clicked(self):
        config: BlobConfig = self.param.config
        mime_type = config.get("mime_type", "")

        if mime_type:
            filter_str = self.t(
                "task_runner.mime_type_files",
                "%s Files (*.*)",
                {"mime_type": mime_type},
            )
        else:
            filter_str = self.t("task_runner.all_files", "All Files (*.*)")
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.t("task_runner.select_file", "Select File"),
            "",
            filter_str,
        )
        if file_path:
            self._label.setText(file_path)
            self.param.value = file_path
            self.runner._on_state_changed()

    def validate_param(self) -> Optional[str]:
        """Validate the current value."""
        error = super().validate_param()
        if error:
            return error
        # Blob/file path is always valid if not None (or if nullable).
        return None
