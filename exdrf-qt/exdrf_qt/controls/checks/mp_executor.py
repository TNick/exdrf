"""Multiprocessing executor for running checks.

This module provides a small IPC layer so checks can be executed in a separate
process while streaming progress/state/results back to the GUI.
"""

from __future__ import annotations

import importlib
import logging
import multiprocessing as mp
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Literal,
    NotRequired,
    Optional,
    TypedDict,
)

if TYPE_CHECKING:
    from multiprocessing.synchronize import Event


logger = logging.getLogger(__name__)


class DbConfigDict(TypedDict, total=False):
    """Database configuration passed into worker processes.

    Attributes:
        c_string: Database connection string.
        schema: Default schema name.
    """

    c_string: str
    schema: str


class SerializedResultDict(TypedDict):
    """Serialized representation of a CheckResult.

    Attributes:
        check_id: Identifier of the executed check.
        state: Task state as a string.
        issue_hash: Issue hash for deduplication.
        t_key: Translation key for the result.
        params: Parameters associated with the result.
        description: Description of the result, computed by applying the
            translation key and parameters through the context's
            translation function.
    """

    check_id: str
    state: str
    issue_hash: str
    t_key: str
    params: Dict[str, Any]
    description: str


class ProgressMessage(TypedDict):
    """Progress update sent from worker to GUI.

    Attributes:
        type: Literal value ``"progress"``.
        check_id: Identifier of the running check.
        progress: Current progress step.
        max_steps: Maximum progress steps.
    """

    type: Literal["progress"]
    check_id: str
    progress: int
    max_steps: int


class ResultsMessage(TypedDict):
    """Results payload sent from worker to GUI.

    Attributes:
        type: Literal value ``"results"``.
        check_id: Identifier of the executed check.
        check_title: Title of the check.
        check_description: Description of the check.
        check_category: Category of the check.
        results: List of serialized results.
    """

    type: Literal["results"]
    check_id: str
    check_title: str
    check_description: str
    check_category: str
    results: List[SerializedResultDict]


class WorkerMessage(TypedDict):
    """Union of messages exchanged between worker and GUI.

    Attributes:
        type: Message kind (progress, results, error, state, started, done).
        check_id: Identifier of the check.
        progress: Optional current progress step.
        max_steps: Optional maximum progress steps.
        check_title: Optional title of the check.
        check_description: Optional description of the check.
        check_category: Optional category of the check.
        results: Optional list of serialized results.
        error: Optional error message.
        state: Optional state string.
    """

    type: Literal["progress", "results", "error", "state", "started", "done"]
    check_id: str
    progress: NotRequired[int]
    max_steps: NotRequired[int]
    check_title: NotRequired[str]
    check_description: NotRequired[str]
    check_category: NotRequired[str]
    results: NotRequired[List[SerializedResultDict]]
    error: NotRequired[str]
    state: NotRequired[str]


def _serialize_result(result) -> SerializedResultDict:
    """Serialize a CheckResult to a plain dict."""
    return {
        "check_id": result.check_id,
        "state": str(result.state),
        "issue_hash": result.issue_hash,
        "t_key": result.t_key,
        "params": dict(result.params),
        "description": result.description,
    }


def run_check_task_in_process(
    *,
    check_id: str,
    db: DbConfigDict,
    param_values: Dict[str, Any],
    out_q: "mp.Queue[WorkerMessage]",
    stop_event: "Event",
    bootstrap_imports: Optional[List[str]] = None,
    bootstrap_callables: Optional[List[str]] = None,
) -> None:
    """Run one check task in a separate process.

    Args:
        check_id: Check id to execute (resolved via get_all_checks in-process).
        db: DB configuration dict with keys 'c_string' and 'schema'.
        param_values: Parameter values keyed by parameter name.
        out_q: Output queue for status/progress/results messages.
        stop_event: Stop event signaled by the GUI.
        bootstrap_imports: Optional list of modules to import before discovery.
        bootstrap_callables: Optional list of dotted callables to invoke before
            discovery (for example to register plugins in the worker).
    """
    try:
        from exdrf_util.check import get_all_checks
        from exdrf_util.task import TaskState
    except Exception as e:
        out_q.put(
            {
                "type": "error",
                "check_id": check_id,
                "error": str(e),
            }
        )
        return

    # Bootstrap worker process (optional).
    for mod_name in bootstrap_imports or []:
        try:
            importlib.import_module(mod_name)
        except Exception as e:
            out_q.put(
                {
                    "type": "error",
                    "check_id": check_id,
                    "error": f"Failed to import {mod_name}: {e}",
                }
            )

    for dotted in bootstrap_callables or []:
        try:
            mod_path, attr = dotted.rsplit(".", 1)
            mod = importlib.import_module(mod_path)
            fn = getattr(mod, attr)
            fn()
        except Exception as e:
            out_q.put(
                {
                    "type": "error",
                    "check_id": check_id,
                    "error": f"Failed to call {dotted}: {e}",
                }
            )

    try:
        from exdrf_qt.context import QtMinContext
    except Exception as e:
        out_q.put(
            {
                "type": "error",
                "check_id": check_id,
                "error": (
                    "Database driver/module missing. "
                    f"Failed to import QtMinContext: {e}"
                ),
            }
        )
        return

    # Create context in the worker.
    ctx = QtMinContext(
        c_string=db.get("c_string", ""),
        schema=db.get("schema", "public"),
    )
    ctx.stg.set_read_only(True)

    # Resolve check instance.
    checks = {
        chk.check_id: chk
        for chk in get_all_checks(
            ctx=ctx,
            for_gui=False,
        )
    }
    chk = checks.get(check_id)
    if chk is None:
        out_q.put(
            {
                "type": "error",
                "check_id": check_id,
                "error": f"Check not found: {check_id}",
            }
        )
        return

    # Apply parameter values.
    for name, value in param_values.items():
        if name in chk.parameters:
            chk.parameters[name].value = value

    task = chk.create_task()

    # Stream state/progress.
    def on_state_changed(_task, state: TaskState) -> None:
        out_q.put(
            {
                "type": "state",
                "check_id": check_id,
                "state": str(state),
            }
        )

    def on_progress_changed(_task, progress: int) -> None:
        if stop_event.is_set():
            _task.should_stop = True
        out_q.put(
            {
                "type": "progress",
                "check_id": check_id,
                "progress": progress,
                "max_steps": int(getattr(_task, "max_steps", -1) or -1),
            }
        )

    task.on_state_changed.append(on_state_changed)
    task.on_progress_changed.append(on_progress_changed)

    try:
        out_q.put({"type": "started", "check_id": check_id})
        task.execute(ctx)  # type: ignore[arg-type]
    except Exception as e:
        out_q.put(
            {
                "type": "error",
                "check_id": check_id,
                "error": str(e),
            }
        )
    finally:
        results = getattr(task, "results", [])
        out_q.put(
            {
                "type": "results",
                "check_id": check_id,
                "check_title": chk.title,
                "check_description": chk.description,
                "check_category": chk.category,
                "results": [_serialize_result(r) for r in results],
            }
        )
        out_q.put({"type": "done", "check_id": check_id})
