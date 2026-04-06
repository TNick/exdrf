"""Compatibility re-exports for SQLAlchemy filter operators.

Prefer importing from ``exdrf.sa_filter_op`` in new code.

Module-level ``logger``, ``al_cast``, and ``ilike_op`` mirror the
implementation module so tests can patch ``exdrf_qt.models.fi_op.*``.
"""

import exdrf.sa_filter_op as _sa_filter_op
from exdrf.sa_filter_op import (
    EqFiOp,
    FiOp,
    FiOpRegistry,
    GreaterFiOp,
    GreaterOrEqFiOp,
    ILikeFiOp,
    InFiOp,
    IsNoneFiOp,
    LessOrEqFiOp,
    NotEqFiOp,
    RegexFiOp,
    SmallerFiOp,
    filter_op_registry,
    is_none,
)

al_cast = _sa_filter_op.al_cast
ilike_op = _sa_filter_op.ilike_op
logger = _sa_filter_op.logger

__all__ = [
    "EqFiOp",
    "FiOp",
    "FiOpRegistry",
    "GreaterFiOp",
    "GreaterOrEqFiOp",
    "ILikeFiOp",
    "InFiOp",
    "IsNoneFiOp",
    "LessOrEqFiOp",
    "NotEqFiOp",
    "RegexFiOp",
    "SmallerFiOp",
    "al_cast",
    "filter_op_registry",
    "ilike_op",
    "is_none",
    "logger",
]
