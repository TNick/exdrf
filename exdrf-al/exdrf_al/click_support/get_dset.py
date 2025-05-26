import click
from exdrf.dataset import ExDataset
from exdrf.py_support import get_symbol_from_path

from exdrf_al.loader import dataset_from_sqlalchemy


class GetDataset(click.ParamType):
    """A custom Click parameter type for loading a dataset from a base.

    The user enters a module.name:base string, and this class loads the base
    class and creates an ExDataset from it.
    """

    name = "base_dset"

    def convert(self, value, param, ctx):
        try:
            base = get_symbol_from_path(value)
            d_set = ExDataset()
            return dataset_from_sqlalchemy(d_set, base)  # type: ignore
        except Exception as e:
            self.fail(f"Could not load dataset '{value}': {e}", param, ctx)
