"""Resolve ``RcvPlan`` from generated ``get_def`` modules with cache +
overrides.
"""

from __future__ import annotations

import importlib
import re
import threading
from dataclasses import dataclass
from typing import Any, Callable, Final

from pydantic import TypeAdapter

from exdrf_rcv.models import RcvField, RcvPlan, RcvResourceDataAccess

_rcv_field_adapter: Final = TypeAdapter(RcvField)


def _resource_data_access_from_module(mod: Any) -> RcvResourceDataAccess | None:
    """Parse optional ``RCV_RESOURCE_DATA_ACCESS`` from a generated paths module.

    Args:
        mod: Imported ``*_rcv_paths`` module object.

    Returns:
        Validated access descriptor, or ``None`` when the constant is absent
        or not a mapping.
    """

    raw = getattr(mod, "RCV_RESOURCE_DATA_ACCESS", None)
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise TypeError(
            "RCV_RESOURCE_DATA_ACCESS must be a dict (got %s)."
            % (type(raw).__name__,),
        )
    return RcvResourceDataAccess.model_validate(raw)


_SEGMENT_RE: Final[re.Pattern[str]] = re.compile(r"^[a-z][a-z0-9_]*$")

RcvPlanOverride = Callable[[RcvPlan], RcvPlan]


@dataclass(frozen=True)
class RcvPlanCacheKey:
    """Cache key for a resolved RCV plan (static ``get_def`` body).

    Attributes:
        import_root: Dotted package for generated modules.
        category: Dot-separated category path or ``""`` for uncategorized.
        resource: Resource snake name (without ``_rcv_paths`` suffix).
        view_type: View discriminator from the HTTP request.
    """

    import_root: str
    category: str
    resource: str
    view_type: str


class RcvPlanCache:
    """Thread-safe in-memory cache of resolved ``RcvPlan`` instances."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data: dict[RcvPlanCacheKey, RcvPlan] = {}

    def get(self, key: RcvPlanCacheKey) -> RcvPlan | None:
        """Return a cached plan copy or ``None``."""

        with self._lock:
            hit = self._data.get(key)
        if hit is None:
            return None
        return hit.model_copy(deep=True)

    def set(self, key: RcvPlanCacheKey, plan: RcvPlan) -> None:
        """Store a deep copy of ``plan``."""

        with self._lock:
            self._data[key] = plan.model_copy(deep=True)

    def clear(self) -> None:
        """Drop every cached entry."""

        with self._lock:
            self._data.clear()


_default_cache = RcvPlanCache()
_override_lock = threading.Lock()
_overrides: dict[RcvPlanCacheKey, list[RcvPlanOverride]] = {}


def default_rcv_plan_cache() -> RcvPlanCache:
    """Process-wide default cache singleton."""

    return _default_cache


def register_rcv_plan_override(
    key: RcvPlanCacheKey,
    fn: RcvPlanOverride,
) -> None:
    """Append a transform applied after ``get_def`` parsing (LIFO chain).

    Clears the default cache so stale merged plans are not served.

    Args:
        key: Same dimensions as :class:`RcvPlanCacheKey`.
        fn: Receives and returns an ``RcvPlan``.
    """

    with _override_lock:
        lst = _overrides.setdefault(key, [])
        lst.append(fn)
    _default_cache.clear()


def unregister_rcv_plan_override(
    key: RcvPlanCacheKey,
    fn: RcvPlanOverride,
) -> None:
    """Remove one override callable; clears cache when anything is removed."""

    with _override_lock:
        lst = _overrides.get(key)
        if not lst:
            return
        try:
            lst.remove(fn)
        except ValueError:
            return
        if not lst:
            del _overrides[key]
    _default_cache.clear()


def clear_rcv_plan_overrides() -> None:
    """Remove all overrides and clear the default cache."""

    with _override_lock:
        _overrides.clear()
    _default_cache.clear()


def _validate_segments(*parts: str) -> None:
    for raw in parts:
        if raw == "":
            continue
        for seg in raw.split("."):
            if seg == "":
                raise ValueError("Empty category segment is not allowed.")
            if not _SEGMENT_RE.match(seg):
                raise ValueError(
                    "Invalid path segment %r (allowed [a-z0-9_])." % (seg,),
                )


def _rcv_paths_module_name(
    import_root: str,
    category: str,
    resource: str,
) -> str:
    """Build ``importlib`` module path for ``{resource}_rcv_paths``."""

    segments = [import_root.strip()]
    if category.strip():
        segments.extend(category.strip().split("."))
    segments.append("%s_rcv_paths" % (resource.strip(),))
    return ".".join(segments)


def resolve_rcv_plan(
    *,
    import_root: str,
    category: str,
    resource: str,
    record_id: int | None,
    view_type: str,
    cache: RcvPlanCache | None = None,
) -> RcvPlan:
    """Import generated ``get_def``, parse fields, apply overrides, cache.

    Args:
        import_root: Dotted package path (e.g.
            ``resi_fapi.routes.al2rcv_generated``).
        category: Dot-separated category or empty string when uncategorized.
        resource: Resource snake name.
        record_id: Optional record id echoed on the plan.
        view_type: View discriminator (part of cache key).
        cache: Cache to use; defaults to :func:`default_rcv_plan_cache`.

    Returns:
        Validated ``RcvPlan``.

    Raises:
        ValueError: For invalid ``category`` / ``resource`` segments.
        ModuleNotFoundError: If the generated module is missing.
    """

    # Normalize string query parameters for consistent cache keys and imports.
    c = (category or "").strip()
    r = (resource or "").strip()
    vt = (view_type or "").strip()

    # Reject requests that cannot identify a resource or view.
    if not r:
        raise ValueError("resource must be non-empty.")
    if not vt:
        raise ValueError("view_type must be non-empty.")

    # Ensure dotted category and resource segments are safe for dynamic import.
    _validate_segments(c, r)

    # Build the cache key (static plan body; ``record_id`` is applied later).
    key = RcvPlanCacheKey(
        import_root=import_root.strip(),
        category=c,
        resource=r,
        view_type=vt,
    )

    # Return a cached plan when present, refreshing only the
    # request ``record_id``.
    store = cache if cache is not None else _default_cache
    cached = store.get(key)
    if cached is not None:
        return cached.model_copy(update={"record_id": record_id})

    # Load the generated ``{resource}_rcv_paths`` module and its ``get_def``.
    mod_name = _rcv_paths_module_name(import_root, c, r)
    mod = importlib.import_module(mod_name)
    get_def = getattr(mod, "get_def", None)
    if not callable(get_def):
        raise AttributeError(
            "Module %s has no callable get_def." % (mod_name,),
        )

    # Call ``get_def`` and require a list of field dictionaries.
    raw_rows: Any = get_def()
    if not isinstance(raw_rows, list):
        raise TypeError(
            "get_def from %s must return a list (got %s)."
            % (mod_name, type(raw_rows).__name__),
        )

    # Validate each wire dict against the discriminated ``RcvField`` union.
    fields: list[Any] = []
    for i, row in enumerate(raw_rows):
        if not isinstance(row, dict):
            raise TypeError(
                "get_def item %d in %s must be dict (got %s)."
                % (i, mod_name, type(row).__name__),
            )
        fields.append(_rcv_field_adapter.validate_python(row))

    # Read optional module-level render hint; otherwise mirror ``view_type``.
    # Generated stubs often set ``RCV_RENDER_TYPE = "default"``; treat that like
    # "unset" so list/new/detail map to distinct render hints.
    render_type = getattr(mod, "RCV_RENDER_TYPE", None)
    if not isinstance(render_type, str) or not render_type.strip():
        render_type = vt
    elif render_type.strip().lower() == "default":
        render_type = vt

    # Optional HTTP row-access metadata from the generated module.
    resource_data_access = _resource_data_access_from_module(mod)

    # Assemble the base plan from request metadata and parsed fields.
    plan = RcvPlan(
        category=c or None,
        resource=r,
        record_id=record_id,
        view_type=vt,
        render_type=render_type,
        fields=fields,
        resource_data_access=resource_data_access,
    )

    # Apply any registered override callables in registration order.
    with _override_lock:
        fns = list(_overrides.get(key, ()))
    for fn in fns:
        plan = fn(plan)

    # Store the final plan for future hits and return an independent deep copy.
    store.set(key, plan)
    return plan.model_copy(deep=True)
