"""exdrf-gen plugin: Pydantic Ex models to DARE TypeScript."""

from __future__ import annotations

import os

import click
from exdrf_gen.cli_base import cli
from exdrf_gen.plugin_support import install_plugin
from exdrf_ts import py_type_to_ts

from exdrf_gen_pd2dare.creator import run_pd2dare


def _f_title(field: object) -> str:
    """Jinja helper: map a field title annotation to TypeScript text."""

    title = getattr(field, "title", "")
    return py_type_to_ts(title)


install_plugin(
    template_paths=[
        os.path.join(os.path.dirname(__file__), "pd2dare_templates"),
    ],
    extra_globals={
        "f_title": _f_title,
    },
)


@cli.command(name="pd2dare")
@click.argument(
    "path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    required=False,
    envvar="EXDRF_PD2DARE_PATH",
)
@click.pass_context
def pd2dare(context: click.Context, path: str | None) -> None:
    """Generate TypeScript DARE resources and dataset from Pydantic Ex models."""

    run_pd2dare(context, path)
