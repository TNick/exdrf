import os
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

from attrs import define, field
from sqlalchemy import Engine, Select, create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session

from exdrf_al.db_ver.db_ver import DbVer

dialects_with_schema = {"postgresql", "oracle", "mssql"}


@define
class AutoCacheEntry:
    """An entry in the auto cache.

    If is_multi is False and is_scalar is False, the query is expected to
    return a single record.

    Attributes:
        value: The value of the cache entry.
        query: The query to retrieve the value if it's not in the cache.
        is_multi: True if the query returns multiple records.
        is_scalar: True if the query returns a single value.
        loaded: True if the query was executed and the value is in the cache.
    """

    value: Any
    selector: "Select"
    is_multi: bool
    is_scalar: bool
    loaded: bool


def react_on_c_string(instance, attribute, value):
    """React to the change of the c_string attribute."""
    old = getattr(instance, attribute.name, None)
    if value == old:
        return value
    instance.engine = None
    instance.s_stack = []
    instance.cache = {}
    instance.auto_cache = {}
    instance.db_version = None

    return value


@define
class DbConn:
    """Holds information about the connection to a database.

    Attributes:
        c_string: The connection string to the database.
        engine: The engine used to connect to the database.
        s_stack: A stack of sessions.
        cache: A general-purpose cache.
        auto_cache: A cache where the information about how to retrieve
            them is stored along with the value.
    """

    c_string: str = field(on_setattr=react_on_c_string)
    schema: str = "public"
    engine: Optional[Engine] = None
    s_stack: List[Session] = field(factory=list, repr=False)
    cache: dict = field(factory=dict, repr=False)
    auto_cache: Dict[str, AutoCacheEntry] = field(factory=dict, repr=False)
    db_version: Optional[str] = None
    auto_migrate: Optional[bool] = False

    def connect(self) -> Engine:
        """Connect to the database."""
        if self.engine:
            return self.engine
        self.engine = create_engine(self.c_string)
        dialect_name = self.engine.dialect.name
        supports_schema = dialect_name in dialects_with_schema
        if supports_schema:
            self._set_search_path()

        mgh = self.get_migration_handler()
        if self.auto_migrate:
            current_version = mgh.get_current_version()
            latest_version = mgh.get_latest_version()
            if current_version != latest_version:
                mgh.upgrade(target=latest_version or "heads")
        self.db_version = mgh.get_current_version()

        return self.engine

    def _set_search_path(self):
        @event.listens_for(self.engine, "connect", insert=True)
        def set_search_path(dbapi_connection, connection_record):
            # Only execute if either the session stack is empty
            # or the last session in the stack is not being prepared (because
            # if it is being prepared then the session executes this
            # exact command).
            if self.schema:
                existing_autocommit = dbapi_connection.autocommit
                dbapi_connection.autocommit = True
                cursor = dbapi_connection.cursor()
                assert self.engine is not None, "Engine not set"
                if self.engine.dialect.name == "mssql":
                    # For MSSQL, we need to set the schema in a different way
                    stm = f"USE {self.schema}"
                elif self.engine.dialect.name == "oracle":
                    # For Oracle, we need to set the schema in a different way
                    stm = f"ALTER SESSION SET CURRENT_SCHEMA = {self.schema}"
                else:
                    # For PostgreSQL
                    stm = f"SET SESSION search_path='{self.schema}'"
                cursor.execute(stm)
                cursor.close()
                dbapi_connection.autocommit = existing_autocommit

    def close(self):
        """Close the connection to the database."""
        self.close_all_sessions()
        if self.engine:
            self.engine.dispose()
            self.engine = None

    def close_all_sessions(self):
        """Close all sessions."""
        for s in self.s_stack:
            s.close()
        self.s_stack = []

    def new_session(self, add_to_stack: bool = True):
        """Create a new session."""
        self.connect()
        Session = sessionmaker(
            bind=self.engine,
            # Ensures that changes are not automatically committed.
            autocommit=False,
            # Allows automatic flush before a query execution.
            autoflush=True,
        )
        s = Session()

        if add_to_stack:
            # Indicate that a session is being prepared.
            self.s_stack.append(None)  # type: ignore

        assert self.engine is not None, "Engine not set"
        # if self.schema and self.engine.dialect.name in dialects_with_schema:
        #     # s.execute(text("SHOW search_path;"))
        #     s.execute(text("SELECT 1"))

        if add_to_stack:
            self.s_stack[-1] = s
        return s

    @contextmanager
    def session(self, auto_commit=False, add_to_stack: bool = True):
        """Creates a new session which it then closed after use.

        The session is added to the internal stack on creation and removed on
        closing. If auto_commit is True, the session is committed after use.

        If the inner code raises an exception, the session is rolled back.
        """
        session = self.new_session(add_to_stack=add_to_stack)
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        else:
            if session.is_active and auto_commit:
                session.commit()
        finally:
            session.close()
            if add_to_stack:
                self.s_stack.pop()

    @contextmanager
    def same_session(self, auto_commit=False):
        """Uses the existing session.

        If no session exists, a new one is created and then closed after use.
        If auto_commit is True, the session is committed after use.

        If the session is not new auto_commit has no effect.

        If the inner code raises an exception, the session is rolled back.
        """
        session = None
        while self.s_stack:
            session = self.s_stack[-1]
            if session is None:
                self.s_stack.pop()
            else:
                break
        if session:
            is_new = False
        else:
            is_new = True
            session = self.new_session()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        else:
            if session.is_active and is_new and auto_commit:
                session.commit()
        finally:
            if is_new:
                session.close()
                self.s_stack.pop()

    def create_all_tables(self, Base):
        """Creates all tables defined in the Base metadata.

        Args:
            Base: The declarative base class containing the table metadata.
        """
        engine = self.connect()
        Base.metadata.create_all(bind=engine)

    def bootstrap(self) -> bool:
        """Prepare the database for use."""
        return True

    def set_auto_cache_entry(
        self,
        key: str,
        selector: Optional["Select"] = None,
        is_scalar: bool = True,
        is_multi: bool = False,
        loaded: bool = False,
        value: Optional[Any] = None,
    ) -> None:
        """Saves a cache record inside this context.

        You can set the value directly or provide a query to retrieve the value
        from the database. If you provide a query, you must also provide the
        is_scalar and is_multi parameters to indicate how to retrieve the value
        from the query.

        Args:
            key: The key to use for the cache.
            query: The query to use to retrieve the value if it's not in the
                cache.
            is_scalar: True if the query returns a single value.
            is_multi: True if the query returns multiple records.
            loaded: True if the query was executed and the value is in the
                cache.
            value: The value to store in the cache.
        """
        if selector is None:
            self.cache[key] = value
        else:
            self.auto_cache[key] = AutoCacheEntry(
                value=value,
                selector=selector,
                is_scalar=is_scalar,
                is_multi=is_multi,
                loaded=loaded,
            )

    def get_cached_value(self, key: str) -> Any:
        """Retrieves a value from either cache or database.

        Args:
            key: The key to use for the cache.

        Raises:
            KeyError: If the information about how to retrieve this value was
                not previously provided through set_auto_cache_entry().

        Returns:
            The value of the cache entry.
        """
        # Fast retrieval.
        entry = self.auto_cache.get(key, None)
        if entry is not None:
            if entry.loaded:
                return entry.value
        else:
            regular_cache = self.cache.get(key, None)
            if regular_cache is not None:
                return regular_cache

            if len(self.auto_cache) == 0:
                raise KeyError(
                    f"There are no cache records. Did you forget to call "
                    f"setup_cache()? Key {key} was the one to trigger the "
                    f"exception."
                )
            else:
                raise KeyError(
                    f'No cache record for "{key}"; allowed keys '
                    f'are: {",".join(list(self.auto_cache.keys()))}'
                )

        # Retrieve value from the database.
        with self.same_session() as session:
            if entry.is_scalar:
                value = session.scalar(entry.selector)
            elif entry.is_multi:
                value = session.scalars(entry.selector)
            else:
                value = session.scalar(entry.selector)

        # Save value in cache.
        entry.value = value
        entry.loaded = True

        # Return value.
        return value

    def get_migration_handler(self, mig_loc: Optional[str] = None) -> "DbVer":
        assert self.engine is not None, "Engine is not connected."
        final_mig_loc = mig_loc or os.environ.get(
            "EXDRF_DB_MIGRATIONS_DIR", None
        )
        if not final_mig_loc:
            raise ValueError("Migration location is not set.")

        # SQLite (and similar dialects) do not support schemas. Passing a schema
        # causes Alembic to look for e.g. "public.alembic_version".
        schema = (
            self.schema
            if self.engine.dialect.name in dialects_with_schema
            else None
        )
        return DbVer(
            engine=self.engine,
            migrations=final_mig_loc,
            schema=schema,
        )
