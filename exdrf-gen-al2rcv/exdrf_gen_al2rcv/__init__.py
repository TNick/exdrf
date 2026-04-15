"""exdrf-gen plugin: RCV path scaffolds from ``ExDataset``."""

from __future__ import annotations

import os

import click
from click import Context
from exdrf_al.click_support import GetDataset
from exdrf_gen.cli_base import cli
from exdrf_gen.plugin_support import install_plugin

from exdrf_gen_al2rcv.creator import generate_rcv_path_scaffolds_from_alchemy

install_plugin(
    template_paths=[
        os.path.join(os.path.dirname(__file__), "al2rcv_templates"),
    ],
)


@cli.command(name="al2rcv")
@click.argument(
    "d_set",
    metavar="DATASET",
    type=GetDataset(),
)
@click.argument(
    "out_path",
    metavar="OUT-PATH",
    type=click.Path(exists=False, file_okay=False, dir_okay=True),
    envvar="EXDRF_AL2RCV_PATH",
    required=False,
)
@click.option(
    "--get-db",
    "get_db_import",
    metavar="MODULE:CALLABLE",
    envvar="EXDRF_AL2RCV_GET_DB",
    default=None,
    help=(
        "FastAPI DB dependency as dotted.module:callable "
        "(emitted as ``from … import callable as get_db``). "
        "Example: ``resi_fapi.deps.al2r_db:get_db``."
    ),
)
@click.option(
    "--rcv-import-root",
    "rcv_import_root",
    metavar="DOTTED.PACKAGE",
    envvar="EXDRF_AL2RCV_IMPORT_ROOT",
    default="resi_fapi.routes.al2rcv_generated",
    show_default=True,
    help=(
        "Dotted package where generated ``*_rcv_paths`` modules live "
        "(embedded in root ``api.py`` for ``resolve_rcv_plan``)."
    ),
)
@click.pass_context
def al2rcv(
    context: Context,
    d_set: object,
    out_path: str,
    get_db_import: str | None,
    rcv_import_root: str,
) -> None:
    """Generate RCV path module scaffolds from SQLAlchemy models.

    Args:
        DATASET: ``module.path:DeclarativeBase`` for SQLAlchemy models.
        OUT-PATH: Directory for generated ``*_rcv_paths.py`` and ``api.py``.
        get_db_import: ``--get-db`` / ``EXDRF_AL2RCV_GET_DB`` for the session
            dependency (``module.path:fn``); required like **`al2r`** when
            emitting DB-backed routes.
        rcv_import_root: ``--rcv-import-root`` / ``EXDRF_AL2RCV_IMPORT_ROOT``
            for dynamic imports in generated ``api.py``.
    """

    if not out_path:
        raise click.UsageError(
            "OUT-PATH is required (or set EXDRF_AL2RCV_PATH).",
        )
    if not (get_db_import or "").strip():
        raise click.UsageError(
            "--get-db is required (or set EXDRF_AL2RCV_GET_DB), e.g. "
            "resi_fapi.deps.al2r_db:get_db.",
        )
    click.echo("Generating remote-controlled-view path scaffolds...")
    generate_rcv_path_scaffolds_from_alchemy(
        d_set=d_set,
        out_path=out_path,
        env=context.obj["jinja_env"],
        get_db_import=get_db_import,
        rcv_import_root=rcv_import_root,
    )
