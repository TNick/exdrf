"""Tests for :mod:`exdrf_al.persist`."""

from __future__ import annotations

import pytest
from sqlalchemy import ForeignKey, Integer, String, create_engine
from sqlalchemy.orm import Mapped, Session, mapped_column

from exdrf_al.persist import (
    RowNotFound,
    apply_payload_attrs,
    fetch_one_strict,
    persist_row_as_ex_cm,
    sync_m2m_list_replace,
    sync_o2m_fk_list_replace,
)


@pytest.fixture
def m2m_pack(LocalBase):
    """In-memory SQLite with parent, child, and association tables."""

    class Parent(LocalBase):
        __tablename__ = "parents_persist"

        id: Mapped[int] = mapped_column(Integer, primary_key=True)
        name: Mapped[str] = mapped_column(String(20), default="")

    class Child(LocalBase):
        __tablename__ = "children_persist"

        id: Mapped[int] = mapped_column(Integer, primary_key=True)

    class ParentChild(LocalBase):
        __tablename__ = "parent_children_persist"

        parent_id: Mapped[int] = mapped_column(
            Integer,
            ForeignKey("parents_persist.id"),
            primary_key=True,
        )
        child_id: Mapped[int] = mapped_column(
            Integer,
            ForeignKey("children_persist.id"),
            primary_key=True,
        )
        extra: Mapped[str | None] = mapped_column(String(5), nullable=True)

    eng = create_engine("sqlite:///:memory:")
    LocalBase.metadata.create_all(eng)
    yield eng, Parent, Child, ParentChild


@pytest.fixture
def o2m_pack(LocalBase):
    """Parent and child with FK on the child."""

    class P(LocalBase):
        __tablename__ = "p_o2m_persist"

        id: Mapped[int] = mapped_column(Integer, primary_key=True)

    class C(LocalBase):
        __tablename__ = "c_o2m_persist"

        id: Mapped[int] = mapped_column(Integer, primary_key=True)
        p_id: Mapped[int | None] = mapped_column(
            Integer,
            ForeignKey("p_o2m_persist.id"),
            nullable=True,
        )

    eng = create_engine("sqlite:///:memory:")
    LocalBase.metadata.create_all(eng)
    yield eng, P, C


def test_fetch_one_strict_raises(m2m_pack):
    """Missing row raises :class:`RowNotFound`."""

    eng, Parent, _, _ = m2m_pack
    with Session(eng) as db:
        with pytest.raises(RowNotFound):
            fetch_one_strict(db, Parent, ("id", 999))


def test_sync_m2m_list_replace_roundtrip(m2m_pack):
    """M2M replace clears and inserts rows including dict extras."""

    eng, Parent, Child, PC = m2m_pack
    with Session(eng) as db:
        p = Parent(id=1, name="a")
        db.add_all([p, Child(id=10), Child(id=11)])
        db.commit()
        sync_m2m_list_replace(
            db,
            PC,
            ("parent_id",),
            "child_id",
            p,
            ("id",),
            [10, {"child_id": 11, "extra": "x"}],
        )
        db.commit()
        rows = db.query(PC).order_by(PC.child_id).all()
        assert len(rows) == 2
        assert rows[1].extra == "x"


def test_sync_o2m_fk_list_replace(o2m_pack):
    """O2M replace detaches then re-attaches children by id."""

    eng, P, C = o2m_pack
    with Session(eng) as db:
        db.add_all([P(id=1), C(id=100, p_id=1), C(id=200, p_id=None)])
        db.commit()
        p = db.get(P, 1)
        sync_o2m_fk_list_replace(db, C, "p_id", "id", p, ("id",), [200])
        db.commit()
        c100 = db.get(C, 100)
        c200 = db.get(C, 200)
        assert c100.p_id is None
        assert c200.p_id == 1


def test_persist_row_as_ex_cm_sets_ex(m2m_pack):
    """Context manager assigns ``ex`` after the ``with`` body."""

    eng, Parent, _, _ = m2m_pack

    class PEx:
        @classmethod
        def model_validate(cls, row, from_attributes=False):
            return ("ok", row.id)

    with Session(eng) as db:
        row = Parent(id=5, name="n")
        with persist_row_as_ex_cm(db, row, PEx, add=True) as h:
            assert h.row.id == 5
        assert h.ex == ("ok", 5)


def test_apply_payload_attrs_class_and_instance(m2m_pack):
    """``apply_payload_attrs`` supports class and instance forms."""

    eng, Parent, _, _ = m2m_pack
    row = apply_payload_attrs(Parent, {"id": 3, "name": "z"}, "id", "name")
    assert row.id == 3
    assert row.name == "z"
    apply_payload_attrs(row, {"name": "q"}, "name")
    assert row.name == "q"
