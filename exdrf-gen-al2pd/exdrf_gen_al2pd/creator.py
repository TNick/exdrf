"""Generate Pydantic schema modules from SQLAlchemy-backed ``ExDataset``."""

from __future__ import annotations

import os
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Dict, List, Tuple, cast

from attrs import define, field
from exdrf_gen.fs_support import Base, File, TopDir, resource_to_args
from jinja2 import Environment

from exdrf_gen_al2pd.pydantic_emit import build_al2pd_template_kwargs

# ``ExResource`` is only needed for static typing of ``cast`` in generators.
if TYPE_CHECKING:
    from exdrf.resource import ExResource


def _restrict_loader_to_al2pd_templates(env: Environment) -> None:
    """Limit Jinja search paths to this package's templates.

    Attributes:
        env: Jinja environment.
    """

    # Narrow the shared loader to this package so template names resolve only
    # against ``al2pd_templates`` (same pattern as other exdrf-gen plugins).
    loader = getattr(env, "loader", None)
    if loader is None:
        return
    paths = list(getattr(loader, "paths", []))
    filtered = [p for p in paths if str(p).endswith("al2pd_templates")]
    setattr(loader, "paths", filtered)


@define
class Al2pdSchemaResFile(Base):
    """Emit one plural-named schema module per resource under category path.

    Output layout matches :meth:`~exdrf.resource.ExResource.ensure_path`:
    ``out / *resource.categories / {res_p_snake}.py``.

    Attributes:
        template: Jinja template path (e.g. ``al2pd/interface.py.j2``).
        extra: Extra context merged into every render.
    """

    template: str = field()
    extra: Dict[str, Any] = field(factory=dict)

    def generate(self, out_path: str, **kwargs: Any) -> None:
        """Write each resource's schema file."""

        env = kwargs.pop("env")
        source_module = kwargs.get("source_module", __name__)
        base = {**self.extra, **kwargs}

        # One plural-named ``.py`` per resource under its category path.
        for resource in kwargs["resources"]:
            res = cast("ExResource", resource)

            # Jinja context: partition kwargs, resource aliases, al2pd extras,
            # emitting module for template source comments.
            pd_kwargs = build_al2pd_template_kwargs(res)
            r_args = resource_to_args(res)
            args = {
                **base,
                **r_args,
                **pd_kwargs,
                "model_name": res.name,
                "m_name": source_module,
            }

            # Write ``{res_p_snake}.py`` next to sibling modules in the category
            # tree (empty categories → output root).
            dest = os.path.join(out_path, *res.categories)
            self.create_file(
                env,
                dest,
                "{res_p_snake}.py",
                self.template,
                **args,
            )


@define
class Al2pdCategoryInitFile(Base):
    """Emit ``__init__.py`` in each leaf category dir that holds schema modules.

    Matches the former ``_ensure_package_inits`` rule: only directories where a
    resource places a ``*.py`` module (non-empty ``categories``), not the output
    root (root ``__init__`` comes from :class:`~exdrf_gen.fs_support.File`).

    Attributes:
        template: Jinja template path (e.g. ``al2pd/category_init.py.j2``).
        extra: Extra context merged into every render.
    """

    template: str = field()
    extra: Dict[str, Any] = field(factory=dict)

    def generate(self, out_path: str, **kwargs: Any) -> None:
        """Write one package init per distinct resource category path."""

        env = kwargs.pop("env")
        base = {**self.extra, **kwargs}

        # Emit ``__init__.py`` for each leaf category dir that contains schema
        # modules (aligned with :class:`Al2pdSchemaResFile`); skip flat output
        # because the root package already has a dedicated :class:`File` init.
        for resource in kwargs["resources"]:
            res = cast("ExResource", resource)
            raw_cats = res.categories or []
            if not raw_cats:
                continue

            dest = os.path.join(out_path, *raw_cats)
            self.create_file(
                env,
                dest,
                "__init__.py",
                self.template,
                **base,
            )


@define
class Al2pdCategoryApiFile(Base):
    """Emit ``api.py`` in each non-root category dir that holds schema modules.

    Imports use one dot (e.g. ``from .widgets import ...``) so category dirs
    under the output root (e.g. ``resi_models/generated/l18``) expose a local
    aggregate alongside the root ``api.py``.

    Attributes:
        template: Jinja template path (e.g. ``al2pd/category_api.py.j2``).
        extra: Extra context merged into every render.
    """

    template: str = field()
    extra: Dict[str, Any] = field(factory=dict)

    def generate(self, out_path: str, **kwargs: Any) -> None:
        """Write one ``api.py`` per distinct category path."""

        env = kwargs.pop("env")
        source_module = kwargs.get("source_module", __name__)
        base = {**self.extra, **kwargs}

        # Group models by the directory where their plural module lives.
        by_cat: Dict[Tuple[str, ...], List[dict]] = defaultdict(list)
        for resource in kwargs["resources"]:
            res = cast("ExResource", resource)
            cats = tuple(res.categories or [])
            if not cats:
                continue
            pd_kw = build_al2pd_template_kwargs(res)
            by_cat[cats].append(
                {
                    "model_name": res.name,
                    "module_local": res.snake_case_name_plural,
                    "generate_edit": pd_kw["al2pd_generate_edit"],
                }
            )

        for cats in sorted(by_cat.keys(), key=lambda c: c):
            entries = sorted(
                by_cat[cats],
                key=lambda e: e["model_name"],
            )
            dest = os.path.join(out_path, *cats)
            self.create_file(
                env,
                dest,
                "api.py",
                self.template,
                **base,
                al2pd_category_api_entries=entries,
                m_name=source_module,
            )


def generate_pydantic_from_alchemy(
    context: Any,
    d_set: Any,
    out_path: str,
) -> None:
    """Write schema tree via :class:`~exdrf_gen.fs_support.TopDir`.

    Args:
        context: Click context with ``jinja_env`` on ``context.obj``.
        d_set: ``ExDataset`` from ``GetDataset()``.
        out_path: Output directory (created if missing).
    """

    # Click wires a shared Jinja env; restrict it before any template lookup.
    env = context.obj["jinja_env"]
    _restrict_loader_to_al2pd_templates(env)

    # Rows for ``api.py``: dotted import path and whether Edit is generated.
    api_entries: List[dict] = []
    for model in d_set.resources:
        kw = build_al2pd_template_kwargs(model)

        # Dotted path matches package layout: categories + plural snake module.
        module_dots = ".".join(
            [*getattr(model, "categories", ()), model.snake_case_name_plural]
        )
        api_entries.append(
            {
                "model_name": model.name,
                "module_dots": module_dots,
                "generate_edit": kw["al2pd_generate_edit"],
            }
        )

    # Root package, root + per-category ``api.py``, schemas, category inits.
    generator = TopDir(
        comp=[
            File("__init__.py", "al2pd/root_init.py.j2"),
            File("api.py", "al2pd/api.py.j2"),
            Al2pdSchemaResFile(template="al2pd/interface.py.j2"),
            Al2pdCategoryApiFile(template="al2pd/category_api.py.j2"),
            Al2pdCategoryInitFile(template="al2pd/category_init.py.j2"),
        ],
    )

    # Pass dataset and api metadata into every TopDir child via kwargs.
    generator.generate(
        dset=d_set,
        env=env,
        out_path=out_path,
        source_module=__name__,
        al2pd_api_entries=api_entries,
    )
