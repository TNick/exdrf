"""exdrf-gen plugin: RTK Query TypeScript from OpenAPI."""

from __future__ import annotations

import os

import click
from click import Context
from exdrf_gen.cli_base import cli
from exdrf_gen.plugin_support import install_plugin

from exdrf_gen_openapi2rtk.creator import run_openapi2rtk

install_plugin(
    template_paths=[
        os.path.join(os.path.dirname(__file__), "openapi2rtk_templates"),
    ],
)


@cli.command(name="openapi2rtk")
@click.argument(
    "routes_out_dir",
    type=click.Path(file_okay=False, dir_okay=True),
    envvar="EXDRF_OPENAPI2RTK_ROUTES_DIR",
)
@click.option(
    "--openapi-file",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to a local openapi.json (or use --openapi-url).",
)
@click.option(
    "--openapi-url",
    default=None,
    help="HTTP(S) URL to fetch OpenAPI JSON (requires --cache-file).",
)
@click.option(
    "--cache-file",
    type=click.Path(dir_okay=False),
    default=None,
    help="Cache path for --openapi-url downloads and ETag metadata.",
)
@click.option(
    "--types-import",
    default="@resi/models",
    show_default=True,
    help="Module path passed to emitted ``from '…'`` type imports.",
)
@click.option(
    "--base-api-profile",
    type=click.Choice(["minimal", "fr_one"]),
    default="minimal",
    show_default=True,
    help=(
        "``fr_one`` matches fr-one auth/baseUrl wiring; "
        "``minimal`` is generic."
    ),
)
@click.pass_context
def openapi2rtk(
    context: Context,
    routes_out_dir: str,
    openapi_file: str | None,
    openapi_url: str | None,
    cache_file: str | None,
    types_import: str,
    base_api_profile: str,
) -> None:
    """Generate RTK Query route modules from an OpenAPI document."""

    run_openapi2rtk(
        context,
        routes_out_dir,
        openapi_file,
        openapi_url,
        cache_file,
        types_import,
        base_api_profile,
    )
