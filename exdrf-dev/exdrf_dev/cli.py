import logging
import os
import subprocess

import click
from dotenv import load_dotenv

from exdrf_dev.__version__ import __version__


@click.group()
@click.option("--debug/--no-debug", default=False)
@click.version_option(__version__, prog_name="exdrf-dev")
def cli(debug: bool):
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="[%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logging.debug("Debug mode is on")
    os.environ["CURDIR"] = os.getcwd()

    load_dotenv(override=True)
    click.echo("=" * 80)
    _print_env("Environment variables after .env")
    click.echo("=" * 80)


def _print_env(title: str = "Environment variables"):
    click.echo(title)
    for key in sorted(os.environ.keys()):
        value = os.environ[key]
        if len(value) > 50:
            click.echo(f"{key}:")
            for part in value.split(";"):
                click.echo(f"  {part}")
        else:
            click.echo(f"{key}: {value}")


@cli.command()
def print_env():
    """Print the environment variables."""
    _print_env()


@cli.command()
@click.argument("args", nargs=-1)
def run(args):
    """Run the exdrf-dev application with provided arguments."""
    click.echo(f"Running exdrf-dev with arguments: {args}")
    try:
        final_args = []
        for a in args:
            if a.startswith("env:"):
                env_var = a[4:]
                env_value = os.environ.get(env_var)
                if env_value is None:
                    click.echo(
                        f"Env. variable '{env_var}' not found.", err=True
                    )
                    return
                a = env_value
            final_args.append(a)

        result = subprocess.run(
            final_args, check=True, text=True, capture_output=True, shell=True
        )
        click.echo(result.stdout)
        if result.stderr:
            click.echo(result.stderr, err=True)
    except subprocess.CalledProcessError as e:
        click.echo(f"Command failed with exit code {e.returncode}", err=True)
        click.echo(e.stderr, err=True)
    except FileNotFoundError:
        click.echo("Command not found", err=True)


if __name__ == "__main__":
    cli()
