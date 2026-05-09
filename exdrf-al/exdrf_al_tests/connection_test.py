from unittest.mock import MagicMock

import pytest
from sqlalchemy import Engine, Integer, inspect
from sqlalchemy.orm import Mapped, mapped_column

from exdrf_al.connection import DbConn


class TestDbConnConnect:
    def test_no_engine(self):
        db_conn = DbConn(c_string="sqlite:///:memory:")
        assert db_conn.engine is None
        engine = db_conn.connect()
        assert isinstance(engine, Engine)
        assert db_conn.engine is engine

    def test_with_engine(self):
        engine = MagicMock(spec=Engine)
        db_conn = DbConn(c_string="sqlite:///:memory:", engine=engine)
        assert db_conn.engine is not None
        engine = db_conn.connect()
        assert db_conn.engine is engine


class TestDbConnClose:
    def test_no_engine(
        self,
    ):
        db_conn = DbConn(c_string="sqlite:///:memory:")
        db_conn.close()
        assert db_conn.engine is None

    def test_with_engine(self):
        engine = MagicMock(spec=Engine)
        db_conn = DbConn(c_string="sqlite:///:memory:", engine=engine)
        db_conn.close()
        assert db_conn.engine is None

    def test_close_all_sessions(self):
        engine = MagicMock(spec=Engine)
        db_conn = DbConn(c_string="sqlite:///:memory:", engine=engine)
        db_conn.s_stack.append(MagicMock())
        db_conn.s_stack.append(MagicMock())
        db_conn.close_all_sessions()
        assert len(db_conn.s_stack) == 0


class TestDbConnNewSession:
    def test_new_session(self):
        engine = MagicMock(spec=Engine)
        db_conn = DbConn(c_string="sqlite:///:memory:", engine=engine)
        session = db_conn.new_session()
        assert len(db_conn.s_stack) == 1
        assert session in db_conn.s_stack


class TestDbConnSession:
    def test_success_no_commit(self):
        db_conn = DbConn(c_string="sqlite:///:memory:")
        assert len(db_conn.s_stack) == 0
        with db_conn.session(auto_commit=False) as session:
            assert len(db_conn.s_stack) == 1
            assert db_conn.s_stack[-1] is session

        assert len(db_conn.s_stack) == 0

    def test_success_auto_commit(self, LocalBase2Tables):
        db_conn, MockModelA, MockModelB = LocalBase2Tables
        assert len(db_conn.s_stack) == 0

        with db_conn.session(auto_commit=True) as session:
            mock_a = MockModelA()
            mock_b = MockModelB()
            session.add(mock_a)
            session.add(mock_b)
            assert len(db_conn.s_stack) == 1
            assert db_conn.s_stack[-1] is session

        assert len(session.dirty) == 0
        assert len(session.new) == 0
        assert len(db_conn.s_stack) == 0

    def test_exception(self, LocalBase2Tables):
        db_conn, MockModelA, MockModelB = LocalBase2Tables
        assert len(db_conn.s_stack) == 0

        session = None
        with pytest.raises(Exception):
            with db_conn.session(auto_commit=True) as session:
                mock_a = MockModelA()
                mock_b = MockModelB()
                session.add(mock_a)
                session.add(mock_b)
                assert len(db_conn.s_stack) == 1
                assert db_conn.s_stack[-1] is session
                raise Exception("Test exception")

        assert session
        assert len(session.dirty) == 0
        assert len(session.new) == 0
        assert len(db_conn.s_stack) == 0


class TestDbConnSameSession:
    def test_existing_session_no_commit(self):
        db_conn = DbConn(c_string="sqlite:///:memory:")
        session_mock = MagicMock()
        db_conn.s_stack.append(session_mock)

        with db_conn.same_session(auto_commit=False) as session:
            assert session is session_mock
            assert len(db_conn.s_stack) == 1

        session_mock.rollback.assert_not_called()
        session_mock.commit.assert_not_called()
        session_mock.close.assert_not_called()
        assert len(db_conn.s_stack) == 1

    def test_existing_session_with_commit(self):
        db_conn = DbConn(c_string="sqlite:///:memory:")
        session_mock = MagicMock()
        db_conn.s_stack.append(session_mock)

        with db_conn.same_session(auto_commit=True) as session:
            assert session is session_mock
            assert len(db_conn.s_stack) == 1

        session_mock.rollback.assert_not_called()
        session_mock.commit.assert_not_called()
        session_mock.close.assert_not_called()
        assert len(db_conn.s_stack) == 1

    def test_new_session_no_commit(self):
        db_conn = DbConn(c_string="sqlite:///:memory:")
        assert len(db_conn.s_stack) == 0

        with db_conn.same_session(auto_commit=False) as session:
            assert len(db_conn.s_stack) == 1
            assert db_conn.s_stack[-1] is session

        assert len(db_conn.s_stack) == 0

    def test_new_session_with_commit(self, LocalBase2Tables):
        db_conn, MockModelA, MockModelB = LocalBase2Tables
        assert len(db_conn.s_stack) == 0

        with db_conn.same_session(auto_commit=True) as session:
            mock_a = MockModelA()
            mock_b = MockModelB()
            session.add(mock_a)
            session.add(mock_b)
            assert len(db_conn.s_stack) == 1
            assert db_conn.s_stack[-1] is session

        assert len(session.dirty) == 0
        assert len(session.new) == 0
        assert len(db_conn.s_stack) == 0

    def test_exception(self, LocalBase2Tables):
        db_conn, MockModelA, MockModelB = LocalBase2Tables
        assert len(db_conn.s_stack) == 0

        session = None
        with pytest.raises(Exception):
            with db_conn.same_session(auto_commit=True) as session:
                mock_a = MockModelA()
                mock_b = MockModelB()
                session.add(mock_a)
                session.add(mock_b)
                assert len(db_conn.s_stack) == 1
                assert db_conn.s_stack[-1] is session
                raise Exception("Test exception")

        assert session
        assert len(session.dirty) == 0
        assert len(session.new) == 0
        assert len(db_conn.s_stack) == 0


class TestDbConnCreateAllTables:
    def test_create_all_tables(self, LocalBase):
        db_conn = DbConn(c_string="sqlite:///:memory:")
        assert len(db_conn.s_stack) == 0

        class MockModelA(LocalBase):
            __tablename__ = "mock_a"
            id: Mapped[int] = mapped_column(
                Integer, primary_key=True, doc="Primary key of mock_a."
            )

        class MockModelB(LocalBase):
            __tablename__ = "mock_b"
            id: Mapped[int] = mapped_column(
                Integer, primary_key=True, doc="Primary key of mock_b."
            )

        db_conn.create_all_tables(LocalBase)

        inspector = inspect(db_conn.engine)
        assert inspector
        tables = inspector.get_table_names()
        assert "mock_a" in tables
        assert "mock_b" in tables
        assert len(db_conn.s_stack) == 0
