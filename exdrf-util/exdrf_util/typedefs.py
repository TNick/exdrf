from typing import TYPE_CHECKING, Any, ContextManager, Protocol

if TYPE_CHECKING:
    from sqlalchemy.orm.session import Session


class HasTranslate(Protocol):
    """Protocol for contexts that provide translation.

    t(key: str, d: str, **kwargs: Any) -> str
    """

    def t(self, key: str, d: str, **kwargs: Any) -> str:
        """Translate a string using the context.

        Args:
            key: The translation key.
            d: The default string if translation is not found.
            **kwargs: Additional arguments for translation string.

        Returns:
            The translated string.
        """
        ...


class HasDbSession(Protocol):
    """Protocol for contexts that provide a database session."""

    def session(
        self, auto_commit: bool = False, add_to_stack: bool = True
    ) -> ContextManager["Session"]:
        """Creates a new session which it then closed after use.

        The session is added to the internal stack on creation and removed on
        closing. If auto_commit is True, the session is committed after use.

        If the inner code raises an exception, the session is rolled back.
        """
        ...

    def same_session(
        self, auto_commit: bool = False
    ) -> ContextManager["Session"]:
        """Uses the existing session.

        If no session exists, a new one is created and then closed after use.
        If auto_commit is True, the session is committed after use.

        If the session is not new auto_commit has no effect.

        If the inner code raises an exception, the session is rolled back.
        """
        ...


class HasBasicContext(HasTranslate, HasDbSession, Protocol):
    """Protocol for contexts that provide both translation and database session."""

    ...
