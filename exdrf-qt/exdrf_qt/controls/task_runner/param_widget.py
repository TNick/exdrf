from typing import TYPE_CHECKING, Optional

from exdrf_qt.context_use import QtUseContext

if TYPE_CHECKING:
    from exdrf_util.task import TaskParameter

    from exdrf_qt.controls.task_runner.task_runner import TaskRunner


class ParamWidget(QtUseContext):
    """Base class for parameter widgets.

    Attributes:
        param: The task parameter this widget represents.
        runner: The task runner that contains this widget.
    """

    param: "TaskParameter"
    runner: "TaskRunner"

    def validate_param(self) -> Optional[str]:
        """Validate the current value.

        Returns:
            An error message if the value is invalid, None if valid.
        """
        # Check if nullable and value is None.
        if not self.param.nullable and self.param.value is None:
            return self.t(
                "task_runner.validation.required",
                "This field is required",
            )
        return None
