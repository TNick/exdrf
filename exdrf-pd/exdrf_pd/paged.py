"""Paged collection shapes for API / Pydantic models."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class PagedList(BaseModel, Generic[T]):
    """A slice of a larger collection with stable paging fields.

    Use this instead of a bare ``list[T]`` when the backing relation can be
    large and clients should load data in pages (``offset`` / ``page_size`` /
    ``total``).

    Attributes:
        total: Number of items available in the full collection.
        offset: Zero-based index of the first entry in ``items`` within the
            full collection.
        page_size: Requested page capacity; ``len(items)`` may be smaller
            (for example on the last page).
        items: Entries returned for this page.
    """

    model_config = ConfigDict(extra="forbid")

    total: int = Field(default=0, ge=0, description="Total items available")
    offset: int = Field(default=0, ge=0, description="Start index of this page")
    page_size: int = Field(
        default=0,
        ge=0,
        description="Requested maximum items per page",
    )
    items: list[T] = Field(
        default_factory=list,
        description="Items loaded for this page",
    )

    @classmethod
    def empty(cls) -> PagedList[T]:
        """Return an empty page (all counters zero, no items).

        Returns:
            A validated empty :class:`PagedList` suitable for
            ``Field(default_factory=...)``.
        """
        return cls.model_construct(
            total=0,
            offset=0,
            page_size=0,
            items=[],
        )


def paged_list_empty_factory() -> PagedList[Any]:
    """Build an empty page without naming the item type (forward-ref safe).

    Use as ``Field(default_factory=paged_list_empty_factory)`` on
    ``PagedList[SomeModel]`` fields when ``SomeModel`` is only imported under
    ``TYPE_CHECKING``.

    Returns:
        An empty :class:`PagedList` instance.
    """
    return PagedList.model_construct(
        total=0,
        offset=0,
        page_size=0,
        items=[],
    )
