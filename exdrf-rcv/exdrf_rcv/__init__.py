"""Shared runtime for remote-controlled-view (RCV) backends.

``exdrf-gen-al2rcv`` emits modules that should import shared symbols from this
package as RCV behavior grows. The front-end RCV project is documented under
``fr-one`` ``libs/rcv``.
"""

from exdrf_rcv.models import RcvField, RcvPlan, RcvResourceDataAccess
from exdrf_rcv.plan_resolve import (
    RcvPlanCache,
    RcvPlanCacheKey,
    clear_rcv_plan_overrides,
    default_rcv_plan_cache,
    register_rcv_plan_override,
    resolve_rcv_plan,
    unregister_rcv_plan_override,
)

__all__ = [
    "RcvPlan",
    "RcvField",
    "RcvResourceDataAccess",
    "RcvPlanCache",
    "RcvPlanCacheKey",
    "clear_rcv_plan_overrides",
    "default_rcv_plan_cache",
    "register_rcv_plan_override",
    "resolve_rcv_plan",
    "unregister_rcv_plan_override",
]
