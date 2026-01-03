import logging
from collections import OrderedDict, defaultdict
from enum import StrEnum
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Generic,
    List,
    Literal,
    Optional,
    TypeVar,
    Union,
)

import pluggy
from attrs import define, field

from .task import Task, TaskParameter

if TYPE_CHECKING:
    from exdrf_util.typedefs import HasBasicContext, HasTranslate

# T represents the type of the item that the check is being performed on
# on each step.
T = TypeVar("T")

logger = logging.getLogger(__name__)


class ResultState(StrEnum):
    """The state of a check result.

    Attributes:
        INITIAL: The check result was not yet computed.
        PASSED: The check passed.
        SKIPPED: The check was skipped.
        FIXED: The check found a problem which was fixed.
        PARTIALLY_FIXED: The check found a problem which was partially fixed.
        NOT_FIXED: The check found a problem which was not fixed.
        FAILED: The check failed to execute (raised an exception).
    """

    INITIAL = "initial"
    PASSED = "passed"
    SKIPPED = "skipped"
    FIXED = "fixed"
    PARTIALLY_FIXED = "partially_fixed"
    NOT_FIXED = "not_fixed"
    FAILED = "failed"


@define(slots=True, kw_only=True)
class CheckResult:
    """The result of a check over a particular record or a record set.

    Attributes:
        check_id: The ID of the check that produced the result.
        state: Whether the check passed, skipped (for cases when the filtration
            could not be fully applied through the query and the runtime check
            if required to determine if a particular record should be checked),
            was fully or partially fixed or was detected but not fixed.
        issue_hash: A pseudo-unique identifier for the issue. When possible we
            should compute the hash so that the behavior of the issue
            can be tracked across time. This may include the record ID,
            the field ID, the check that was performed.
        t_key: The translation code that can be used, along with the parameters,
            to recreate the description.
        params: Additional information about the result in dictionary format.
            When recreating the description the code and params are used,
            but additional information can be added here. Note that these
            are NOT the parameters of the check.
        description: A description of the result.
    """

    check_id: str
    state: ResultState = field(default=ResultState.INITIAL)
    issue_hash: Optional[str] = field(default=None)
    t_key: str = field(default="", repr=False)
    params: Dict[str, Any] = field(factory=dict)
    description: str = field(default="", repr=False)


@define(slots=True, kw_only=True)
class CheckTask(Task, Generic[T]):
    """A task that executes a check."""

    check: "Check"
    results: List[CheckResult] = field(factory=list)

    def __attrs_post_init__(self):
        if self.title == "":
            self.title = self.check.title
        if self.description == "":
            self.description = self.check.description
        if not self.parameters:
            self.parameters = self.check.parameters

    def results_by_type(self) -> Dict[ResultState, List[CheckResult]]:
        """Split the list of results by their state."""
        results_by_type = defaultdict(list)
        for result in self.results:
            results_by_type[result.state].append(result)
        return results_by_type

    def result_count_by_type(self) -> Dict[ResultState, int]:
        """Count the number of results by their state."""
        results_by_type = self.results_by_type()
        return {
            state: len(results) for state, results in results_by_type.items()
        }

    def get_success_message(self, ctx: "HasTranslate") -> str:
        if len(self.results) == 0:
            return ctx.t(
                "check.no-results", "The check did not find any results."
            )
        elif self.check.is_global:
            assert (
                len(self.results) == 1
            ), "Global check should have exactly one result."

            result = self.results[0]
            state = result.state
            if state == ResultState.PASSED:
                return ctx.t("check.global.success", "The check passed.")
            elif state == ResultState.SKIPPED:
                return ctx.t("check.global.skipped", "The check was skipped.")
            elif state == ResultState.FIXED:
                return ctx.t(
                    "check.global.fixed",
                    "The check detected an issue and fixed it.",
                )
            elif state == ResultState.NOT_FIXED:
                return ctx.t(
                    result.t_key,
                    "The check detected an issue but did not fix it.",
                    **result.params,
                )
            elif state == ResultState.PARTIALLY_FIXED:
                return ctx.t(
                    "check.global.partially-fixed",
                    "The check detected an issue and partially fixed it but "
                    "it requires further manual action.",
                )
            elif state == ResultState.FAILED:
                return ctx.t(
                    result.t_key,
                    "The check failed to execute.",
                    **result.params,
                )
            else:
                raise ValueError(f"Invalid result state: {state}")
        else:
            final = []
            results_by_type = self.result_count_by_type()
            passed = results_by_type.get(ResultState.PASSED, 0)
            skipped = results_by_type.get(ResultState.SKIPPED, 0)
            fixed = results_by_type.get(ResultState.FIXED, 0)
            not_fixed = results_by_type.get(ResultState.NOT_FIXED, 0)
            partially_fixed = results_by_type.get(
                ResultState.PARTIALLY_FIXED, 0
            )
            failed = results_by_type.get(ResultState.FAILED, 0)
            if passed > 0:
                final.append(
                    ctx.t(
                        "check.success.count",
                        "{count} checks passed.",
                        count=passed,
                    )
                )
            if skipped > 0:
                final.append(
                    ctx.t(
                        "check.skipped.count",
                        "{count} checks skipped.",
                        count=skipped,
                    )
                )
            if fixed > 0:
                final.append(
                    ctx.t(
                        "check.fixed.count",
                        "{count} issues were fixed.",
                        count=fixed,
                    )
                )
            if not_fixed > 0:
                final.append(
                    ctx.t(
                        "check.not-fixed.count",
                        "{count} issues were not fixed.",
                        count=not_fixed,
                    )
                )
            if partially_fixed > 0:
                final.append(
                    ctx.t(
                        "check.partially-fixed.count",
                        "{count} issues were partially fixed and require "
                        "further manual action.",
                        count=partially_fixed,
                    )
                )
            if failed > 0:
                final.append(
                    ctx.t(
                        "check.failed.count",
                        "{count} checks failed to execute.",
                        count=failed,
                    )
                )
            return "\n".join(final)

    def prepare_task(self, ctx: "HasBasicContext") -> bool:  # type: ignore
        """Prepare the task."""
        result = self.check.prepare_check(ctx)
        if result is not None:
            # Add any private data to the data.
            assert isinstance(result, dict)
            for k, v in result.items():
                if k in self.data:
                    logger.warning(
                        "Private data key %s overrides preset with same name. "
                        "Avoid naming the preset data keys the same as the "
                        "private data keys to avoid unexpected behavior.",
                        k,
                    )
                self.data[k] = v

            # Move the parameters to the data.
            for k, v in self.check.parameters.items():
                if k in self.data:
                    logger.warning(
                        "Parameter %s overrides private data with same name. "
                        "Avoid naming the private data keys the same as the "
                        "parameters to avoid unexpected behavior.",
                        k,
                    )
                self.data[k] = v.value

            # If the result has a records member, we assume its length to be
            # the number of records to check.
            if "records" in result:
                self.max_steps = len(result["records"])
            return True
        return False

    def cleanup_task(self, ctx: "HasBasicContext") -> bool:  # type: ignore
        """Cleanup the task."""
        return self.check.cleanup_check(ctx)

    def get_failed_message(self, ctx: "HasTranslate") -> str:
        return self.get_success_message(ctx)

    def prepare_step(self, ctx: "HasTranslate") -> None:
        """Prepare the task."""
        self.results.append(CheckResult(check_id=self.check.check_id))

    def handle_exception(
        self,
        ctx: "HasTranslate",
        e: Exception,
        stage: Literal["prepare", "execute", "cleanup"],
    ) -> bool:
        """Handle an exception that occurred during the task execution."""
        if stage in ("prepare", "cleanup"):
            return super().handle_exception(ctx, e, stage)

        t_key = "check.failed.exception"
        result = self.results[-1]
        result.check_id = self.check.check_id
        result.state = ResultState.FAILED
        result.params["exception"] = str(e)
        result.params["e_class"] = e.__class__.__name__
        result.description = ctx.t(
            t_key,
            "The check failed to execute: {exception} ({e_class}).",
            **result.params,
        )
        return True

    def execute_step(self, ctx: "HasBasicContext") -> None:  # type: ignore
        """Execute one step in the task."""
        item = self.check.get_record_to_check(self.step, self.data)
        result = self.results[-1]
        record_id = self.check.get_record_id(self.step, self.data, item)
        result.params["id"] = record_id
        result.issue_hash = self.check.compute_hash(self.step, self.data, item)
        result = self.check.execute(ctx, item, result)
        self.results[-1] = result


@define(slots=True, frozen=True, kw_only=True)
class Check(Generic[T]):
    """A check that can be performed on a record or a record set.

    Attributes:
        check_id: A unique identifier for the check.
        description: A description of the check.
        category: The category of the check.
        tags: The tags of the check.
        is_global: Whether the check is global. A global check is one that
            cannot iterate over the members so reporting the progress is
            not possible.
        has_fix: Whether this check provides an automatic fix for the problem
            it detects. This does not mean that all issues will be fixed
            or that the fix will be complete. It just means that the
            class implements the fix method< wether a particular issue was
            fixed or not will be reflected in the result.
        parameters: Definition of the parameters that the check accepts
            and their values.
    """

    check_id: str
    title: str = field(default="", repr=False)
    description: str = field(default="", repr=False)
    category: str = field(default="", repr=False)
    tags: List[str] = field(factory=list, repr=False)
    is_global: bool = field(default=False, repr=False)
    has_fix: bool = field(default=False, repr=False)
    parameters: Dict[str, "TaskParameter"] = field(
        factory=OrderedDict, repr=False
    )

    def prepare_check(self, ctx: "HasBasicContext") -> Optional[Dict[str, Any]]:
        """Prepare the check.

        Returns a (possibly empty) dictionary of private data that
        the check needs to store between the prepare and cleanup steps.

        This is the best place to obtain and store the list of records that
        will be checked.

        If the result is None this indicates that the preparation step failed.
        The check will be aborted and the user will be notified.
        """
        del ctx
        return {}

    def cleanup_check(self, ctx: "HasBasicContext") -> bool:
        """Cleanup the check.

        The result indicates whether the cleanup step was successful.
        """
        with ctx.same_session() as s:
            s.commit()
        return True

    def get_record_to_check(self, step: int, data: Dict[str, Any]) -> T:
        """Get the record to check out of the prepared data."""
        raise NotImplementedError("Subclasses must implement this method.")

    def get_record_id(self, step: int, data: Dict[str, Any], item: T) -> str:
        """Get the record ID of the item."""
        return str(item.id)  # type: ignore

    def compute_hash(self, step: int, data: Dict[str, Any], item: T) -> str:
        """Compute the hash of the item.

        The hash is used to track the changes of the item with respect
        to this check through time.
        """
        del step, data, item
        return ""

    def execute(
        self,
        ctx: "HasBasicContext",
        item: Union[T, List[T]],
        result: Optional["CheckResult"] = None,
    ) -> "CheckResult":
        """Execute the check on the given item.

        For global checks the `item` is a list of all the records that were
        found for the query. For non-global checks the `item` is a single
        record.

        Args:
            item: The item to check.
            result: The result to update. If not provided a new result will be
                created.

        Returns:
            The result of the check.
        """
        raise NotImplementedError

    def create_task(self) -> CheckTask[T]:
        return CheckTask[T](
            check=self,
            title=self.title,
            description=self.description,
            parameters=self.parameters,
        )


PROJECT_NAME = "exdrf-checks"
exdrf_check_spec = pluggy.HookspecMarker(PROJECT_NAME)
exdrf_check_impl = pluggy.HookimplMarker(PROJECT_NAME)


class HookSpecs:
    """Hook specifications for the check registry."""

    @exdrf_check_spec
    def exdrf_checks(ctx: "HasTranslate", for_gui: bool) -> List["Check"]:
        """Get the checks that should be made available to the user.

        Args:
            ctx: The context of the application.
            for_gui: Whether the checks are being requested for the GUI.
                Some parameters will use this information to import
                different data for the GUI and the CLI.
        """
        raise NotImplementedError


exdrf_checks_pm = pluggy.PluginManager(PROJECT_NAME)
exdrf_checks_pm.add_hookspecs(HookSpecs)


def get_all_checks(ctx: "HasTranslate", for_gui: bool) -> List["Check"]:
    """Get all the checks that should be made available to the user.

    For your check to be noticed by the registry you need to:

    1. Create a Check class that implements the check logic.
    2. Implement the hook using the @exdrf_check_impl decorator.
    3. Register your plugin with the plugin manager.

    Example::

        from exdrf_util.check import (
            Check, CheckResult, ResultState, exdrf_check_impl, exdrf_checks_pm
        )
        from exdrf_util.typedefs import HasBasicContext

        class MyCustomCheck(Check[str]):
            \"\"\"A custom check that validates string length.\"\"\"

            def __init__(self):
                super().__init__(
                    check_id="my_custom_check",
                    title="Custom String Check",
                    description="Checks if string length is valid",
                    category="validation"
                )

            def execute(
                self,
                ctx: HasBasicContext,
                item: str,
                result: Optional[CheckResult] = None,
            ) -> CheckResult:
                if result is None:
                    result = CheckResult()

                if len(item) < 5:
                    result.state = ResultState.NOT_FIXED
                    result.t_key = "check.string.too_short"
                    result.params = {"length": len(item), "min_length": 5}
                    result.description = (
                        f"String is too short: {len(item)} < 5"
                    )
                else:
                    result.state = ResultState.PASSED

                return result

        class MyChecksPlugin:
            \"\"\"Plugin that provides custom checks.\"\"\"

            @exdrf_check_impl
            def exdrf_checks(self) -> List[Check]:
                \"\"\"Return the list of checks provided by this plugin.\"\"\"
                return [MyCustomCheck()]

        # Register the plugin
        exdrf_checks_pm.register(MyChecksPlugin())
    """
    result = []
    for hookimpl in exdrf_checks_pm.hook.exdrf_checks(ctx=ctx, for_gui=for_gui):
        result.extend(hookimpl)
    logger.debug(f"Found {len(result)} checks")
    return result
