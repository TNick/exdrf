import logging

logger = logging.getLogger(__name__)


def top_level_handler(func):
    """A decorator that makes a function a top-level handler.

    This decorator wraps methods to provide consistent error handling
    and user feedback for top-level UI event handlers. It catches
    exceptions, logs them, and shows user-friendly error messages.

    Args:
        func: The function to wrap with error handling.

    Returns:
        Wrapped function with error handling.
    """

    def show_error(self, e: Exception):
        self.ctx.show_error(
            message=self.t(
                "resi.qt.handler-error.message",
                "An error occurred while executing the "
                "function {func}: {error}",
                func=func.__name__,
                error=str(e),
            ),
            title=self.t(
                "resi.qt.handler-error.title",
                "Error",
            ),
        )

    def wrapper(self, *args, **kwargs):
        """Wrapper function that provides error handling.

        Args:
            self: The instance the method is called on.
            *args: Positional arguments passed to the method.
            **kwargs: Keyword arguments passed to the method.

        Returns:
            Result of the original function, or None if an error occurred.
        """
        xep = None
        try:
            return func(self, *args, **kwargs)
        except TypeError as e:
            xep = e
            if "takes 1 positional argument but 2 were given" in str(e):
                try:
                    return func(self)
                except Exception as e:
                    xep = e
                    logger.error(
                        "An error occurred while executing the function: %s",
                        func.__name__,
                        exc_info=True,
                    )

            else:
                logger.error(
                    "An error occurred while executing the function: %s",
                    func.__name__,
                    exc_info=True,
                )

        except Exception as e:
            xep = e
            logger.error(
                "An error occurred while executing the function: %s",
                func.__name__,
                exc_info=True,
            )
        show_error(self, xep)
        return None

    return wrapper
