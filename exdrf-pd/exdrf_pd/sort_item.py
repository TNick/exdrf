"""Sort keys for list queries (JSON alongside :class:`~exdrf_pd.filter_item.FilterItem`)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SortItem(BaseModel):
    """One attribute and direction in an ordered ``ORDER BY`` specification.

    Sort keys are applied in list order (first key is primary, later keys
    break ties). Serialize as JSON objects in a list, for example
    ``[{"attr": "name", "order": "asc"}, {"attr": "id", "order": "desc"}]``.

    Attributes:
        attr: Column or ORM attribute name to sort by.
        order: ``asc`` or ``desc``.
    """

    model_config = ConfigDict(extra="forbid")

    attr: str = Field(description="Attribute or column name to sort by.")
    order: Literal["asc", "desc"] = Field(
        description="Sort direction for this key.",
    )
