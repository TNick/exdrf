import logging
import sys
from typing import Any, Dict, List, Optional, cast

from exdrf_gen.jinja_support import Loader, jinja_env

if sys.version_info < (3, 10):
    from importlib_metadata import entry_points
else:
    from importlib.metadata import entry_points

logger = logging.getLogger(__name__)


def load_plugins():
    """Scan for and load all exdrf-gen- plugins."""
    discovered_plugins = entry_points(group="exdrf.plugins")
    for plugin in discovered_plugins:
        if plugin.name == "exdrf_gen":
            try:
                plugin.load()
            except Exception as e:
                logger.error(f"Failed to load plugin {plugin.name}: {e}")


def install_plugin(
    template_paths: Optional[List[str]] = None,
    extra_tests: Optional[Dict[str, Any]] = None,
    extra_filters: Optional[Dict[str, Any]] = None,
    extra_globals: Optional[Dict[str, Any]] = None,
):
    """One stop function to install plugins."""
    if template_paths:
        loader = cast(Loader, jinja_env.loader)
        loader.paths.extend(template_paths)

    if extra_tests:
        for name, test in extra_tests.items():
            if name in jinja_env.tests:
                logger.warning(f"Test {name} already exists. Overwriting.")
            jinja_env.tests[name] = test

    if extra_globals:
        for name, value in extra_globals.items():
            if name in jinja_env.globals:
                logger.warning(f"Global {name} already exists. Overwriting.")
            jinja_env.globals[name] = value

    if extra_filters:
        for name, filter_func in extra_filters.items():
            if name in jinja_env.filters:
                logger.warning(f"Filter {name} already exists. Overwriting.")
            jinja_env.filters[name] = filter_func
