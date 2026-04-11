"""exdrf-gen plugin: FastAPI routers from SQLAlchemy-backed ``ExDataset``."""

from __future__ import annotations

import os

import click
from click import Context
from exdrf_al.click_support import GetDataset
from exdrf_gen.cli_base import cli
from exdrf_gen.plugin_support import install_plugin

from exdrf_gen_al2r.creator import generate_fastapi_routes_from_alchemy


install_plugin(
    template_paths=[
        os.path.join(os.path.dirname(__file__), "al2r_templates"),
    ],
)


@cli.command(name="al2r")
@click.argument(
    "d_set",
    metavar="DATASET",
    type=GetDataset(),
)
@click.argument(
    "out_path",
    metavar="OUT-PATH",
    type=click.Path(exists=False, file_okay=False, dir_okay=True),
    envvar="EXDRF_AL2R_PATH",
    required=False,
)
@click.argument(
    "db_module",
    metavar="DB-MODULE",
    type=str,
)
@click.argument(
    "schemas_root",
    metavar="SCHEMAS-PKG",
    type=str,
    envvar="EXDRF_AL2R_SCHEMAS",
    required=False,
)
@click.pass_context
def al2r(
    context: Context,
    d_set: object,
    out_path: str,
    db_module: str,
    schemas_root: str,
) -> None:
    """Generate FastAPI APIRouter modules from SQLAlchemy models.

    Args:
        DATASET: ``module.path:DeclarativeBase`` for SQLAlchemy models.
        OUT-PATH: Directory for generated ``*_routes.py`` and ``__init__.py``.
        DB-MODULE: Import path where ORM classes are imported from
            (passed through to generated ``from ... import Model`` lines).
        SCHEMAS-PKG: Dotted import root for ``al2pd`` output (must match layout).
    """

    if not out_path:
        raise click.UsageError(
            "OUT-PATH is required (or set EXDRF_AL2R_PATH).",
        )
    if not schemas_root:
        raise click.UsageError(
            "SCHEMAS-PKG is required (or set EXDRF_AL2R_SCHEMAS).",
        )
    click.echo("Generating FastAPI route stubs from exdrf / SQLAlchemy...")
    generate_fastapi_routes_from_alchemy(
        d_set=d_set,
        out_path=out_path,
        db_module=db_module,
        schemas_root=schemas_root,
        env=context.obj["jinja_env"],
    )
