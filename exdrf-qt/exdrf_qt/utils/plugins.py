import logging
import uuid
from typing import TYPE_CHECKING, Callable, Optional

if TYPE_CHECKING:
    from pluggy._hooks import _F

logger = logging.getLogger(__name__)


def func_plugin(
    _func: Optional["_F"] = None,
    *,
    plugin_name: Optional[str] = None,
    specname: Optional[str] = None,
) -> Callable:
    """A plugin that has a single spec.

    This can be used as a decorator with or without arguments:
    - `@func_plugin`
    - `@func_plugin(specname='some_spec')`

    Example:
        @func_plugin
        def context_created(context: "QtContext") -> None:
            pass

    This will register a plugin with the name
    "exdrf_qt.plugins.func_plugin.context_created....."
    and the specname "context_created".

    Args:
        _func: The function to decorate. This is automatically passed when
            the decorator is used without arguments.
        plugin_name: The name of the plugin. If not provided, a unique
            name is generated. The name must be unique across all plugins.
        specname: The name of the hook specification. If not provided, the
            name of the decorated function is used.

    Returns:
        The decorator or the decorated function.
    """
    from exdrf_qt.plugins import exdrf_qt_pm, hook_impl

    def decorator(func: "_F") -> "_F":
        _plugin_name = plugin_name
        if _plugin_name is None:
            _plugin_name = (
                func.__module__ + "." + func.__name__ + "." + uuid.uuid4().hex
            )

        _specname = specname
        if _specname is None:
            _specname = func.__name__

        class FuncPluginImpl:
            @hook_impl(specname=_specname)
            def bridge(*args, **kwargs):
                return func(*args, **kwargs)

        exdrf_qt_pm.register(FuncPluginImpl, name=_plugin_name)
        return func

    if _func is None:
        return decorator
    else:
        return decorator(_func)


def safe_hook_call(hook_caller, *args, **kwargs):
    """We use this function to ensure that an exception in a hook does not
        cause the entire function to crash.

        Example:
            from exdrf_qt.context import QtContext
            from exdrf_qt.plugins import exdrf_qt_pm
    from exdrf_qt.utils.plugins import safe_hook_call

            context = QtContext()
            results, errors = safe_hook_call(
                exdrf_qt_pm.hook.context_created,
                context=context
            )
    """
    result_map = {}
    error_map = {}

    for impl in hook_caller.get_hookimpls():
        try:
            result_map[impl.plugin_name] = impl.function(*args, **kwargs)
        except Exception as e:
            error_map[impl.plugin_name] = e
            logger.error(
                "Error in in %s hook of the %s plugin",
                hook_caller.name,
                impl.plugin_name,
                exc_info=True,
            )

    return result_map, error_map
