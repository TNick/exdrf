"""Tests for ``exdrf_gen_al2r.creator``."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from exdrf.field_types.int_field import IntField
from exdrf.field_types.str_field import StrField
from exdrf.label_dsl import parse_expr
from exdrf.resource import ExResource
from jinja2 import Environment, FileSystemLoader

from exdrf_gen_al2r.creator import (
    build_al2r_list_relation_import_groups,
    category_router_export_name,
    generate_fastapi_routes_from_alchemy,
    parse_get_db_import,
    path_pk_segment,
    primary_key_names_for_routes,
    schema_module_dotted,
)


def _minimal_dataset(resources: list) -> SimpleNamespace:
    """Shim ``ExDataset`` API required by :class:`~exdrf_gen.fs_support.TopDir`."""

    r = list(resources)
    return SimpleNamespace(
        resources=r,
        category_map={},
        zero_categories=lambda: [],
        sorted_by_deps=lambda: r,
    )


def test_primary_key_names_for_routes_prefers_flag() -> None:
    """The first ``primary`` field wins ordering by ``primary_fields``."""

    class R:
        fields = [SimpleNamespace(name="uuid", primary=True)]

        def primary_fields(self):
            return ["uuid"]

        def __contains__(self, key: str) -> bool:
            return key == "uuid"

    assert primary_key_names_for_routes(R()) == ["uuid"]


def test_path_pk_segment_joins() -> None:
    """Path segments use FastAPI brace syntax."""

    assert path_pk_segment(["id"]) == "{id}"
    assert path_pk_segment(["a", "b"]) == "{a}/{b}"


def test_schema_module_dotted() -> None:
    """Schema import path mirrors categories + plural module stem."""

    r = ExResource(name="Widget", categories=["x", "y"])
    assert schema_module_dotted("app.schemas", r) == "app.schemas.x.y.widgets"


def test_build_al2r_list_relation_import_groups_empty_without_refs() -> None:
    """Resources with no list relations yield no extra schema import groups."""

    class _Orm:
        __tablename__ = "widgets"

    res = ExResource(
        name="Widget",
        src=_Orm,
        fields=[
            IntField(name="id", primary=True, nullable=False),
            StrField(name="title", nullable=False),
        ],
        label_ast=parse_expr("title"),
    )
    assert build_al2r_list_relation_import_groups("app.schemas", res) == []


def test_parse_get_db_import_splits_module_and_symbol() -> None:
    """``dotted.module:callable`` maps to a two-part import."""

    assert parse_get_db_import("resi_fapi.deps.al2r_db:get_db") == (
        "resi_fapi.deps.al2r_db",
        "get_db",
    )


def test_category_router_export_name_joins_path() -> None:
    """Aggregate router identifier uses underscore-joined category segments."""

    assert category_router_export_name(("ancpi",)) == "ancpi_router"
    assert category_router_export_name(("issues", "l18")) == "issues_l18_router"


def test_generate_writes_router_with_schemas(tmp_path: Path) -> None:
    """Routers import ``Ex`` models and include POST; PATCH when Edit exists."""

    class _Orm:
        __tablename__ = "widgets"

    res = ExResource(
        name="Widget",
        src=_Orm,
        fields=[
            IntField(name="id", primary=True, nullable=False),
            StrField(name="title", nullable=False),
        ],
        label_ast=parse_expr("title"),
    )
    d_set = _minimal_dataset([res])

    tmpl_root = (
        Path(__file__).resolve().parents[1]
        / "exdrf_gen_al2r"
        / "al2r_templates"
    )
    env = Environment(loader=FileSystemLoader(str(tmpl_root)))

    generate_fastapi_routes_from_alchemy(
        d_set=d_set,
        out_path=str(tmp_path),
        db_module="test_app.models",
        schemas_root="test_app.schemas",
        env=env,
    )

    routes = tmp_path / "widget_routes.py"
    assert routes.is_file()
    body = routes.read_text(encoding="utf-8")
    assert "from test_app.schemas.widgets import" in body
    assert "WidgetEx" in body
    assert "WidgetCreate" in body
    assert "PagedList[WidgetEx]" in body
    assert "response_model=PagedList[WidgetEx]" in body
    assert "inner_list_page_size" in body
    assert "inner_filters" in body
    assert "inner_sort" in body
    assert "FilterItem" in body
    assert "SortItem" in body
    assert "exdrf_pd.paged" in body
    assert "return list_root_ex_page(" in body
    assert "def list_widget" in body
    assert "filter_op_registry" in body
    utils_body = (tmp_path / "al2r_route_utils.py").read_text(encoding="utf-8")
    assert "def parse_filter_items_json" in utils_body
    assert "filter_op_registry" in utils_body
    assert body.count("response_model=WidgetEx") == 3
    assert "-> WidgetEx:" in body
    assert "@router.patch" in body
    assert "WidgetEdit" in body
    assert "payload = body.model_dump(exclude_unset=True)" in body
    assert "status.HTTP_201_CREATED" in body
    assert "    persist_row_as_ex," in body
    assert "return persist_row_as_ex(db, row, WidgetEx, add=True)" in body
    assert "return persist_row_as_ex(db, row, WidgetEx)" in body
    assert "get_one_or_404" in body
    get_start = body.index("def get_widget")
    patch_start = body.index("def patch_widget")
    get_block = body[get_start:patch_start]
    assert "get_one_or_404" in get_block
    assert "WidgetEx.model_validate" in get_block
    assert "inner_list_page_size" in get_block
    assert "NotImplementedError" not in get_block
    assert "row = apply_payload_attrs(" in body
    assert "apply_payload_attrs" in body
    assert "from .al2r_route_utils import" in body
    assert (tmp_path / "al2r_route_utils.py").is_file()

    init_py = tmp_path / "__init__.py"
    assert init_py.is_file()
    root_api = tmp_path / "api.py"
    assert root_api.is_file()
    root_api_body = root_api.read_text(encoding="utf-8")
    assert "from . import router" in root_api_body
    assert "from .widget_routes import router as widget_router" in root_api_body
    assert "router.include_router(widget_router)" in root_api_body
    assert "router = APIRouter" not in root_api_body
    init_body = init_py.read_text(encoding="utf-8")
    assert "router = APIRouter" in init_body
    assert 'tags=["generated"]' not in init_body


def test_generate_get_db_import_line(tmp_path: Path) -> None:
    """Passing ``get_db_import`` emits ``from … import … as get_db``."""

    class _Orm:
        __tablename__ = "widgets"

    res = ExResource(
        name="Widget",
        src=_Orm,
        fields=[
            IntField(name="id", primary=True, nullable=False),
            StrField(name="title", nullable=False),
        ],
        label_ast=parse_expr("title"),
    )
    d_set = _minimal_dataset([res])

    tmpl_root = (
        Path(__file__).resolve().parents[1]
        / "exdrf_gen_al2r"
        / "al2r_templates"
    )
    env = Environment(loader=FileSystemLoader(str(tmpl_root)))

    generate_fastapi_routes_from_alchemy(
        d_set=d_set,
        out_path=str(tmp_path),
        db_module="test_app.models",
        schemas_root="test_app.schemas",
        env=env,
        get_db_import="email.mime.text:MIMEText",
    )

    body = (tmp_path / "widget_routes.py").read_text(encoding="utf-8")
    assert "from email.mime.text import MIMEText as get_db" in body
    assert "def get_db()" not in body


def test_generate_omits_patch_for_composite_pk_link(tmp_path: Path) -> None:
    """Composite-PK-only rows skip PATCH (no ``XxxEdit``)."""

    class _Orm:
        __tablename__ = "link_rows"

    link = ExResource(
        name="LinkRow",
        src=_Orm,
        fields=[
            IntField(name="left_id", primary=True, nullable=False),
            IntField(name="right_id", primary=True, nullable=False),
        ],
        label_ast=parse_expr("(concat left_id)"),
    )
    d_set = _minimal_dataset([link])

    tmpl_root = (
        Path(__file__).resolve().parents[1]
        / "exdrf_gen_al2r"
        / "al2r_templates"
    )
    env = Environment(loader=FileSystemLoader(str(tmpl_root)))

    generate_fastapi_routes_from_alchemy(
        d_set=d_set,
        out_path=str(tmp_path),
        db_module="test_app.models",
        schemas_root="test_app.schemas",
        env=env,
    )

    body = (tmp_path / "link_row_routes.py").read_text(encoding="utf-8")
    assert (tmp_path / "al2r_route_utils.py").is_file()
    assert "persist_row_as_ex" in body
    assert "return persist_row_as_ex(db, row, LinkRowEx, add=True)" in body
    assert "from .al2r_route_utils import get_one_or_404" in body
    assert "response_model=PagedList[LinkRowEx]" in body
    assert body.count("response_model=LinkRowEx") == 2
    assert "@router.patch" not in body
    assert "LinkRowEdit" not in body
    assert "{left_id}/{right_id}" in body
    assert "payload = body.model_dump(exclude_unset=True)" in body
    assert '("left_id", left_id),' in body
    assert '("right_id", right_id),' in body
    link_get_start = body.index("def get_link_row")
    rest_after_get = body[link_get_start + 1 :]
    next_def = rest_after_get.find("\ndef ")
    get_link_block = (
        body[link_get_start:]
        if next_def == -1
        else body[link_get_start : link_get_start + 1 + next_def]
    )
    assert "get_one_or_404" in get_link_block
    assert "LinkRowEx.model_validate" in get_link_block
    assert "NotImplementedError" not in get_link_block


def test_generate_writes_category_subdir_and_init(tmp_path: Path) -> None:
    """Resources with ``categories`` emit under ``out/<cat>/`` plus ``__init__.py``."""

    class _Orm:
        __tablename__ = "widgets"

    res = ExResource(name="Widget", src=_Orm, categories=["l18"])
    d_set = _minimal_dataset([res])

    tmpl_root = (
        Path(__file__).resolve().parents[1]
        / "exdrf_gen_al2r"
        / "al2r_templates"
    )
    env = Environment(loader=FileSystemLoader(str(tmpl_root)))

    generate_fastapi_routes_from_alchemy(
        d_set=d_set,
        out_path=str(tmp_path),
        db_module="test_app.models",
        schemas_root="test_app.schemas",
        env=env,
    )

    routes = tmp_path / "l18" / "widget_routes.py"
    assert routes.is_file()
    cat_init = tmp_path / "l18" / "__init__.py"
    assert cat_init.is_file()

    api_py = tmp_path / "l18" / "api.py"
    assert api_py.is_file()
    api_body = api_py.read_text(encoding="utf-8")
    assert "from . import l18_router" in api_body
    assert (
        "from .widget_routes import router as widget_routes_router" in api_body
    )
    assert "l18_router.include_router(widget_routes_router)" in api_body
    assert '__all__ = ["l18_router"]' in api_body

    root_init = (tmp_path / "__init__.py").read_text(encoding="utf-8")
    assert "router = APIRouter" in root_init
    assert 'tags=["generated"]' not in root_init

    root_api = (tmp_path / "api.py").read_text(encoding="utf-8")
    assert "from . import router" in root_api
    assert "from .l18.api import l18_router" in root_api
    assert "router.include_router(l18_router)" in root_api

    cat_init_body = cat_init.read_text(encoding="utf-8")
    assert "l18_router = APIRouter" in cat_init_body
    assert 'prefix="/l18"' in cat_init_body
    assert "tags=" not in cat_init_body

    body = routes.read_text(encoding="utf-8")
    assert "from ..al2r_route_utils import" in body
    assert "from . import l18_router" in body
    assert "from test_app.schemas.l18.widgets import" in body
