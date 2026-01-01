from collections import OrderedDict
from typing import TYPE_CHECKING, List, Optional, Tuple, cast

from exdrf.constants import (
    FIELD_TYPE_BLOB,
    FIELD_TYPE_BOOL,
    FIELD_TYPE_DATE,
    FIELD_TYPE_DT,
    FIELD_TYPE_DURATION,
    FIELD_TYPE_ENUM,
    FIELD_TYPE_FLOAT,
    FIELD_TYPE_FLOAT_LIST,
    FIELD_TYPE_FORMATTED,
    FIELD_TYPE_INT_LIST,
    FIELD_TYPE_INTEGER,
    FIELD_TYPE_REF_ONE_TO_MANY,
    FIELD_TYPE_REF_ONE_TO_ONE,
    FIELD_TYPE_STRING,
    FIELD_TYPE_STRING_LIST,
    FIELD_TYPE_TIME,
)
from exdrf_util.task import Task, TaskState
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QButtonGroup,
    QDialog,
    QFormLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from exdrf_qt.context_use import QtUseContext
from exdrf_qt.controls.task_runner.task_runner_ui import Ui_TaskRunner

if TYPE_CHECKING:
    from exdrf_util.task import TaskParameter

    from exdrf_qt.context import QtContext


class QThreadVehicle(QThread):
    """A thread that executes a task."""

    progressChanged = pyqtSignal(int)
    stateChanged = pyqtSignal(object)

    def __init__(self, task: "Task", ctx: "QtContext"):
        super().__init__()
        self.task = task
        self.ctx = ctx

    def _on_progress_changed(self, task: "Task", progress: int):
        """The progress has changed."""
        self.progressChanged.emit(progress)

    def _on_state_changed(self, task: "Task", state: "TaskState"):
        """The state has changed."""
        self.stateChanged.emit(state)

    def run(self):
        """Execute the task."""
        self.task.on_progress_changed.append(self._on_progress_changed)
        self.task.on_state_changed.append(self._on_state_changed)
        try:
            self.task.execute(self.ctx)
        finally:
            self.task.on_progress_changed.remove(self._on_progress_changed)
            self.task.on_state_changed.remove(self._on_state_changed)


class TaskRunner(QWidget, QtUseContext, Ui_TaskRunner):
    """A widget that allows the user to run a task."""

    task: "Task"

    tabs: List[Tuple["QPushButton", "QWidget"]]
    params: List[Tuple["TaskParameter", "QWidget"]]
    worker: Optional[QThreadVehicle]

    stateChanged = pyqtSignal(object)
    shouldClose = pyqtSignal()
    shouldStart = pyqtSignal()
    shouldRestart = pyqtSignal()
    progressChanged = pyqtSignal(int)

    def __init__(
        self, ctx: "QtContext", task: "Task", parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.ctx = ctx
        self.setup_ui(self)
        self.task = task
        self.tabs = []
        self.params = []
        self.worker = None

        self.setWindowTitle(self.task.title)
        self.setWindowIcon(self.get_icon("fire"))

        self.c_cancel_button.clicked.connect(self._on_cancel_clicked)
        self.c_main_button.clicked.connect(self._on_main_clicked)
        self.stateChanged.connect(self._react_to_state)
        self.progressChanged.connect(self.c_progress.setValue)

        self.c_db_connection.populate_db_connections()
        self.populate_parameters()

        self._react_to_state(task.state)

    def _on_state_changed(self):
        """Handle state changes from parameter widgets."""

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
            # Validate all parameters before starting.
            errors = []
            for param, widget in self.params:
                error = widget.validate()
                if error:
                    errors.append(f"{param.title}: {error}")
            if errors:
                from PyQt5.QtWidgets import QMessageBox

                error_msg = "\n".join(errors)
                QMessageBox.warning(
                    self,
                    self.t("task_runner.validation.title", "Validation Error"),
                    self.t(
                        "task_runner.validation.message",
                        "Please fix the following errors:\n\n{errors}",
                        errors=error_msg,
                    ),
                )
                return
            self.shouldStart.emit()
        elif self.task.state in (
            TaskState.COMPLETED,
            TaskState.FAILED,
        ):
            self.shouldRestart.emit()
        else:
            raise ValueError(f"Invalid state: {self.task.state}")

    def populate_parameters(self):
        categories = self.task.params_by_category()
        if len(categories) == 0:
            self.c_task_tab.hide()
            return

        self.c_task_tab.show()

        b_index = 0

        # Tab-like navigation between categories and task.
        self.c_tab_group = QButtonGroup()
        self.c_tab_group.setExclusive(True)
        self.c_tab_group.addButton(self.c_task_tab, b_index)
        b_index += 1
        self.c_tab_group.idClicked.connect(self.c_stacked.setCurrentIndex)

        # This is the name of the first category after the task tab.
        c_name_default = self.t("task.parameters", "Parameters")

        # The user might have use this exact name.
        if c_name_default in categories:
            default_categ = categories[c_name_default]
            del categories[c_name_default]
        else:
            default_categ = OrderedDict()

        # We allow for both None and "" to signify the default category.
        if None in categories:
            default_categ.update(categories[None])  # type: ignore
            del categories[None]  # type: ignore
        if "" in categories:
            default_categ.update(categories[""])
            del categories[""]

        # Add this page if there's anything in it.
        if len(default_categ):
            self.create_page_for_category(
                c_name_default, default_categ, b_index
            )
            b_index += 1

        # Ad the other categories in order of their insertion.
        for category, parameters in categories.items():
            self.create_page_for_category(category, parameters, b_index)
            b_index += 1

    def create_bool_control(self, param: "TaskParameter") -> QWidget:
        """Create a control for a boolean parameter."""
        from exdrf_qt.controls.task_runner.bool_param import BoolParam

        return BoolParam(ctx=self.ctx, param=param, runner=self, parent=self)

    def create_string_control(self, param: "TaskParameter") -> QWidget:
        """Create a control for a string parameter."""
        from exdrf_qt.controls.task_runner.str_param import StrParam

        widget = StrParam(ctx=self.ctx, param=param, runner=self, parent=self)
        return widget.get_widget()

    def create_integer_control(self, param: "TaskParameter") -> QWidget:
        """Create a control for an integer parameter."""
        from exdrf_qt.controls.task_runner.int_param import IntParam

        widget = IntParam(ctx=self.ctx, param=param, runner=self, parent=self)
        return widget.get_widget()

    def create_float_control(self, param: "TaskParameter") -> QWidget:
        """Create a control for a float parameter."""
        from exdrf_qt.controls.task_runner.float_param import FloatParam

        widget = FloatParam(ctx=self.ctx, param=param, runner=self, parent=self)
        return widget.get_widget()

    def create_date_control(self, param: "TaskParameter") -> QWidget:
        """Create a control for a date parameter."""
        from exdrf_qt.controls.task_runner.date_param import DateParam

        return DateParam(ctx=self.ctx, param=param, runner=self, parent=self)

    def create_dt_control(self, param: "TaskParameter") -> QWidget:
        """Create a control for a datetime parameter."""
        from exdrf_qt.controls.task_runner.datetime_param import DateTimeParam

        return DateTimeParam(
            ctx=self.ctx, param=param, runner=self, parent=self
        )

    def create_time_control(self, param: "TaskParameter") -> QWidget:
        """Create a control for a time parameter."""
        from exdrf_qt.controls.task_runner.time_param import TimeParam

        return TimeParam(ctx=self.ctx, param=param, runner=self, parent=self)

    def create_duration_control(self, param: "TaskParameter") -> QWidget:
        """Create a control for a duration parameter."""
        from exdrf_qt.controls.task_runner.duration_param import DurationParam

        return DurationParam(
            ctx=self.ctx, param=param, runner=self, parent=self
        )

    def create_enum_control(self, param: "TaskParameter") -> QWidget:
        """Create a control for an enum parameter."""
        from exdrf_qt.controls.task_runner.enum_param import EnumParam

        return EnumParam(ctx=self.ctx, param=param, runner=self, parent=self)

    def create_formatted_control(self, param: "TaskParameter") -> QWidget:
        """Create a control for a formatted parameter."""
        from exdrf_qt.controls.task_runner.formatted_param import FormattedParam

        return FormattedParam(
            ctx=self.ctx, param=param, runner=self, parent=self
        )

    def create_blob_control(self, param: "TaskParameter") -> QWidget:
        """Create a control for a blob parameter."""
        from exdrf_qt.controls.task_runner.blob_param import BlobParam

        return BlobParam(ctx=self.ctx, param=param, runner=self, parent=self)

    def create_string_list_control(self, param: "TaskParameter") -> QWidget:
        """Create a control for a string list parameter."""
        from exdrf_qt.controls.task_runner.str_list_param import StrListParam

        return StrListParam(ctx=self.ctx, param=param, runner=self, parent=self)

    def create_int_list_control(self, param: "TaskParameter") -> QWidget:
        """Create a control for an integer list parameter."""
        from exdrf_qt.controls.task_runner.int_list_param import IntListParam

        return IntListParam(ctx=self.ctx, param=param, runner=self, parent=self)

    def create_float_list_control(self, param: "TaskParameter") -> QWidget:
        """Create a control for a float list parameter."""
        from exdrf_qt.controls.task_runner.float_list_param import (
            FloatListParam,
        )

        return FloatListParam(
            ctx=self.ctx, param=param, runner=self, parent=self
        )

    def create_ref_one_to_one_control(self, param: "TaskParameter") -> QWidget:
        """Create a control for a one-to-one reference parameter."""
        from exdrf_qt.controls.task_runner.ref_one_param import (
            RefOneToOneParam,
        )

        return RefOneToOneParam(
            ctx=self.ctx, param=param, runner=self, parent=self
        )

    def create_ref_one_to_many_control(self, param: "TaskParameter") -> QWidget:
        """Create a control for a one-to-many reference parameter."""
        from exdrf_qt.controls.task_runner.ref_many_param import (
            RefOneToManyParam,
        )

        return RefOneToManyParam(
            ctx=self.ctx, param=param, runner=self, parent=self
        )

    def create_control_for_parameter(
        self, param: "TaskParameter", parent: Optional[QWidget] = None
    ):
        """Create a control for a parameter."""
        if param.type_name == FIELD_TYPE_BOOL:
            w = self.create_bool_control(param)
        elif param.type_name == FIELD_TYPE_STRING:
            w = self.create_string_control(param)
        elif param.type_name == FIELD_TYPE_INTEGER:
            w = self.create_integer_control(param)
        elif param.type_name == FIELD_TYPE_FLOAT:
            w = self.create_float_control(param)
        elif param.type_name == FIELD_TYPE_DATE:
            w = self.create_date_control(param)
        elif param.type_name == FIELD_TYPE_DT:
            w = self.create_dt_control(param)
        elif param.type_name == FIELD_TYPE_TIME:
            w = self.create_time_control(param)
        elif param.type_name == FIELD_TYPE_DURATION:
            w = self.create_duration_control(param)
        elif param.type_name == FIELD_TYPE_ENUM:
            w = self.create_enum_control(param)
        elif param.type_name == FIELD_TYPE_FORMATTED:
            w = self.create_formatted_control(param)
        elif param.type_name == FIELD_TYPE_BLOB:
            w = self.create_blob_control(param)
        elif param.type_name == FIELD_TYPE_REF_ONE_TO_MANY:
            w = self.create_ref_one_to_many_control(param)
        elif param.type_name == FIELD_TYPE_REF_ONE_TO_ONE:
            w = self.create_ref_one_to_one_control(param)
        elif param.type_name == FIELD_TYPE_STRING_LIST:
            w = self.create_string_list_control(param)
        elif param.type_name == FIELD_TYPE_INT_LIST:
            w = self.create_int_list_control(param)
        elif param.type_name == FIELD_TYPE_FLOAT_LIST:
            w = self.create_float_list_control(param)
        else:
            raise ValueError(f"Invalid type: {param.type_name}")

        self.params.append((param, w))
        return w

    def create_page_for_category(
        self,
        title: str,
        controls: OrderedDict[str, "TaskParameter"],
        b_index: int,
    ):
        """Create a page and its tab button for a category."""
        # The page to be inserted in the stack and its layout.
        page = QWidget()
        lay = QFormLayout()
        lay.setContentsMargins(2, 2, 2, 2)
        lay.setSpacing(2)
        page.setLayout(lay)

        label_font = None

        for parameter in controls.values():
            lay.addRow(
                parameter.title, self.create_control_for_parameter(parameter)
            )
            if parameter.description:
                # Add the description right beneath the control.
                lbl = QLabel(parameter.description, self)
                lbl.setTextInteractionFlags(
                    cast(
                        "Qt.TextInteractionFlags",
                        Qt.TextInteractionFlag.TextSelectableByMouse
                        | Qt.TextInteractionFlag.TextSelectableByKeyboard,
                    )
                )
                lbl.setWordWrap(True)

                # Set italic font
                if label_font is None:
                    label_font = lbl.font()
                    label_font.setItalic(True)
                lbl.setFont(label_font)

                # Add 2px margin beneath the label
                lbl.setContentsMargins(0, 0, 0, 2)
                lay.addRow(lbl)

        # The tab button for the page.
        btn = QPushButton(title, self)
        btn.setCheckable(True)
        self.lay_tab.addWidget(btn)

        # Add the tab button to the group and the page to the stack.
        self.c_tab_group.addButton(btn, b_index)
        self.c_stacked.addWidget(page)
        self.tabs.append((btn, page))
        return page

    def on_progress_changed(self, progress: int):
        """The progress has changed."""
        if self.task.max_steps > 0:
            if self.c_progress.maximum() != 100:
                self.c_progress.setRange(0, 100)
            self.c_progress.setValue(progress)

    def execute_task(self):
        """Execute the task."""
        self.worker = QThreadVehicle(self.task, self.ctx)
        self.worker.finished.connect(self._on_task_finished)
        self.worker.stateChanged.connect(self.stateChanged)
        self.worker.progressChanged.connect(self.on_progress_changed)
        self.worker.start()

    def _on_task_finished(self):
        """The task has finished."""
        if self.worker is not None:
            worker = self.worker
            self.worker = None
            worker.wait()
            worker.deleteLater()
        if self.task.state == TaskState.FAILED:
            QMessageBox.critical(
                self,
                self.t("task_runner.error.title", "Error"),
                self.task.get_failed_message(self.ctx),
            )
        else:
            QMessageBox.information(
                self,
                self.t("task_runner.success.title", "Success"),
                self.task.get_success_message(self.ctx),
            )


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
        self.task_runner.shouldStart.connect(self.task_runner.execute_task)
