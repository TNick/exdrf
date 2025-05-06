import logging

import click
from dotenv import load_dotenv
from exdrf.utils import inflect_e

from exdrf_gen.__version__ import __version__
from exdrf_gen.jinja_support import jinja_env


def create_context_obj(debug: bool):
    """Sets up the logging and prepares the context for the CLI.

    Args:
        debug: If True, sets the logging level to DEBUG.
    """
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="[%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logging.debug("Debug mode is on")

    return {
        "jinja_env": jinja_env,
        "inflect": inflect_e,
    }


@click.group()
@click.option("--debug/--no-debug", default=False)
@click.version_option(__version__, prog_name="exdrf-gen")
@click.pass_context
def cli(context: click.Context, debug: bool):
    load_dotenv()
    context.obj = create_context_obj(debug)
