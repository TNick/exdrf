from importlib import import_module


def get_symbol_from_path(path: str) -> object:
    """Given a `module.path:name`, load the python module and return the symbol.

    Args:
        path: The module path and symbol name, e.g. `module.path:name`.
    """

    if ":" in path:
        module_path, symbol = path.split(":")
    else:
        module_path = path
        symbol = None

    module = import_module(module_path)

    if symbol is not None:
        return getattr(module, symbol)
    return module
