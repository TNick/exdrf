"""Tests for ``exdrf_gen_al2pd.creator``."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import exdrf_gen_al2pd  # noqa: F401
from exdrf_gen.jinja_support import jinja_env

from exdrf.label_dsl import parse_expr
from exdrf.resource import ExResource
from exdrf.field_types.int_field import IntField
from exdrf.field_types.str_field import StrField

from exdrf_gen_al2pd.creator import generate_pydantic_from_alchemy


def _minimal_dataset(resources: list) -> SimpleNamespace:
    """Shim ``ExDataset`` API for :class:`~exdrf_gen.fs_support.TopDir`."""

    r = list(resources)
    return SimpleNamespace(
        resources=r,
        category_map={},
        zero_categories=lambda: [],
        sorted_by_deps=lambda: r,
    )


def test_al2pd_registers_cli_command() -> None:
    """Importing the package registers the ``al2pd`` subcommand."""

    from exdrf_gen.cli_base import cli as base_cli

    assert "al2pd" in base_cli.commands


def test_cli_al2pd_writes_modules(tmp_path: Path) -> None:
    """The al2pd Click command writes a plural module and ``api.py``."""

    res = ExResource(
        name="Widget",
        fields=[
            IntField(name="id", primary=True, nullable=False),
            StrField(name="title", nullable=False),
        ],
        label_ast=parse_expr("title"),
    )
    d_set = _minimal_dataset([res])

    ctx = SimpleNamespace(obj={"jinja_env": jinja_env})

    generate_pydantic_from_alchemy(ctx, d_set, str(tmp_path))

    mod = tmp_path / "widgets.py"
    assert mod.is_file()
    body = mod.read_text(encoding="utf-8")
    assert "import json" not in body
    assert "json.loads" not in body
    assert "_EXDRF_FIELD_" not in body
    assert '{"exdrf": {}}' not in body
    assert "class WidgetEx(Widget):" in body

    api = tmp_path / "api.py"
    assert api.is_file()
    assert "from .widgets import" in api.read_text(encoding="utf-8")


def test_cli_al2pd_writes_category_api(tmp_path: Path) -> None:
    """Nested ``categories`` get a local ``api.py`` with relative imports."""

    common = dict(
        fields=[
            IntField(name="id", primary=True, nullable=False),
            StrField(name="title", nullable=False),
        ],
        label_ast=parse_expr("title"),
        categories=["l18"],
    )
    r1 = ExResource(name="Alpha", **common)
    r2 = ExResource(name="Beta", **common)
    d_set = _minimal_dataset([r1, r2])

    ctx = SimpleNamespace(obj={"jinja_env": jinja_env})
    generate_pydantic_from_alchemy(ctx, d_set, str(tmp_path))

    cat_api = tmp_path / "l18" / "api.py"
    assert cat_api.is_file()
    text = cat_api.read_text(encoding="utf-8")
    assert "from .alphas import" in text
    assert "from .betas import" in text
    assert "Alpha" in text and "Beta" in text
