from typing import TYPE_CHECKING, Optional, TypedDict, cast

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
    """Widget for blob parameters.

    Attributes:
        ctx: The Qt context.
        runner: The task runner that contains this widget.
        param: The task parameter this widget represents.
        _label: The label displaying the selected file path.
        _button: The browse button.
    """

    ctx: "QtContext"
    runner: "TaskRunner"
    param: "TaskParameter"

    _label: QLabel
    _button: QPushButton

    def __init__(
        self,
        ctx: "QtContext",
        param: "TaskParameter",
        runner: "TaskRunner",
        parent: Optional[QWidget] = None,
    ):
        """Initialize the blob parameter widget.

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

        # Create the layout and set margins.
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create and configure the label.
        self._label = QLabel(self)
        self._label.setText(
            self.t("task_runner.no_file_selected", "No file selected")
        )
        layout.addWidget(self._label)

        # Create and configure the browse button.
        self._button = QPushButton(
            self.t("task_runner.browse", "Browse..."), self
        )
        self._button.clicked.connect(self._on_browse_clicked)
        layout.addWidget(self._button)

        # Set initial value if provided.
        if param.value is not None:
            if isinstance(param.value, str):
                self._label.setText(param.value)
            else:
                self._label.setText(
                    self.t("task_runner.file_selected", "File selected")
                )

    def _on_browse_clicked(self):
        """Handle the browse button click event."""
        config: BlobConfig = cast(BlobConfig, self.param.config)
        mime_type = config.get("mime_type", "")

        # Build the file filter string.
        if mime_type:
            filter_str = self.t(
                "task_runner.mime_type_files",
                f"{mime_type} Files (*.*)",
            )
        else:
            filter_str = self.t("task_runner.all_files", "All Files (*.*)")

        # Show the file dialog.
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.t("task_runner.select_file", "Select File"),
            "",
            filter_str,
        )

        # Update the label and parameter value if a file was selected.
        if file_path:
            self._label.setText(file_path)
            self.param.value = file_path
            self.runner._on_state_changed()
