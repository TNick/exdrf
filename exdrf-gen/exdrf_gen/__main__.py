"""Run the ``exdrf-gen`` CLI (plugins + Click group)."""

from exdrf_gen.cli_base import cli
from exdrf_gen.plugin_support import load_plugins


def main() -> None:
    """Entry point for ``python -m exdrf_gen`` and the ``exdrf-gen`` script.

    Loads all ``exdrf.plugins`` entry points named ``exdrf_gen``, then runs the
    Click CLI group.
    """
    load_plugins()
    cli()


if __name__ == "__main__":
    main()
