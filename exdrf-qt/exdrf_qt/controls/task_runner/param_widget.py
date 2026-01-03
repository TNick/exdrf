from typing import TYPE_CHECKING, Optional, Protocol

from exdrf_qt.context_use import QtUseContext

if TYPE_CHECKING:
    from exdrf_util.task import TaskParameter


class HasParamRunner(Protocol):
    """Protocol for objects that host parameter widgets.

    Parameter widgets expect a runner-like object with a ``_on_state_changed``
    method so they can signal that input state has changed.
    """

    def _on_state_changed(self) -> None:
        """Signal that the current input state has changed."""


class ParamWidget(QtUseContext):
    """Base class for parameter widgets.

    Attributes:
        param: The task parameter this widget represents.
        runner: The runner that contains this widget.
    """

    param: "TaskParameter"
    runner: "HasParamRunner"

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
