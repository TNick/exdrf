"""Tests for al2pd pydantic emit and partitioning."""

from __future__ import annotations

import json
import re

import exdrf_gen_al2pd  # noqa: F401 — register templates on shared Jinja env

from exdrf.label_dsl import parse_expr
from exdrf.resource import ExResource
from exdrf.field_types.date_time import DateTimeField
from exdrf.field_types.int_field import IntField
from exdrf.field_types.str_field import StrField

from exdrf_gen.jinja_support import jinja_env
from exdrf_gen_al2pd.pydantic_emit import (
    _field_exdrf_properties,
    _folded_json_string_literal,
    build_al2pd_template_kwargs,
    resource_generates_edit_payload,
)


def test_folded_description_prefers_whitespace_breaks() -> None:
    """Fold long descriptions at spaces; avoid mid-word cuts (e.g. addre + ss)."""

    text = (
        "Special handling for some entries "
        "(like indicating an official address)"
    )
    folded = _folded_json_string_literal(text, max_single_line=20)
    pieces = re.findall(r'"(?:\\.|[^"\\])*"', folded)
    reconstructed = "".join(json.loads(p) for p in pieces)
    assert reconstructed == text
    for p in pieces:
        assert not json.loads(p).endswith("addre")


def test_build_al2pd_emits_four_models_with_edit() -> None:
    """Single PK resource gets Create + Edit; audit field omitted."""

    w = ExResource(
        name="Widget",
        fields=[
            IntField(name="id", primary=True, nullable=False),
            StrField(name="title", nullable=False),
            DateTimeField(name="created_on", nullable=True),
        ],
        label_ast=parse_expr("title"),
    )
    kwargs = build_al2pd_template_kwargs(w)
    text = jinja_env.get_template("al2pd/interface.py.j2").render(
        m_name="test",
        model_name=w.name,
        **kwargs,
    )
    assert "class Widget(ExModel):" in text
    assert "class WidgetEx(Widget):" in text
    assert "class WidgetCreate(ExModel):" in text
    assert "class WidgetEdit(ExModel):" in text
    assert kwargs["al2pd_generate_edit"] is True
    assert resource_generates_edit_payload(w) is True
    c_names = [s.name for s in kwargs["al2pd_create_scalar_fields"]]
    e_names = [s.name for s in kwargs["al2pd_edit_scalar_fields"]]
    assert "created_on" not in c_names
    assert "created_on" not in e_names


def test_composite_pk_link_no_edit_class() -> None:
    """Two PK scalars and nothing else → Create only, no Edit."""

    link = ExResource(
        name="LinkRow",
        fields=[
            IntField(name="left_id", primary=True, nullable=False),
            IntField(name="right_id", primary=True, nullable=False),
        ],
        label_ast=parse_expr("(concat left_id)"),
    )
    kwargs = build_al2pd_template_kwargs(link)
    text = jinja_env.get_template("al2pd/interface.py.j2").render(
        m_name="test",
        model_name=link.name,
        **kwargs,
    )
    assert kwargs["al2pd_generate_edit"] is False
    assert resource_generates_edit_payload(link) is False
    assert "class LinkRowCreate(ExModel):" in text
    assert "class LinkRowEdit" not in text


def test_primary_simple_omits_pk_on_create_payload_fields() -> None:
    """``is_primary_simple`` omits the lone PK from Create/Edit scalars."""

    w = ExResource(
        name="Gadget",
        fields=[
            IntField(name="id", primary=True, nullable=False),
            StrField(name="code", nullable=False),
        ],
        label_ast=parse_expr("code"),
    )
    kwargs = build_al2pd_template_kwargs(w)
    create_names = [s.name for s in kwargs["al2pd_create_scalar_fields"]]
    edit_names = [s.name for s in kwargs["al2pd_edit_scalar_fields"]]
    assert "id" not in create_names
    assert "id" not in edit_names
    assert "code" in create_names
    assert "code" in edit_names


def test_exdrf_payload_omits_redundant_field_keys() -> None:
    """Exdrf dicts omit redundant keys (name, title, resource, type, etc.)."""

    w = ExResource(
        name="Widget",
        fields=[
            IntField(name="id", primary=True, nullable=False),
            StrField(
                name="title",
                nullable=False,
                title="Title",
                description="Shown in listings.",
            ),
        ],
        label_ast=parse_expr("title"),
    )
    title_f = next(f for f in w.fields if f.name == "title")
    props = _field_exdrf_properties(title_f)
    assert "name" not in props
    assert "title" not in props
    assert "resource" not in props
    assert "type_name" not in props
    assert "description" not in props
    assert "nullable" not in props
    assert "read_only" not in props


def test_exdrf_payload_category_omits_general_only() -> None:
    """``category`` is absent for ``general``; kept for other buckets."""

    w = ExResource(
        name="Widget",
        fields=[
            IntField(name="id", primary=True, nullable=False),
            StrField(name="code", nullable=False, category="audit"),
            StrField(name="title", nullable=False),
        ],
        label_ast=parse_expr("code"),
    )
    id_f = next(f for f in w.fields if f.name == "id")
    code_f = next(f for f in w.fields if f.name == "code")
    title_f = next(f for f in w.fields if f.name == "title")
    assert _field_exdrf_properties(id_f).get("category") == "keys"
    assert _field_exdrf_properties(code_f).get("category") == "audit"
    assert "category" not in _field_exdrf_properties(title_f)


def test_exdrf_payload_read_only_only_when_true() -> None:
    """``read_only`` appears in exdrf JSON only for read-only fields."""

    w = ExResource(
        name="Widget",
        fields=[
            IntField(name="id", primary=True, nullable=False, read_only=True),
            StrField(name="code", nullable=False),
        ],
        label_ast=parse_expr("code"),
    )
    id_f = next(f for f in w.fields if f.name == "id")
    code_f = next(f for f in w.fields if f.name == "code")
    assert _field_exdrf_properties(id_f).get("read_only") is True
    assert "read_only" not in _field_exdrf_properties(code_f)


def test_exdrf_assignments_literal_omits_redundant_keys() -> None:
    """Resource assignment omits redundant keys; fields use inline ``exdrf``."""

    w = ExResource(
        name="Widget",
        fields=[
            IntField(name="id", primary=True, nullable=False),
            StrField(name="code", nullable=False),
        ],
        label_ast=parse_expr("code"),
    )
    kwargs = build_al2pd_template_kwargs(w)
    assigns = kwargs["al2pd_exdrf_assignments"]
    assert kwargs["al2pd_resource_exdrf_var"] is None
    assert assigns == []
    id_spec = next(s for s in kwargs["al2pd_simple_fields"] if s.name == "id")
    assert id_spec.json_schema_extra_expr is not None
    for spec in kwargs["al2pd_simple_fields"]:
        ex = spec.json_schema_extra_expr
        if ex is None:
            continue
        assert "json.loads" not in ex
        assert '"name":' not in ex
        assert '"nullable":' not in ex
