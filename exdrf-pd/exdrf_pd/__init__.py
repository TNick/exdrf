"""Pydantic helpers used alongside exdrf-generated APIs."""

from exdrf_pd.base import ExModel
from exdrf_pd.paged import PagedList, paged_list_empty_factory
from exdrf_pd.schema_extra import (
    EXDRF_JSON_SCHEMA_EXTRA_KEY,
    wrap_exdrf_props,
)

__all__ = [
    "EXDRF_JSON_SCHEMA_EXTRA_KEY",
    "ExModel",
    "PagedList",
    "paged_list_empty_factory",
    "wrap_exdrf_props",
]
