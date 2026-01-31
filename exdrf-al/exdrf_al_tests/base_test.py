from unittest import mock

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from exdrf_al.visitor import DbVisitor


def test_all_models_returns_registered_model_classes(LocalBase):
    """
    Tests that all_models yields the class_ attribute of each mapper
    in the Base registry's mappers collection.
    """

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

    result = set(x.__tablename__ for x in LocalBase.all_models())

    assert result == set(["mock_a", "mock_b"])


def test_all_models_empty_registry(LocalBase):
    """
    Tests that all_models yields nothing when the registry has no mappers.
    """
    # Act: Call the all_models class method and collect results
    result = list(LocalBase.all_models())

    # Assert: Check if the result is an empty list
    assert result == []


def test_visit_empty(LocalBase):
    """Tests that visit methods do not get called when there are no models."""
    visitor = mock.MagicMock(spec=DbVisitor)
    LocalBase.visit(visitor)

    assert len(visitor.categ_map) == 0
    assert visitor.visit_model.call_count == 0
    assert visitor.visit_column.call_count == 0
    assert visitor.visit_hybrid.call_count == 0
    assert visitor.visit_relation.call_count == 0


def test_visit_with_models(LocalBase):
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

        a_id: Mapped[int] = mapped_column(
            Integer,
            ForeignKey("mock_a.id"),
            doc="Foreign key to mock_a.",
        )

        a = relationship(
            "MockModelA",
            foreign_keys=[a_id],
            doc="Relationship to mock_a.",
        )

    visitor = mock.MagicMock(spec=DbVisitor)
    visitor.category = mock.MagicMock(return_value=["c1", "c2"])
    visitor.categ_map = {}
    LocalBase.visit(visitor)

    assert len(visitor.categ_map) == 1
    assert len(visitor.categ_map["c1"]) == 1
    assert len(visitor.categ_map["c1"]["c2"]) == 2
    assert visitor.visit_model.call_count == 2
    assert visitor.visit_column.call_count == 3
    assert visitor.visit_hybrid.call_count == 0
    assert visitor.visit_relation.call_count == 1


def test_visit_calls_visit_hybrid_for_hybrid_properties(LocalBase):
    """Tests that visit_hybrid is called for each hybrid property on a model."""

    class MockModelWithHybrid(LocalBase):
        __tablename__ = "mock_hybrid"
        id: Mapped[int] = mapped_column(
            Integer, primary_key=True, doc="Primary key."
        )
        x: Mapped[int] = mapped_column(Integer, doc="Column x.")
        y: Mapped[int] = mapped_column(Integer, doc="Column y.")

        @hybrid_property
        def total(self) -> int:
            return self.x + self.y

        @total.expression
        def total(cls):
            return cls.x + cls.y

    visitor = mock.MagicMock(spec=DbVisitor)
    visitor.category = mock.MagicMock(return_value=[])
    visitor.categ_map = {}
    LocalBase.visit(visitor)

    assert visitor.visit_hybrid.call_count == 1
    visitor.visit_hybrid.assert_called_once_with(
        MockModelWithHybrid, "total", mock.ANY
    )
    call_args = visitor.visit_hybrid.call_args[0]
    assert call_args[2].extension_type is not None
