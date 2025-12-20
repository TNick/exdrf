import os
from typing import TYPE_CHECKING

import click
from exdrf_al.click_support import GetDataset
from exdrf_gen.cli_base import cli
from exdrf_gen.plugin_support import install_plugin

from exdrf_gen_al2at.creator import generate_attrs_from_alchemy

if TYPE_CHECKING:
    from exdrf.dataset import ExDataset

install_plugin(
    template_paths=[
        os.path.join(os.path.dirname(__file__), "al2at_templates"),
    ]
)


@cli.command(name="al2at")
@click.pass_context  # type: ignore
@click.argument(
    "d_set",
    metavar="DATASET",
    type=GetDataset(),
)
@click.argument(
    "out_path",
    metavar="OUT-PATH",
    type=click.Path(exists=False, file_okay=False, dir_okay=True),
    envvar="EXDRF_AL2AT_PATH",
)
@click.argument(
    "out_module",
    metavar="OUT-MODULE",
    type=str,
)
@click.argument(
    "db_module",
    metavar="DB-MODULE",
    type=str,
)
def at_from_alchemy(
    context: click.Context,
    d_set: "ExDataset",
    out_path: str,
    out_module: str,
    db_module: str,
):
    """Generate attrs models from SqlAlchemy models.

    Arguments:
        DATASET: The base class for the SQLAlchemy models as a module.name:path.
        OUT-PATH: The directory path to write the generated files to.
        OUT-MODULE: The module name to use for the generated files.
        DB-MODULE: The module name for the SQLAlchemy models.
    """
    click.echo("Generating attrs from exdrf...")
    generate_attrs_from_alchemy(
        d_set=d_set,
        out_path=out_path,
        out_module=out_module,
        db_module=db_module,
        env=context.obj["jinja_env"],
    )
