"""Emit remote-controlled-view path module scaffolds from ``ExDataset``."""

from __future__ import annotations

import os
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Dict, List, Tuple, cast

from attrs import define, field
from exdrf_gen.fs_support import Base, File, TopDir, resource_to_args
from jinja2 import Environment

from exdrf_gen_al2rcv.rcv_field_emit import (
    build_rcv_field_dicts_for_resource,
    default_rcv_render_type,
    rcv_field_dicts_py_literal,
)

if TYPE_CHECKING:
    from exdrf.resource import ExResource


def parse_get_db_import(spec: str) -> Tuple[str, str]:
    """Split ``module.path:callable`` for ``from … import … as get_db``.

    Args:
        spec: Import location in ``dotted.module:symbol`` form (one ``:``).

    Returns:
        Tuple of ``(dotted_module, symbol)``.

    Raises:
        ValueError: If ``spec`` is empty, has no ``:``, or parts are empty.
    """

    # Normalize whitespace so env-var defaults do not trip validation.
    raw = (spec or "").strip()

    # Require a non-empty spec before splitting.
    if not raw:
        raise ValueError("get_db import spec must be non-empty.")

    # Exactly one ``:`` separates module path from callable name.
    if ":" not in raw:
        raise ValueError(
            "get_db import must look like 'pkg.mod:dependency_fn' "
            "(got %r)." % (spec,),
        )

    # ``rpartition`` keeps dotted modules intact (only the last ``:`` splits).
    mod, _, symbol = raw.rpartition(":")
    mod = mod.strip()
    symbol = symbol.strip()

    # Reject ``":fn"`` or ``"mod:"`` style garbage after stripping.
    if not mod or not symbol:
        raise ValueError(
            "get_db import must look like 'pkg.mod:dependency_fn' "
            "(got %r)." % (spec,),
        )
    return mod, symbol


def _restrict_loader_to_al2rcv_templates(env: Environment) -> None:
    """Limit Jinja search paths to this package's templates."""

    loader = getattr(env, "loader", None)

    # Some callers pass a bare env; nothing to narrow.
    if loader is None:
        return

    # Drop unrelated template dirs so ``al2rcv/...`` resolves unambiguously.
    paths = list(getattr(loader, "paths", []))
    filtered = [p for p in paths if str(p).endswith("al2rcv_templates")]
    setattr(loader, "paths", filtered)


@define
class Al2rcvResourcePathFile(Base):
    """Emit one ``{res_snake}_rcv_paths.py`` per categorized resource.

    Output layout mirrors ``exdrf-gen-al2r`` route files:
    ``out / *resource.categories / {res_snake}_rcv_paths.py`` (empty
    categories place files at ``out`` root next to root ``__init__.py``).

    Attributes:
        template: Jinja template path (for example
            ``al2rcv/resource_rcv_paths.py.j2``).
        extra: Extra context merged into every render.
    """

    template: str = field()
    extra: Dict[str, Any] = field(factory=dict)

    def generate(self, out_path: str, **kwargs: Any) -> None:
        """Write each resource's RCV path scaffold module."""

        # ``env`` is consumed here so child templates do not see it twice.
        env = kwargs.pop("env")
        base = {**self.extra, **kwargs}

        # One ``*_rcv_paths.py`` per resource, under its category path (or out).
        for resource in kwargs["resources"]:
            res = cast("ExResource", resource)
            r_args = resource_to_args(res)
            cats_t = tuple(res.categories or ())

            # Precompute validated field dicts and their Python literal for
            # Jinja.
            rcv_rows = build_rcv_field_dicts_for_resource(res)
            args = {
                **base,
                **r_args,
                "model": res,
                "rcv_field_dicts_repr": rcv_field_dicts_py_literal(rcv_rows),
                "rcv_render_type_repr": repr(default_rcv_render_type()),
                "al2rcv_category_dot_path": (
                    ".".join(cats_t) if cats_t else ""
                ),
            }

            dest = os.path.join(out_path, *cats_t)
            self.create_file(
                env,
                dest,
                "{res_snake}_rcv_paths.py",
                self.template,
                **args,
            )


@define
class Al2rcvCategoryInitFile(Base):
    """Emit a minimal ``__init__.py`` for each distinct category directory.

    Attributes:
        template: Jinja template path (e.g. ``al2rcv/category_init.py.j2``).
        extra: Extra context merged into every render.
    """

    template: str = field()
    extra: Dict[str, Any] = field(factory=dict)

    def generate(self, out_path: str, **kwargs: Any) -> None:
        """Write one ``__init__.py`` per distinct non-root category path."""

        env = kwargs.pop("env")
        base = {**self.extra, **kwargs}

        # Emit at most one package init per distinct category tuple.
        seen: set[Tuple[str, ...]] = set()
        for resource in kwargs["resources"]:
            res = cast("ExResource", resource)
            raw_cats = tuple(res.categories or ())

            # Skip uncategorized resources and duplicates of the same category.
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
                al2rcv_category_dot_path=".".join(raw_cats),
            )


@define
class Al2rcvCategoryApiFile(Base):
    """Emit an empty ``api.py`` per category (placeholder for future wiring).

    Attributes:
        template: Jinja template path (e.g. ``al2rcv/category_api.py.j2``).
        extra: Extra context merged into every render.
    """

    template: str = field()
    extra: Dict[str, Any] = field(factory=dict)

    def generate(self, out_path: str, **kwargs: Any) -> None:
        """Write one ``api.py`` per distinct category path."""

        env = kwargs.pop("env")
        base = {**self.extra, **kwargs}

        # Group resources by their full category path for one stub ``api.py``.
        by_cat: Dict[Tuple[str, ...], List[Any]] = defaultdict(list)
        for resource in kwargs["resources"]:
            res = cast("ExResource", resource)
            cats = tuple(res.categories or ())

            if not cats:
                continue
            by_cat[cats].append(res)

        # Stable order so diffs are reproducible across runs.
        for cats in sorted(by_cat.keys(), key=lambda c: c):
            dest = os.path.join(out_path, *cats)
            self.create_file(
                env,
                dest,
                "api.py",
                self.template,
                **base,
            )


def generate_rcv_path_scaffolds_from_alchemy(
    d_set: Any,
    out_path: str,
    env: Environment,
    *,
    get_db_import: str,
    rcv_import_root: str = "resi_fapi.routes.al2rcv_generated",
) -> None:
    """Write RCV path scaffolds via :class:`~exdrf_gen.fs_support.TopDir`.

    Args:
        d_set: ``ExDataset`` populated by
            ``exdrf_al.loader.dataset_from_sqlalchemy``.
        out_path: Directory to write Python modules into (created if missing).
            Root ``__init__.py`` imports ``api``; root ``api.py`` is a scaffold.
            Per-resource files live at
            ``out / *categories / {res_snake}_rcv_paths.py``; uncategorized
            resources write to ``out``. Each non-root category directory gets
            ``__init__.py`` and an empty ``api.py``.
        env: Shared Jinja environment (``context.obj[\"jinja_env\"]``).
        get_db_import: ``dotted.module:callable`` for the FastAPI DB dependency
            in root ``api.py`` (imported as ``get_db``), same as **`al2r`**.
        rcv_import_root: Dotted package where generated RCV modules live
            (embedded in root ``api.py`` for ``resolve_rcv_plan``).
    """

    # Avoid picking up templates from other exdrf_gen plugins in the same env.
    _restrict_loader_to_al2rcv_templates(env)

    # Values are forwarded into ``root_api.py.j2`` for the FastAPI DB session.
    al2rcv_get_db_module, al2rcv_get_db_attr = parse_get_db_import(
        get_db_import.strip(),
    )

    # Children run in order: category dirs first, then per-resource files, etc.
    generator = TopDir(
        comp=[
            Al2rcvCategoryInitFile(template="al2rcv/category_init.py.j2"),
            Al2rcvResourcePathFile(template="al2rcv/resource_rcv_paths.py.j2"),
            Al2rcvCategoryApiFile(template="al2rcv/category_api.py.j2"),
            File("__init__.py", "al2rcv/package_init.py.j2"),
            File("api.py", "al2rcv/root_api.py.j2"),
        ],
    )

    # ``TopDir`` fans out ``resources`` / ``categ_map`` from ``d_set``.
    generator.generate(
        dset=d_set,
        env=env,
        out_path=out_path,
        m_name=__name__,
        source_module=__name__,
        al2rcv_get_db_module=al2rcv_get_db_module,
        al2rcv_get_db_attr=al2rcv_get_db_attr,
        al2rcv_import_root=rcv_import_root.strip(),
    )
