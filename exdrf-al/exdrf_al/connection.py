from contextlib import contextmanager
from typing import List, Optional

from attrs import define, field
from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session

dialects_with_schema = {"postgresql", "oracle", "mssql"}


@define
class DbConn:
    """Holds information about the connection to a database.

    Attributes:
        c_string: The connection string to the database.
        engine: The engine used to connect to the database.
        s_stack: A stack of sessions.
        cache: A cache for values that are unlikely to change.
    """

    c_string: str
    schema: str = "public"
    engine: Optional[Engine] = None
    s_stack: List[Session] = field(factory=list)
    cache: dict = field(factory=dict)

    def connect(self) -> Engine:
        """Connect to the database."""
        if self.engine:
            return self.engine
        self.engine = create_engine(self.c_string)
        dialect_name = self.engine.dialect.name
        supports_schema = dialect_name in dialects_with_schema
        if supports_schema:
            self._set_search_path()
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

    def new_session(self):
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

        # Indicate that a session is being prepared.
        self.s_stack.append(None)  # type: ignore

        assert self.engine is not None, "Engine not set"
        if self.schema and self.engine.dialect.name in dialects_with_schema:
            # s.execute(text("SHOW search_path;"))
            s.execute(text("SELECT 1"))

        self.s_stack[-1] = s
        return s

    @contextmanager
    def session(self, auto_commit=False):
        """Creates a new session which it then closes after use.

        The session is added to the internal stack on creation and removed on
        closing. If auto_commit is True, the session is committed after use.

        If the inner code raises an exception, the session is rolled back.
        """
        session = self.new_session()
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
            self.s_stack.pop()

    @contextmanager
    def same_session(self, auto_commit=False):
        """Uses the existing session.

        If no session exists, a new one is created and then closed after use.
        If auto_commit is True, the session is committed after use.

        If the session is not new auto_commit has no effect.

        If the inner code raises an exception, the session is rolled back.
        """
        if self.s_stack:
            is_new = False
            session = self.s_stack[-1]
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

    def bootstrap(self):
        """Prepare the database for use."""
