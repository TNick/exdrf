from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext


class QtUseContext:
    """Utility methods for classes that have a context."""

    ctx: "QtContext"

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
