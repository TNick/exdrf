from unittest.mock import MagicMock

from exdrf_dev.db.models import get_dev_engine, get_populated_dev_engine
from PyQt5.QtWidgets import QWidget
from pytest import fixture
from sqlalchemy.orm import (
    sessionmaker,
)

from exdrf_qt.context import QtContext
from exdrf_qt.worker import Relay


@fixture
def engine():
    """Fixture to provide a SQLAlchemy engine for the dev database."""
    engine = get_dev_engine()
    yield engine
    engine.dispose()


@fixture
def populated_engine(engine):
    """Fixture to provide a populated SQLAlchemy engine for the dev database."""
    return get_populated_dev_engine(engine)


@fixture
def session(engine):
    """Fixture to provide a SQLAlchemy session for the dev database."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    with SessionLocal() as session:
        yield session


@fixture
def context(populated_engine, session):
    """Fixture to provide a context for the dev database."""
    return QtContext(
        c_string="sqlite:///:memory:",
        engine=populated_engine,
        s_stack=[session],
        top_widget=MagicMock(spec=QWidget),
        work_relay=MagicMock(spec=Relay),
    )
