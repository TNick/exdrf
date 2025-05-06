import click
from exdrf.py_support import get_symbol_from_path


class ModuleSymbol(click.ParamType):
    name = "mod_symbol"

    def convert(self, value, param, ctx):
        try:
            return get_symbol_from_path(value)
        except Exception as e:
            self.fail(f"Could not load symbol '{value}': {e}", param, ctx)
