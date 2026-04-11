"""Emit FastAPI ``APIRouter`` stubs from an ``ExDataset`` built via SQLAlchemy."""

from __future__ import annotations

import keyword
import os
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Dict, List, Tuple, cast

from attrs import define, field
from exdrf_gen.fs_support import Base, File, TopDir, resource_to_args
from exdrf_gen_al2pd.pydantic_emit import (
    build_al2pd_template_kwargs,
    resource_generates_edit_payload,
)
from jinja2 import Environment

from exdrf_gen_al2r.list_query_specs import build_al2r_list_relation_query_specs
from exdrf_gen_al2r.list_route_specs import build_al2r_list_relation_route_specs
from exdrf_gen_al2r.relation_specs import (
    build_al2r_relation_sync_specs,
    extra_orm_classes_for_relations,
)

if TYPE_CHECKING:
    from exdrf.resource import ExResource


def primary_key_field_name(resource: Any) -> str:
    """Pick a path-parameter name for the resource primary key.

    Args:
        resource: Dataset resource (``ExResource``) or compatible duck type.

    Returns:
        Field name to use in route paths (for example ``id``).
    """

    for fld in resource.fields:
        if getattr(fld, "primary", False):
            return fld.name
    for candidate in ("id", "uuid"):
        if candidate in resource:
            return candidate
    if resource.fields:
        return resource.fields[0].name
    return "id"


def primary_key_names_for_routes(resource: Any) -> List[str]:
    """Ordered primary key field names for path segments.

    Args:
        resource: ``ExResource`` with ``primary_fields``.

    Returns:
        Non-empty list of path parameter names.
    """

    names = list(resource.primary_fields())
    if names:
        return names
    return [primary_key_field_name(resource)]


def path_pk_segment(pk_names: List[str]) -> str:
    """Build ``{a}/{b}`` path fragment for FastAPI path parameters.

    Args:
        pk_names: Primary key Python names.

    Returns:
        Slash-separated ``{name}`` segments without leading slash.
    """

    return "/".join(f"{{{n}}}" for n in pk_names)


def schema_module_dotted(schemas_root: str, resource: Any) -> str:
    """Dotted import path for the generated schema module for ``resource``.

    Args:
        schemas_root: Package root (e.g. ``myapp.generated.schemas``).
        resource: ``ExResource`` with ``categories`` and
            ``snake_case_name_plural``.

    Returns:
        Import string such as ``myapp.generated.schemas.a.b.widgets``.
    """

    parts = [
        schemas_root,
        *getattr(resource, "categories", ()),
        resource.snake_case_name_plural,
    ]
    return ".".join(p for p in parts if p)


def category_router_export_name(categories: Tuple[str, ...]) -> str:
    """Python name for the aggregate :class:`fastapi.APIRouter` in a category dir.

    Args:
        categories: Resource category path (e.g. ``("ancpi",)``).

    Returns:
        Identifier such as ``ancpi_router`` or ``issues_l18_router``.
    """

    base = "_".join(categories) + "_router"
    if keyword.iskeyword(base):
        return "%s_" % (base,)
    return base


def category_path_prefix(categories: Tuple[str, ...]) -> str:
    """URL prefix for the category aggregate router.

    Args:
        categories: Resource category path segments.

    Returns:
        Leading-slash path (e.g. ``/ancpi`` or ``/issues/l18``).
    """

    return "/" + "/".join(categories)


def _category_tags_repr(categories: Tuple[str, ...]) -> str:
    """Return a Python list literal string for FastAPI ``tags=``."""

    return repr(list(categories))


def parse_get_db_import(spec: str) -> Tuple[str, str]:
    """Split ``module.path:callable`` for generated ``from … import … as get_db``.

    Args:
        spec: Import location in ``dotted.module:symbol`` form (one ``:``).

    Returns:
        Tuple of ``(dotted_module, symbol)``.

    Raises:
        ValueError: If ``spec`` is empty, has no ``:``, or parts are empty.
    """

    raw = (spec or "").strip()
    if not raw:
        raise ValueError("get_db import spec must be non-empty.")
    if ":" not in raw:
        raise ValueError(
            "get_db import must look like 'pkg.mod:dependency_fn' "
            "(got %r)." % (spec,),
        )
    mod, _, symbol = raw.rpartition(":")
    mod = mod.strip()
    symbol = symbol.strip()
    if not mod or not symbol:
        raise ValueError(
            "get_db import must look like 'pkg.mod:dependency_fn' "
            "(got %r)." % (spec,),
        )
    return mod, symbol


def _unidecode_companion_pairs(resource: Any) -> List[Dict[str, str]]:
    """Build ``(source, ua_target)`` pairs for NO_DIACRITICS companion columns.

    Args:
        resource: ``ExResource`` whose string fields may set ``no_dia_field``.

    Returns:
        Dicts with keys ``source`` and ``target`` (ORM attribute names).
    """

    pairs: List[Dict[str, str]] = []
    for fld in getattr(resource, "fields", ()) or ():
        target = getattr(fld, "no_dia_field", None)
        if target is None:
            continue
        tgt_name = getattr(target, "name", "") or ""
        if not tgt_name:
            continue
        pairs.append({"source": fld.name, "target": tgt_name})
    return pairs


def _restrict_loader_to_al2r_templates(env: Environment) -> None:
    """Limit Jinja search paths to this package's templates."""

    loader = getattr(env, "loader", None)
    if loader is None:
        return
    paths = list(getattr(loader, "paths", []))
    filtered = [p for p in paths if str(p).endswith("al2r_templates")]
    setattr(loader, "paths", filtered)


@define
class Al2rRouterResFile(Base):
    """Emit one ``{res_snake}_routes.py`` stub per resource under category path.

    Output layout matches :class:`~exdrf_gen_al2pd.creator.Al2pdSchemaResFile`:
    ``out / *resource.categories / {res_snake}_routes.py`` (empty categories →
    output root).

    Attributes:
        template: Jinja template path (e.g. ``al2r/resource_router.py.j2``).
        extra: Extra context merged into every render.
    """

    template: str = field()
    extra: Dict[str, Any] = field(factory=dict)

    def generate(self, out_path: str, **kwargs: Any) -> None:
        """Write each resource's router module."""

        env = kwargs.pop("env")
        source_module = kwargs.get("source_module", __name__)
        db_module = kwargs["db_module"]
        schemas_root = kwargs["schemas_root"]
        base = {**self.extra, **kwargs}
        for resource in kwargs["resources"]:
            res = cast("ExResource", resource)
            rargs = resource_to_args(res)
            orm_name = res.src.__name__ if res.src is not None else res.name
            pk_names = primary_key_names_for_routes(res)
            cats_t = tuple(res.categories or ())
            cr_name = category_router_export_name(cats_t) if cats_t else ""
            pd_kw = build_al2pd_template_kwargs(res)
            uni_pairs = _unidecode_companion_pairs(res)
            create_specs = pd_kw.get("al2pd_create_scalar_fields") or ()
            rel_specs, rel_all_ok = build_al2r_relation_sync_specs(res)
            extra_orms = extra_orm_classes_for_relations(orm_name, rel_specs)
            list_rel_specs = build_al2r_list_relation_route_specs(pd_kw)
            list_rel_query_specs = build_al2r_list_relation_query_specs(
                res,
                list_rel_specs,
                rel_specs,
            )
            list_rel_types = sorted(
                {s["related_name"] for s in list_rel_specs},
            )
            args = {
                **base,
                **rargs,
                **pd_kw,
                "model": res,
                "db_module": db_module,
                "orm_class_name": orm_name,
                "pk_names": pk_names,
                "path_pk_segment": path_pk_segment(pk_names),
                "schema_module": schema_module_dotted(schemas_root, res),
                "generate_edit": resource_generates_edit_payload(res),
                "m_name": source_module,
                "al2r_category_router_name": cr_name,
                "al2r_unidecode_pairs": uni_pairs,
                "al2r_needs_unidecode": bool(uni_pairs),
                "al2r_create_has_deleted": any(
                    getattr(s, "name", None) == "deleted" for s in create_specs
                ),
                "al2r_relation_sync_specs": rel_specs,
                "al2r_all_list_relations_supported": rel_all_ok,
                "al2r_extra_orm_imports": extra_orms,
                "al2r_list_relation_routes": list_rel_specs,
                "al2r_list_relation_query_specs": list_rel_query_specs,
                "al2r_list_relation_related_types": list_rel_types,
            }
            dest = os.path.join(out_path, *cats_t)
            self.create_file(
                env,
                dest,
                "{res_snake}_routes.py",
                self.template,
                **args,
            )


@define
class Al2rCategoryInitFile(Base):
    """Emit ``__init__.py`` defining the named aggregate ``APIRouter`` per path.

    One router per distinct category directory (e.g. ``ancpi_router`` under
    ``ancpi/__init__.py``). Resource modules import this symbol from the same
    package; :class:`Al2rCategoryApiFile` mounts each resource ``router`` on it.

    Attributes:
        template: Jinja template path (e.g. ``al2r/category_init.py.j2``).
        extra: Extra context merged into every render.
    """

    template: str = field()
    extra: Dict[str, Any] = field(factory=dict)

    def generate(self, out_path: str, **kwargs: Any) -> None:
        """Write one ``__init__.py`` per distinct non-root category path."""

        env = kwargs.pop("env")
        base = {**self.extra, **kwargs}
        seen: set[Tuple[str, ...]] = set()
        for resource in kwargs["resources"]:
            res = cast("ExResource", resource)
            raw_cats = tuple(res.categories or ())
            if not raw_cats or raw_cats in seen:
                continue
            seen.add(raw_cats)
            dest = os.path.join(out_path, *raw_cats)
            self.create_file(
                env,
                dest,
                "__init__.py",
                self.template,
                **base,
                al2r_category_router_name=category_router_export_name(raw_cats),
                al2r_category_path_prefix=category_path_prefix(raw_cats),
                al2r_category_tags_repr=_category_tags_repr(raw_cats),
            )


@define
class Al2rCategoryApiFile(Base):
    """Emit ``api.py`` that mounts every ``*_routes`` router on the package router.

    Imports the aggregate router from ``__init__.py`` (same package) and
    :meth:`fastapi.APIRouter.include_router` for each resource in that category
    path.

    Attributes:
        template: Jinja template path (e.g. ``al2r/category_api.py.j2``).
        extra: Extra context merged into every render.
    """

    template: str = field()
    extra: Dict[str, Any] = field(factory=dict)

    def generate(self, out_path: str, **kwargs: Any) -> None:
        """Write one ``api.py`` per distinct category path."""

        env = kwargs.pop("env")
        base = {**self.extra, **kwargs}
        by_cat: Dict[Tuple[str, ...], List[Any]] = defaultdict(list)
        for resource in kwargs["resources"]:
            res = cast("ExResource", resource)
            cats = tuple(res.categories or ())
            if not cats:
                continue
            by_cat[cats].append(res)

        for cats in sorted(by_cat.keys(), key=lambda c: c):
            rows = sorted(by_cat[cats], key=lambda r: r.name)
            entries = [
                {
                    "route_module": "%s_routes" % (r.snake_case_name,),
                    "router_alias": "%s_routes_router" % (r.snake_case_name,),
                }
                for r in rows
            ]
            dest = os.path.join(out_path, *cats)
            self.create_file(
                env,
                dest,
                "api.py",
                self.template,
                **base,
                al2r_category_router_name=category_router_export_name(cats),
                al2r_category_api_route_entries=entries,
            )


def generate_fastapi_routes_from_alchemy(
    d_set: Any,
    out_path: str,
    db_module: str,
    schemas_root: str,
    env: Environment,
    *,
    get_db_import: str | None = None,
) -> None:
    """Write route stubs via :class:`~exdrf_gen.fs_support.TopDir`.

    Args:
        d_set: ``ExDataset`` populated by
            ``exdrf_al.loader.dataset_from_sqlalchemy``.
        out_path: Directory to write Python modules into (created if missing).
            Route modules mirror ``al2pd`` layout:
            ``out / *categories / {res_snake}_routes.py``; uncategorized
            resources stay at ``out``. Each category package defines
            ``{cat}_router`` in ``__init__.py``; per-category ``api.py`` mounts
            resource routers on it. Root ``__init__.py`` defines the aggregate
            ``router``; root ``api.py`` imports it with ``from . import router``
            and calls ``include_router`` for every category router and every
            uncategorized resource router (same pattern as each category
            ``api.py``). Root ``__init__.py`` ends with ``from . import api`` so
            importing the package mounts children. Existing root
            ``*_routes.py`` files are removed before writing so prior flat outputs
            do not linger.
        db_module: Dotted import path for SQLAlchemy declarative models.
        schemas_root: Dotted package root where ``al2pd`` wrote schema modules.
        env: Shared Jinja environment (``context.obj[\"jinja_env\"]``).
        get_db_import: Optional ``dotted.module:attr`` for the FastAPI DB
            dependency; emitted as ``from … import attr as get_db``. When
            omitted, generated modules define a stub ``get_db`` that raises
            ``NotImplementedError``.
    """

    _restrict_loader_to_al2r_templates(env)

    al2r_get_db_module: str | None = None
    al2r_get_db_attr: str | None = None
    if get_db_import:
        al2r_get_db_module, al2r_get_db_attr = parse_get_db_import(
            get_db_import
        )

    # Drop root-level ``*_routes.py`` from an older flat layout so categorized
    # resources do not leave duplicate modules next to the new per-category tree.
    if os.path.isdir(out_path):
        for entry in os.scandir(out_path):
            if entry.is_file() and entry.name.endswith("_routes.py"):
                os.unlink(entry.path)

    models_list = list(d_set.resources)
    uncategorized = [
        m for m in models_list if not getattr(m, "categories", None)
    ]
    cat_keys = sorted(
        {
            tuple(cast("ExResource", m).categories)
            for m in models_list
            if getattr(m, "categories", None)
        },
        key=lambda c: c,
    )
    root_category_imports = [
        {
            "rel_import": ".".join((*cats, "api")),
            "router_symbol": category_router_export_name(cats),
        }
        for cats in cat_keys
    ]

    generator = TopDir(
        comp=[
            File("al2r_route_utils.py", "al2r/route_utils.py.j2"),
            Al2rCategoryInitFile(template="al2r/category_init.py.j2"),
            Al2rRouterResFile(template="al2r/resource_router.py.j2"),
            Al2rCategoryApiFile(template="al2r/category_api.py.j2"),
            File("__init__.py", "al2r/package_init.py.j2"),
            File("api.py", "al2r/root_api.py.j2"),
        ],
    )
    generator.generate(
        dset=d_set,
        env=env,
        out_path=out_path,
        m_name=__name__,
        source_module=__name__,
        models=models_list,
        db_module=db_module,
        schemas_root=schemas_root,
        al2r_root_category_imports=root_category_imports,
        al2r_root_uncategorized_models=uncategorized,
        al2r_get_db_module=al2r_get_db_module,
        al2r_get_db_attr=al2r_get_db_attr,
    )
