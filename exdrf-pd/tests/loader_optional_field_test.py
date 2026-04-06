"""Tests for :mod:`exdrf_pd.loader` optional / PEP 604 union annotations."""

from __future__ import annotations

from typing import Optional

from exdrf.field_types.str_field import StrField
from exdrf.resource import ExResource
from pydantic import BaseModel

from exdrf_pd.loader import field_from_pydantic


class TestFieldFromPydanticOptional:
    """Covers ``str | None`` and ``Optional[str]`` field annotations."""

    def test_pep604_str_or_none_produces_str_field(self) -> None:
        """``str | None`` unwraps to :class:`StrField` instead of failing."""

        class Sample(BaseModel):
            """Minimal model with a PEP 604 optional string."""

            label: str | None = None

        resource = ExResource(name="Sample", src=Sample)
        info = Sample.model_fields["label"]
        field_from_pydantic(resource, "label", info)
        assert len(resource.fields) == 1
        assert isinstance(resource.fields[0], StrField)
        assert resource.fields[0].name == "label"

    def test_optional_str_produces_str_field(self) -> None:
        """``Optional[str]`` is handled like ``str | None``."""

        class Sample(BaseModel):
            """Minimal model with ``typing.Optional``."""

            label: Optional[str] = None

        resource = ExResource(name="Sample", src=Sample)
        info = Sample.model_fields["label"]
        field_from_pydantic(resource, "label", info)
        assert len(resource.fields) == 1
        assert isinstance(resource.fields[0], StrField)
