"""Pytest setup: ensure sibling editable packages are on ``sys.path``."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
for _name in (
    "exdrf",
    "exdrf-al",
    "exdrf-gen",
    "exdrf-rcv",
    "exdrf-gen-al2rcv",
):
    _p = _REPO_ROOT / _name
    if _p.is_dir():
        s = str(_p)
        if s not in sys.path:
            sys.path.insert(0, s)
