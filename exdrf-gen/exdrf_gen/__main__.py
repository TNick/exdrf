from exdrf_gen.cli_base import cli
from exdrf_gen.plugin_support import load_plugins

if __name__ == "__main__":
    load_plugins()
    cli()
