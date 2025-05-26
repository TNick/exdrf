import click
from exdrf.py_support import get_symbol_from_path


class GetBase(click.ParamType):
    """A custom Click parameter type for loading a Base for sqlalchemy models.

    The user enters a module.name:base string, and this class loads the base
    class and returns it.
    """

    name = "base"

    def convert(self, value, param, ctx):
        try:
            base = get_symbol_from_path(value)
            return base
        except Exception as e:
            self.fail(f"Could not load base '{value}': {e}", param, ctx)
