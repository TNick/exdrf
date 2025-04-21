from typing import TYPE_CHECKING, Generator, Type

from sqlalchemy.orm import DeclarativeBase

if TYPE_CHECKING:
    from exdrf_al.visitor import DbVisitor


class Base(DeclarativeBase):
    @classmethod
    def all_models(cls) -> Generator[Type["Base"], None, None]:
        for mapper in cls.registry.mappers:
            yield mapper.class_

    @classmethod
    def visit(
        cls,
        visitor: "DbVisitor",
    ) -> None:
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

            # Then visit all relationships of the model.
            for rel in model.__mapper__.relationships:
                visitor.visit_relation(model, rel)  # type: ignore
