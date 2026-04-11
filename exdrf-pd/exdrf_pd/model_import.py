"""Import Pydantic model modules so ``dataset_from_pydantic`` can see subclasses."""

from __future__ import annotations

import importlib
import os
from typing import Iterable, List

_ENV_PRIMARY = "EXDRF_PYDANTIC_MODELS_MODULES"
_ENV_LEGACY = "RESI_PYDANTIC_MODELS_MODULES"


def load_pydantic_modules(modules: Iterable[str]) -> List[str]:
    """Import each module name so ExModel subclasses register before dataset build.

    Args:
        modules: Iterable of dotted Python module names.

    Returns:
        Module names that were imported successfully, in order.
    """

    imported: List[str] = []

    # Import each module in order to register its Pydantic subclasses.
    for module_name in modules:
        clean_name = module_name.strip()
        if not clean_name:
            continue
        importlib.import_module(clean_name)
        imported.append(clean_name)

    return imported


def load_pydantic_modules_from_env() -> List[str]:
    """Import modules listed in ``EXDRF_PYDANTIC_MODELS_MODULES``.

    If ``EXDRF_PYDANTIC_MODELS_MODULES`` is unset or empty, falls back to
    ``RESI_PYDANTIC_MODELS_MODULES`` for backward compatibility (deprecated).

    Returns:
        The list of imported module names.
    """

    raw_value = os.getenv(_ENV_PRIMARY, "")
    if not raw_value.strip():
        raw_value = os.getenv(_ENV_LEGACY, "")
    modules = raw_value.split(",") if raw_value else []
    return load_pydantic_modules(modules)
