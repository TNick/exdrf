import logging
from collections import OrderedDict, defaultdict
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Literal, Optional

from attrs import define, field
from exdrf.field import ExFieldBase

if TYPE_CHECKING:
    from exdrf_util.typedefs import HasBasicContext, HasTranslate

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
    if not -1 <= other <= 100:
        logger.error("Progress must be between 0 and 100. %s", other)
        return other

    logger.log(1, "Progress changed to %s", other)

    for callback in obj.on_progress_changed:
        callback(obj, other)
    return other


@define(slots=True, kw_only=True)
class TaskParameter(ExFieldBase):
    value: Any = field(default=None, repr=False)
    config: Dict[str, Any] = field(factory=dict, repr=False)


@define(slots=True, kw_only=True)
class Task:
    """A task to be run.

    Attributes:
        title: The title of the task.
        description: The description of the task.
        parameters: The parameters of the task that the user needs to fill in
            before the task can be run.
        should_stop: Whether the task should stop. The inner logic of the task
            should periodically check this flag and stop if it is set to True.
        state: The state of the task.
        on_state_changed: The callbacks to call when the state of the task
            changes.
        progress: The progress of the task in the range of 0 to 100.
        on_progress_changed: The callbacks to call when the progress of the
            task changes.
        step: The current step of the task.
        max_steps: The maximum number of steps in the task. This is usually
            computed in the prepare function. If greater than zero the default
            implementation will calculate the progress based on the step and the
            max_steps.
        global_session: Whether to use a global session for the task. If True,
            the prepare, execute and cleanup functions will be wrapped in a
            same_session context manager.
        data: The data of the task. The task can use this to store data that
            needs to be persisted between the steps of the task.
    """

    title: str
    description: str = field(default="", repr=False)
    parameters: Dict[str, "TaskParameter"] = field(
        factory=OrderedDict, repr=False
    )
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
    max_steps: int = field(default=-1, repr=False)

    global_session: bool = field(default=True, repr=False)
    data: Dict[str, Any] = field(factory=dict, repr=False)

    def get_success_message(self, ctx: "HasTranslate") -> str:
        """Get the success message for the task."""
        return ctx.t("task.success", "Task completed successfully.")

    def get_failed_message(self, ctx: "HasTranslate") -> str:
        """Get the failed message for the task."""
        return ctx.t("task.failed", "Task failed.")

    def prepare_task(self, ctx: "HasTranslate") -> bool:
        """Prepare the task."""
        return True

    def cleanup_task(self, ctx: "HasTranslate") -> bool:
        """Cleanup the task."""
        return True

    def prepare_step(self, ctx: "HasTranslate") -> None:
        """Prepare the task."""

    def cleanup_step(self, ctx: "HasTranslate") -> None:
        """Cleanup the task."""

    def execute_step(self, ctx: "HasTranslate") -> Any:
        """Execute one step in the task."""
        raise NotImplementedError("Subclasses must implement this method.")

    def handle_exception(
        self,
        ctx: "HasTranslate",
        e: Exception,
        stage: Literal["prepare", "execute", "cleanup"],
    ) -> bool:
        """Handle an exception that occurred during the task execution."""
        logger.error(
            "Error executing task %s in stage %s: %s",
            self.title,
            stage,
            e,
            exc_info=True,
        )
        return False

    def execute(self, ctx: "HasBasicContext") -> None:
        """Execute the task."""
        logger.debug("Executing task %s", self.title)

        self.state = TaskState.RUNNING
        self.progress = -1
        self.step = -1

        if self.global_session:
            with ctx.same_session():
                self._execute(ctx)
        else:
            self._execute(ctx)

        self.progress = 100
        logger.debug("Task %s finished with state %s", self.title, self.state)

    def _execute(self, ctx: "HasTranslate") -> Any:
        # Initialization stage.
        try:
            prepare_result = self.prepare_task(ctx)
        except Exception as e:
            logger.error(
                "Error preparing task %s: %s", self.title, e, exc_info=True
            )
            prepare_result = self.handle_exception(ctx, e, "prepare")
        if not prepare_result:
            self.state = TaskState.FAILED
            return

        # Execution stage.
        while not self.should_stop:
            try:
                self.step += 1
                if self.max_steps > 0 and self.step >= self.max_steps:
                    break
                self.prepare_step(ctx)
                self.execute_step(ctx)
                self.cleanup_step(ctx)
                if self.max_steps > 0:
                    self.progress = int(self.step / self.max_steps * 100)
            except IndexError:
                break
            except Exception as e:
                logger.error(
                    "Error executing step %s of task %s: %s",
                    self.step,
                    self.title,
                    e,
                    exc_info=True,
                )
                if self.handle_exception(ctx, e, "execute"):
                    continue

                self.state = TaskState.FAILED
                return

        # Cleanup stage.
        try:
            cleanup_result = self.cleanup_task(ctx)
        except Exception as e:
            logger.error(
                "Error cleaning up task %s: %s", self.title, e, exc_info=True
            )
            cleanup_result = self.handle_exception(ctx, e, "cleanup")
        if not cleanup_result:
            self.state = TaskState.FAILED
            return

        self.state = TaskState.COMPLETED

    def params_by_category(
        self,
    ) -> Dict[str, OrderedDict[str, "TaskParameter"]]:
        """Get the parameters split into categories."""
        result = defaultdict(OrderedDict)
        for parameter in self.parameters.values():
            result[parameter.category][parameter.name] = parameter
        return result


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
    prepare_func: Optional[Callable[["FuncTask", "HasTranslate"], bool]] = (
        field(default=None, repr=False)
    )
    cleanup_func: Optional[Callable[["FuncTask", "HasTranslate"], bool]] = (
        field(default=None, repr=False)
    )
    step_func: Callable[["FuncTask", "HasTranslate"], Any] = field(
        default=None, repr=False
    )

    def get_success_message(self, ctx: "HasTranslate") -> str:
        """Get the success message for the task."""
        return (
            self.success_message
            if self.success_message
            else super().get_success_message(ctx)
        )

    def get_failed_message(self, ctx: "HasTranslate") -> str:
        """Get the failed message for the task."""
        return (
            self.failed_message
            if self.failed_message
            else super().get_failed_message(ctx)
        )

    def prepare(self, ctx: "HasTranslate") -> bool:
        """Prepare the task."""
        if self.prepare_func:
            return self.prepare_func(self, ctx)
        return True

    def cleanup(self, ctx: "HasTranslate") -> bool:
        """Cleanup the task."""
        return self.cleanup_func(self, ctx) if self.cleanup_func else True

    def execute_step(self, ctx: "HasTranslate") -> None:
        """Execute one step in the task."""
        self.step_func(self, ctx)

    def handle_exception(
        self,
        ctx: "HasTranslate",
        e: Exception,
        stage: Literal["prepare", "execute", "cleanup"],
    ) -> bool:
        """Handle an exception that occurred during the task execution."""
        source_title: str
        if stage == "prepare":
            source_title = ctx.t("task.prepare.error", "Initializing")
        elif stage == "execute":
            source_title = ctx.t("task.execute.error", "Executing")
        elif stage == "cleanup":
            source_title = ctx.t("task.cleanup.error", "Cleaning up")
        else:
            raise ValueError(f"Invalid stage: {stage}")
        message = ctx.t(
            "task.error",
            "An error occurred while {source_title} the task: {error}.",
            source_title=source_title,
            error=e,
        )
        logger.error(message, exc_info=True)
        self.failed_message = message
        return False
