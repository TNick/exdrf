"""exdrf-gen plugin: Pydantic schemas from SQLAlchemy-backed ``ExDataset``."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import click
from click import Context
from exdrf_al.click_support import GetDataset
from exdrf_gen.cli_base import cli
from exdrf_gen.plugin_support import install_plugin

from exdrf_gen_al2pd.creator import generate_pydantic_from_alchemy

if TYPE_CHECKING:
    from exdrf.dataset import ExDataset

install_plugin(
    template_paths=[
        os.path.join(os.path.dirname(__file__), "al2pd_templates"),
    ]
)


@cli.command(name="al2pd")
@click.argument(
    "d_set",
    metavar="DATASET",
    type=GetDataset(),
)
@click.argument(
    "out_path",
    metavar="OUT-PATH",
    type=click.Path(exists=False, file_okay=False, dir_okay=True),
    envvar="EXDRF_AL2PD_PATH",
    required=False,
)
@click.pass_context
def generate_pd_from_alchemy(
    context: Context,
    d_set: "ExDataset",
    out_path: str,
) -> None:
    """Generate Pydantic models (Xxx, XxxEx, XxxCreate, XxxEdit) per resource.

    Arguments:
        DATASET: ``module.path:DeclarativeBase`` for SQLAlchemy models.
        OUT-PATH: Output directory for generated ``*.py`` modules and ``api.py``.
    """

    if not out_path:
        raise click.UsageError(
            "OUT-PATH is required (or set EXDRF_AL2PD_PATH).",
        )
    click.echo("Generating Pydantic schemas from exdrf / SQLAlchemy...")
    generate_pydantic_from_alchemy(context, d_set, out_path)
