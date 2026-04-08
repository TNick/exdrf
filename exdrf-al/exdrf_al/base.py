from typing import TYPE_CHECKING, Any, Generator, Type

from sqlalchemy.ext.hybrid import HybridExtensionType
from sqlalchemy.inspection import inspect as sa_inspect
from sqlalchemy.orm import DeclarativeBase

if TYPE_CHECKING:
    from exdrf_al.visitor import DbVisitor


class _RegistryVisitorMixin:
    """SQLAlchemy registry helpers shared by application and isolated bases.

    Attributes:
        None
    """

    @classmethod
    def all_models(cls) -> Generator[Type[Any], None, None]:
        """Yield each ORM class registered on this declarative base."""
        for mapper in cls.registry.mappers:
            yield mapper.class_

    @classmethod
    def visit(
        cls,
        visitor: "DbVisitor",
    ) -> None:
        """Walk all mapped models and forward them to ``visitor``."""
        for model in cls.all_models():

            # Compute the categories (list of modules) of the model.
            categories = visitor.category(model)

            # Create the tree of categories.
            m_map = visitor.categ_map
            for c in categories:
                # Get the category at this level.
                c_map = m_map.get(c, None)
                if c_map is None:
                    # It does not exist, so create it.
                    c_map = m_map[c] = {}

                # Move to the next level.
                m_map = c_map

            # The leaf receives the model.
            m_map[model.__name__] = model

            # Visit the model itself.
            visitor.visit_model(model)  # type: ignore

            # Then visit all fields of the model.
            for column in model.__table__.columns:
                visitor.visit_column(model, column)  # type: ignore

            # Then visit all hybrid properties of the model.
            for name, desc in sa_inspect(model).all_orm_descriptors.items():
                ext_ty = getattr(desc, "extension_type", None)
                if ext_ty is not None:
                    if ext_ty == HybridExtensionType.HYBRID_PROPERTY:
                        visitor.visit_hybrid(model, name, desc)  # type: ignore

            # Then visit all relationships of the model.
            for rel in model.__mapper__.relationships:
                visitor.visit_relation(model, rel)  # type: ignore


class Base(_RegistryVisitorMixin, DeclarativeBase):
    """Application-wide declarative base for Ex-DRF SQLAlchemy models.

    Attributes:
        None
    """


def isolated_declarative_base() -> type[DeclarativeBase]:
    """Return a new declarative base with its own metadata/registry.

    Used by tests that define temporary models and must not see classes
    registered on the process-wide :class:`Base` (for example models from
    optional dev packages imported earlier in the suite).

    Returns:
        A fresh declarative base class with :meth:`all_models` and
        :meth:`visit` identical to :class:`Base`.
    """

    class _IsolatedBase(_RegistryVisitorMixin, DeclarativeBase):
        pass

    return _IsolatedBase
