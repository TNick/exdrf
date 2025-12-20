"""Data class for split entry definitions."""

from dataclasses import dataclass
from typing import Dict


@dataclass
class SplitEntry:
    """Definition of a split output file."""

    pages_expr: str
    title: str
    row_index: int
    page_rotations: Dict[int, int]
