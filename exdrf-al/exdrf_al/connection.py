from contextlib import contextmanager
from typing import List, Optional

from attrs import define, field
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session


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
    engine: Optional[Engine] = None
    s_stack: List[Session] = field(factory=list)
    cache: dict = field(factory=dict)

    def connect(self) -> Engine:
        """Connect to the database."""
        if self.engine:
            return self.engine
        self.engine = create_engine(self.c_string)
        return self.engine

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
        self.s_stack.append(s)
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
