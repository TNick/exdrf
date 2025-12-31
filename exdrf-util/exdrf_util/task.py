import logging
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Callable, List, Optional

from attrs import define, field

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext

logger = logging.getLogger(__name__)


class TaskState(StrEnum):
    """The state of a task.

    Attributes:
        INPUT: The task is being configured.
        PENDING: The task is waiting to be run.
        RUNNING: The task is running.
        COMPLETED: The task has completed.
        FAILED: The task has failed.
    """

    INPUT = "input"
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


def on_state_changed(obj: "Task", attr, other: "TaskState") -> Any:
    """Callback for when the state of the task changes."""
    logger.debug("State changed to %s", other)

    for callback in obj.on_state_changed:
        callback(obj, other)
    return other


def on_progress_changed(obj: "Task", attr, other: int) -> Any:
    """Callback for when the state of the task changes."""
    if not isinstance(other, int):
        logger.error("Progress must be an integer. %s", other)
        return other
    if other < 0 or other > 100:
        logger.error("Progress must be between 0 and 100. %s", other)
        return other

    logger.debug("Progress changed to %s", other)

    for callback in obj.on_progress_changed:
        callback(obj, other)
    return other


@define(slots=True, kw_only=True)
class Task:
    """A task to be run."""

    title: str
    description: str = field(default="", repr=False)
    should_stop: bool = field(default=False, repr=False, init=False)

    state: TaskState = field(
        default=TaskState.INPUT, on_setattr=on_state_changed
    )
    on_state_changed: List[Callable[["Task", "TaskState"], None]] = field(
        factory=list, repr=False
    )

    progress: int = field(
        default=-1,
        repr=False,
        on_setattr=on_progress_changed,
    )
    on_progress_changed: List[Callable[["Task", int], None]] = field(
        factory=list, repr=False
    )

    step: int = field(default=-1, repr=False)

    def get_success_message(self, ctx: "QtContext") -> str:
        """Get the success message for the task."""
        return ctx.t("task.success", "Task completed successfully.")

    def get_failed_message(self, ctx: "QtContext") -> str:
        """Get the failed message for the task."""
        return ctx.t("task.failed", "Task failed.")

    def prepare(self, ctx: "QtContext") -> bool:
        """Prepare the task."""
        return True

    def cleanup(self, ctx: "QtContext") -> bool:
        """Cleanup the task."""
        return True

    def execute_step(self, ctx: "QtContext") -> Any:
        """Execute one step in the task."""
        raise NotImplementedError("Subclasses must implement this method.")

    def handle_exception(self, e: Exception) -> bool:
        """Handle an exception that occurred during the task execution."""
        logger.error(
            "Error executing task %s: %s", self.title, e, exc_info=True
        )
        return False

    def execute(self, ctx: "QtContext") -> Any:
        """Execute the task."""
        logger.debug("Executing task %s", self.title)

        self.state = TaskState.RUNNING
        self.progress = -1
        self.step = -1

        try:
            prepare_result = self.prepare(ctx)
        except Exception as e:
            logger.error(
                "Exception while preparing the task %s: %s",
                self.title,
                e,
                exc_info=True,
            )
            prepare_result = False

        if not prepare_result:
            self.state = TaskState.FAILED
            self.progress = 100
            return

        while not self.should_stop:
            try:
                self.step += 1
                self.execute_step(ctx)
            except Exception as e:
                if self.handle_exception(e):
                    continue

                self.state = TaskState.FAILED
                self.progress = 100
                return

        try:
            cleanup_result = self.cleanup(ctx)
        except Exception as e:
            logger.error(
                "Exception while cleaning up the task %s: %s",
                self.title,
                e,
                exc_info=True,
            )
            cleanup_result = False

        if not cleanup_result:
            self.state = TaskState.FAILED
            self.progress = 100
            return

        self.state = TaskState.COMPLETED
        self.progress = 100
        logger.debug("Task %s completed", self.title)


@define(slots=True, kw_only=True)
class FuncTask(Task):
    """Helper for implementing class-less tasks.

    Attributes:
        success_message: The message to display when the task completes
            successfully. If not provided, the default message will be used.
        failed_message: The message to display when the task fails.
            If not provided, the default message will be used.
        prepare_func: The function to call to prepare the task.
        cleanup_func: The function to call to cleanup the task.
        step_func: The function to call to execute one step in the task.

    """

    success_message: str = field(default="", repr=False)
    failed_message: str = field(default="", repr=False)
    prepare_func: Optional[Callable[["FuncTask", "QtContext"], bool]] = field(
        default=None, repr=False
    )
    cleanup_func: Optional[Callable[["FuncTask", "QtContext"], bool]] = field(
        default=None, repr=False
    )
    step_func: Callable[["FuncTask", "QtContext"], Any] = field(
        default=None, repr=False
    )

    def get_success_message(self, ctx: "QtContext") -> str:
        """Get the success message for the task."""
        return (
            self.success_message
            if self.success_message
            else super().get_success_message(ctx)
        )

    def get_failed_message(self, ctx: "QtContext") -> str:
        """Get the failed message for the task."""
        return (
            self.failed_message
            if self.failed_message
            else super().get_failed_message(ctx)
        )

    def prepare(self, ctx: "QtContext") -> bool:
        """Prepare the task."""
        if self.prepare_func:
            return self.prepare_func(self, ctx)
        return True

    def cleanup(self, ctx: "QtContext") -> bool:
        """Cleanup the task."""
        return self.cleanup_func(self, ctx) if self.cleanup_func else True

    def execute_step(self, ctx: "QtContext") -> None:
        """Execute one step in the task."""
        self.step_func(self, ctx)
