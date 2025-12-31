from typing import TYPE_CHECKING, Optional

from exdrf_util.task import Task, TaskState
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QWidget

from exdrf_qt.context_use import QtUseContext
from exdrf_qt.controls.task_runner.task_runner_ui import Ui_TaskRunner

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext


class TaskRunner(QWidget, QtUseContext, Ui_TaskRunner):
    """A widget that allows the user to run a task."""

    task: "Task"

    stateChanged = pyqtSignal(object)
    shouldClose = pyqtSignal()
    shouldStart = pyqtSignal()
    shouldRestart = pyqtSignal()

    def __init__(
        self, ctx: "QtContext", task: "Task", parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.ctx = ctx
        self.setup_ui(self)
        self.task = task

        self.setWindowTitle(self.task.title)
        self.setWindowIcon(self.get_icon("fire"))

        self.c_cancel_button.clicked.connect(self._on_cancel_clicked)
        self.c_main_button.clicked.connect(self._on_main_clicked)
        self.stateChanged.connect(self._react_to_state)

        self.c_db_connection.populate_db_connections()

        self._react_to_state(task.state)

    def _on_state_changed(self, task: "Task", state: "TaskState"):
        assert self.task is task
        self.stateChanged.emit(state)

    def _react_to_state(self, state: "TaskState"):
        if state == TaskState.INPUT:
            self.c_db_connection.setEnabled(True)
            self.c_progress.hide()

            self.c_main_button.setEnabled(True)
            self.c_main_button.setText(self.t("task.run", "Run"))

            self.c_cancel_button.setEnabled(True)
            self.c_cancel_button.setText(self.t("task.cancel", "Cancel"))

            self.lbl_description.setText(self.task.description)
        elif state == TaskState.PENDING:
            self.c_db_connection.setEnabled(False)

            self.c_main_button.setEnabled(False)
            self.c_main_button.setText(self.t("task.pending", "Pending..."))

            self.c_cancel_button.setEnabled(False)
            self.c_cancel_button.setText(self.t("task.cancel", "Cancel"))

            self.c_progress.show()
        elif state == TaskState.RUNNING:
            self.c_db_connection.setEnabled(False)

            self.c_main_button.setEnabled(False)
            self.c_main_button.setText(self.t("task.running", "Running..."))

            self.c_cancel_button.setEnabled(True)
            self.c_cancel_button.setText(self.t("task.cancel", "Cancel"))

            self.c_progress.show()
        elif state == TaskState.COMPLETED:
            self.c_db_connection.setEnabled(False)

            self.c_main_button.setEnabled(True)
            self.c_main_button.setText(self.t("task.restart", "Restart"))

            self.c_cancel_button.setEnabled(True)
            self.c_cancel_button.setText(self.t("task.cancel", "Cancel"))

            self.c_progress.hide()
            self.lbl_description.setText(
                self.task.get_success_message(self.ctx)
            )
        elif state == TaskState.FAILED:
            self.c_db_connection.setEnabled(False)

            self.c_main_button.setEnabled(True)
            self.c_main_button.setText(self.t("task.restart", "Restart"))

            self.c_cancel_button.setEnabled(True)
            self.c_cancel_button.setText(self.t("task.cancel", "Cancel"))

            self.c_progress.hide()
            self.lbl_description.setText(self.task.get_failed_message(self.ctx))
        else:
            raise ValueError(f"Invalid state: {state}")

    def _on_cancel_clicked(self):
        if self.task.state in (
            TaskState.INPUT,
            TaskState.COMPLETED,
            TaskState.FAILED,
        ):
            self.shouldClose.emit()
            return

        self.c_cancel_button.setText(self.t("task.cancelling", "Cancelling..."))
        self.c_cancel_button.setEnabled(False)
        self.c_main_button.setEnabled(False)
        self.task.should_stop = True

    def _on_main_clicked(self):
        if self.task.state == TaskState.INPUT:
            self.shouldStart.emit()
        elif self.task.state in (
            TaskState.COMPLETED,
            TaskState.FAILED,
        ):
            self.shouldRestart.emit()
        else:
            raise ValueError(f"Invalid state: {self.task.state}")


class TaskRunnerDlg(QDialog, QtUseContext):
    """A dialog that allows the user to run a task."""

    lay_main: "QVBoxLayout"
    task_runner: "TaskRunner"

    def __init__(
        self, ctx: "QtContext", task: "Task", parent: Optional[QDialog] = None
    ):
        super().__init__(parent)
        self.ctx = ctx

        self.lay_main = QVBoxLayout(self)
        self.lay_main.setContentsMargins(0, 0, 0, 0)
        self.lay_main.setSpacing(0)

        self.task_runner = TaskRunner(ctx, task)
        self.lay_main.addWidget(self.task_runner)

        self.setWindowTitle(self.task_runner.windowTitle())
        self.setWindowIcon(self.get_icon("fire"))

        self.task_runner.shouldClose.connect(self.reject)
