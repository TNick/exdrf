import inspect
import logging
from functools import wraps

logger = logging.getLogger(__name__)


def top_level_handler(*d_args, **d_kwargs):
    """Wrap a function/method to behave like a safe top-level UI handler.

    The wrapper catches exceptions, logs them, and shows a user-friendly
    error message (via `ctx.show_error`) when a context is available.

    This decorator supports:

    - `@top_level_handler` (same as `@top_level_handler()`)
    - `@top_level_handler()`
    - `@top_level_handler(ctx=self.ctx)`

    Args:
        ctx: Optional Qt context used for translation and error display.
            If not provided it is assumed that the function is a method and
            the self has a ctx attribute.

    Returns:
        A decorator, or a wrapped function when used as `@top_level_handler`.
    """

    # Parse decorator arguments.
    ctx = d_kwargs.pop("ctx", None)
    if d_kwargs:
        raise TypeError(
            "top_level_handler() got unexpected keyword arguments: %s"
            % ", ".join(sorted(d_kwargs.keys()))
        )

    def show_error(w_ctx, e: Exception, wrapped_func):
        w_ctx.show_error(
            message=w_ctx.t(
                "exdrf.qt.handler-error.message",
                "An error occurred while executing the "
                "function {func}: {error}",
                func=wrapped_func.__name__,
                error=str(e),
            ),
            title=w_ctx.t(
                "exdrf.qt.handler-error.title",
                "Error",
            ),
        )

    def decorate(wrapped_func):
        sig = inspect.signature(wrapped_func)

        def _call_with_qt_arg_fallback(*args, **kwargs):
            """Call handler, trimming extra Qt args when the signature rejects.

            Qt often calls callbacks with extra positional args, e.g. a QAction
            may call slots as `callback(checked: bool)`. Many handlers in this
            codebase are defined as `def on_x(self): ...` and should ignore that
            extra argument.
            """

            # First try the normal call path.
            try:
                return wrapped_func(*args, **kwargs)
            except TypeError:
                # Only attempt a fallback when it's a call signature mismatch.
                # If bind() succeeds, the TypeError came from inside the
                # wrapped handler and must not be swallowed.
                try:
                    sig.bind(*args, **kwargs)
                except TypeError:
                    pass
                else:
                    raise

            # Try trimming positional args until the signature binds.
            trimmed_args = args
            while trimmed_args:
                trimmed_args = trimmed_args[:-1]
                try:
                    sig.bind(*trimmed_args, **kwargs)
                except TypeError:
                    continue
                return wrapped_func(*trimmed_args, **kwargs)

            # Try dropping kwargs as a last resort (rare in Qt, but safe).
            try:
                sig.bind(*args)
            except TypeError:
                pass
            else:
                return wrapped_func(*args)

            raise

        @wraps(wrapped_func)
        def wrapper(*args, **kwargs):
            """Execute handler and surface errors to the UI when possible."""

            # Execute handler.
            try:
                return _call_with_qt_arg_fallback(*args, **kwargs)
            except Exception as e:
                logger.error(
                    "An error occurred while executing the function: %s",
                    wrapped_func.__name__,
                    exc_info=True,
                )

                # Resolve context: explicit `ctx` wins; otherwise infer from
                # the first argument (typical `self` in bound methods).
                resolved_ctx = ctx
                if resolved_ctx is None and args:
                    resolved_ctx = getattr(args[0], "ctx", None)

                if resolved_ctx is not None:
                    show_error(resolved_ctx, e, wrapped_func)
                else:
                    logger.warning(
                        "No context available for error handling: %s",
                        wrapped_func.__name__,
                    )

                return None

        return wrapper

    # Used as `@top_level_handler`.
    if len(d_args) == 1 and callable(d_args[0]) and ctx is None:
        return decorate(d_args[0])

    # Used as `@top_level_handler(...)`.
    if d_args:
        raise TypeError(
            "top_level_handler() should be used as @top_level_handler or "
            "@top_level_handler(...)"
        )

    return decorate
