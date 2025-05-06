import os
from typing import TYPE_CHECKING

import click
from exdrf_al.click_support import GetDataset
from exdrf_gen.cli_base import cli
from exdrf_gen.plugin_support import install_plugin

if TYPE_CHECKING:
    from exdrf.dataset import ExDataset

install_plugin(
    template_paths=[
        os.path.join(os.path.dirname(__file__), "templates"),
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
def generate_pd_from_alchemy(
    d_set: "ExDataset",
    out_path: str,
):
    """Generate pd data from SqlAlchemy models.

    Arguments:
        db_base: The base class for the SQLAlchemy models as a module.name:path.
        out_path: The output path for the generated files.
    """
    click.echo("Generating pd project from exdrf project...")
