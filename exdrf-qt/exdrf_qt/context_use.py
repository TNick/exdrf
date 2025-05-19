from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QWidget  # noqa: F401

    from exdrf_qt.context import QtContext


class QtUseContext:
    """Utility methods for classes that have a context."""

    ctx: "QtContext"

    def create_window(self, w: "QWidget", title: str):
        """Creates a stand-alone window.

        The default implementation assumes that the `top_widget` has a
        `mdi_area` attribute that is an instance of `QMdiArea`. Reimplement
        this method if you want to use a different type of window manager.

        Args:
            w: The widget to create a window for.
            title: The title of the window.
        """
        return self.ctx.create_window(w, title)

    def close_window(self, w: "QWidget"):
        """Closes a stand-alone window.

        The default implementation assumes that the `top_widget` has a
        `mdi_area` attribute that is an instance of `QMdiArea`. Reimplement
        this method if you want to use a different type of window manager.

        Args:
            w: The widget to close.
        """
        return self.ctx.close_window(w)

    def get_icon(self, name: str):
        """Returns an icon from the resource file.

        Args:
            name: The name of the icon.

        Returns:
            The icon.
        """
        return self.ctx.get_icon(name)

    def t(self, text: str, d: str, **kwargs: Any) -> str:
        """Translates a string using the context.

        Args:
            text: The string to translate.
            d: The default string if translation is not found.
            **kwargs: Additional arguments for translation string.

        Returns:
            The translated string.
        """
        return self.ctx.t(text, d, **kwargs)

    def show_error(
        self,
        message: str,
        title: str = "Error",
    ):
        """Shows an error message.

        Args:
            title: The title of the error message.
            message: The error message.
        """
        self.ctx.show_error(message, title)
