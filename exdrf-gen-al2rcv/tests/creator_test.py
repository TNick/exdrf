"""Tests for ``exdrf_gen_al2rcv.creator``."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from exdrf.field_types.int_field import IntField
from exdrf.label_dsl import parse_expr
from exdrf.resource import ExResource
from jinja2 import Environment, FileSystemLoader

from exdrf_gen_al2rcv.creator import (
    generate_rcv_path_scaffolds_from_alchemy,
    parse_get_db_import,
)


def _minimal_dataset(resources: list) -> SimpleNamespace:
    """Shim ``ExDataset`` for :class:`~exdrf_gen.fs_support.TopDir`."""

    r = list(resources)
    return SimpleNamespace(
        resources=r,
        category_map={},
        zero_categories=lambda: [],
        sorted_by_deps=lambda: r,
    )


def test_generate_writes_per_resource_and_category_api(
    tmp_path: Path,
) -> None:
    """Categorized models get path file, package ``__init__``, empty ``api``."""

    class _Orm:
        __tablename__ = "widgets"

    res = ExResource(
        name="Widget",
        src=_Orm,
        categories=["issues", "l18"],
        fields=[
            IntField(name="id", primary=True, nullable=False),
        ],
        label_ast=parse_expr("id"),
    )
    d_set = _minimal_dataset([res])
    tmpl_root = (
        Path(__file__).resolve().parent.parent
        / "exdrf_gen_al2rcv"
        / "al2rcv_templates"
    )
    env = Environment(loader=FileSystemLoader(str(tmpl_root)))
    generate_rcv_path_scaffolds_from_alchemy(
        d_set=d_set,
        out_path=str(tmp_path),
        env=env,
        get_db_import="resi_fapi.deps.al2r_db:get_db",
    )
    assert (tmp_path / "__init__.py").is_file()
    assert (tmp_path / "api.py").is_file()
    root_api = (tmp_path / "api.py").read_text(encoding="utf-8")
    assert "Root ``api`` scaffold" in root_api
    assert "from resi_fapi.deps.al2r_db import get_db" in root_api
    assert "resolve_rcv_plan" in root_api
    assert "RCV_IMPORT_ROOT" in root_api
    cat = tmp_path / "issues" / "l18"
    wpath = cat / "widget_rcv_paths.py"
    assert wpath.is_file()
    wtxt = wpath.read_text(encoding="utf-8")
    assert "def get_def" in wtxt
    assert "RCV_RENDER_TYPE" in wtxt
    assert (cat / "__init__.py").is_file()
    assert (cat / "api.py").is_file()
    api_text = (cat / "api.py").read_text(encoding="utf-8")
    assert "empty scaffold" in api_text


def test_generate_uncategorized_resource_at_root(tmp_path: Path) -> None:
    """Resources without categories write only the scaffold file at the root."""

    class _Orm:
        __tablename__ = "roots"

    res = ExResource(
        name="RootRow",
        src=_Orm,
        categories=[],
        fields=[
            IntField(name="id", primary=True, nullable=False),
        ],
        label_ast=parse_expr("id"),
    )
    d_set = _minimal_dataset([res])
    tmpl_root = (
        Path(__file__).resolve().parent.parent
        / "exdrf_gen_al2rcv"
        / "al2rcv_templates"
    )
    env = Environment(loader=FileSystemLoader(str(tmpl_root)))
    generate_rcv_path_scaffolds_from_alchemy(
        d_set=d_set,
        out_path=str(tmp_path),
        env=env,
        get_db_import="resi_fapi.deps.al2r_db:get_db",
    )
    assert (tmp_path / "__init__.py").is_file()
    assert (tmp_path / "api.py").is_file()
    rpath = tmp_path / "root_row_rcv_paths.py"
    assert rpath.is_file()
    assert "def get_def" in rpath.read_text(encoding="utf-8")


def test_parse_get_db_import_splits_module_and_symbol() -> None:
    """``module:symbol`` splits into import pieces."""

    assert parse_get_db_import("resi_fapi.deps.al2r_db:get_db") == (
        "resi_fapi.deps.al2r_db",
        "get_db",
    )
    assert parse_get_db_import("pkg.mod:session_dep") == (
        "pkg.mod",
        "session_dep",
    )


def test_generate_root_api_imports_renamed_get_db_as_alias(
    tmp_path: Path,
) -> None:
    """Non-``get_db`` symbols are imported with an ``as get_db`` alias."""

    class _Orm:
        __tablename__ = "widgets"

    res = ExResource(
        name="Widget",
        src=_Orm,
        categories=[],
        fields=[
            IntField(name="id", primary=True, nullable=False),
        ],
        label_ast=parse_expr("id"),
    )
    d_set = _minimal_dataset([res])
    tmpl_root = (
        Path(__file__).resolve().parent.parent
        / "exdrf_gen_al2rcv"
        / "al2rcv_templates"
    )
    env = Environment(loader=FileSystemLoader(str(tmpl_root)))
    generate_rcv_path_scaffolds_from_alchemy(
        d_set=d_set,
        out_path=str(tmp_path),
        env=env,
        get_db_import="pkg.rcv_db:session_scope",
    )
    root_api = (tmp_path / "api.py").read_text(encoding="utf-8")
    assert "from pkg.rcv_db import session_scope as get_db" in root_api
