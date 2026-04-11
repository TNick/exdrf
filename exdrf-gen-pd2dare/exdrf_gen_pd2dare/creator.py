"""Build DARE TypeScript files from imported Pydantic Ex models."""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, cast

import click
from attrs import define, field
from exdrf.dataset import ExDataset
from exdrf.resource import ExResource
from exdrf_gen.fs_support import Base, TopDir, resource_to_args
from exdrf_pd.loader import dataset_from_pydantic
from exdrf_pd.model_import import load_pydantic_modules_from_env
from exdrf_ts import type_to_field_class
from jinja2 import Environment


def _restrict_loader_to_pd2dare_templates(env: Environment) -> None:
    """Limit Jinja search paths to this package's templates."""

    loader = getattr(env, "loader", None)
    if loader is None:
        return
    paths = list(getattr(loader, "paths", []))
    filtered = [p for p in paths if str(p).endswith("pd2dare_templates")]
    setattr(loader, "paths", filtered)


@define
class Pd2dareExInterfaceFile(Base):
    """Emit one ``*.ts`` DARE interface per resource whose name ends with ``Ex``.

    Output layout matches :meth:`~exdrf.resource.ExResource.ensure_path` with
    the default file name: ``out / *categories / {ModelName}.ts``.

    Attributes:
        template: Jinja template path (e.g. ``pd2dare/interface.ts.j2``).
        extra: Extra context merged into every render.
    """

    template: str = field()
    extra: Dict[str, Any] = field(factory=dict)

    def generate(self, out_path: str, **kwargs: Any) -> None:
        """Write each ``*Ex`` model's interface file."""

        env = kwargs.pop("env")
        m_name = kwargs.get("m_name", __name__)
        base = {**self.extra, **kwargs}
        for resource in kwargs["resources"]:
            resource = cast("ExResource", resource)
            if not resource.name.endswith("Ex"):
                continue
            f_classes = sorted(
                {
                    type_to_field_class[f.type_name]
                    for f in resource.fields
                    if f.type_name in type_to_field_class
                }
            )
            rargs = resource_to_args(resource)
            args = {
                **base,
                **rargs,
                "model_name": resource.name,
                "doc_lines": resource.doc_lines,
                "f_classes": f_classes,
                "m_name": m_name,
            }
            dest = os.path.join(out_path, *getattr(resource, "categories", ()))
            self.create_file(
                env,
                dest,
                "{model_name}.ts",
                self.template,
                **args,
            )


@define
class Pd2dareCategoryIndex(Base):
    """Recursively write ``index.ts`` under each category (category map tree).

    Mirrors the layout produced by the former ``write_dataset_category_index``
    helper.

    Attributes:
        template: Jinja template path (e.g. ``pd2dare/index.ts.j2``).
        file_name: Index file name (for example ``index.ts``).
        extra: Extra context merged into every render.
    """

    template: str = field()
    file_name: str = field(default="index.ts")
    extra: Dict[str, Any] = field(factory=dict)

    def generate(self, out_path: str, **kwargs: Any) -> None:
        """Walk ``categ_map`` and emit an index at each level."""

        env = kwargs.pop("env")
        dset = kwargs.get("dset")
        base = {**self.extra, **kwargs}
        categ_map: dict = base.get("categ_map", {})
        merge = {k: v for k, v in base.items() if k != "categ_map"}

        def do_map(the_map: dict, parts: List[str]) -> List[Any]:
            model_list: List[Any] = []
            for map_name in sorted(the_map.keys()):
                value = the_map[map_name]
                if isinstance(value, dict):
                    model_list.extend(
                        [
                            (m, map_name)
                            for m in do_map(value, parts + [map_name])
                        ],
                    )
                else:
                    model_list.append((map_name, map_name))

            dir_path = os.path.join(out_path, *parts)
            self.create_file(
                env,
                dir_path,
                self.file_name,
                self.template,
                model_list=model_list,
                crt_path=parts,
                dataset=dset,
                level=len(parts),
                **merge,
            )

            return [m[0] for m in model_list]

        do_map(categ_map, [])


@define
class Pd2dareDatasetFile(Base):
    """Write the root ``dataset.ts`` aggregating all ``*Ex`` models.

    Attributes:
        template: Jinja template path (e.g. ``pd2dare/dataset.ts.j2``).
        extra: Extra context merged into every render.
    """

    template: str = field()
    extra: Dict[str, Any] = field(factory=dict)

    def generate(self, out_path: str, **kwargs: Any) -> None:
        """Render ``dataset.ts`` with the filtered model list."""

        env = kwargs.pop("env")
        m_name = kwargs.get("m_name", __name__)
        dare_models = [m for m in kwargs["resources"] if m.name.endswith("Ex")]
        mapping = {
            **self.extra,
            **kwargs,
            "models": dare_models,
            "m_name": m_name,
        }
        self.create_file(
            env,
            out_path,
            "dataset.ts",
            self.template,
            **mapping,
        )


def generate_pd2dare(context: click.Context, path: str) -> None:
    """Load Ex models and write DARE TS under ``path`` via :class:`TopDir`.

    Args:
        context: Click context with ``jinja_env``.
        path: Output directory (must exist or be creatable by callers).
    """

    env = context.obj["jinja_env"]
    _restrict_loader_to_pd2dare_templates(env)

    load_pydantic_modules_from_env()
    d_set = ExDataset(res_class=ExResource)
    dataset_from_pydantic(d_set)

    m_name = __name__

    generator = TopDir(
        comp=[
            Pd2dareExInterfaceFile(template="pd2dare/interface.ts.j2"),
            Pd2dareCategoryIndex(template="pd2dare/index.ts.j2"),
            Pd2dareDatasetFile(template="pd2dare/dataset.ts.j2"),
        ],
    )
    generator.generate(
        dset=d_set,
        env=env,
        out_path=path,
        m_name=m_name,
    )


def run_pd2dare(context: click.Context, path: str | None) -> None:
    """Validate arguments and run generation.

    Args:
        context: Click context.
        path: Output directory or None when missing from argv and env.
    """

    if not path:
        click.echo(
            "You must specify a path to the output directory as an argument or "
            "set the EXDRF_PD2DARE_PATH environment variable.",
            err=True,
        )
        sys.exit(1)

    generate_pd2dare(context, path)
