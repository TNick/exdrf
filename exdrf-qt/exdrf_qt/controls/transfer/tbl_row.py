"""One table-row entry for the tables list model."""

from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class TblRow:
    """One entry in the tables list model.

    Attributes:
        name: The table name.
        cnt_src: Row count in the source connection; None until loaded.
        cnt_dst: Row count in the destination connection; None until loaded.
    """

    name: str
    cnt_src: Optional[int] = None
    cnt_dst: Optional[int] = None
