from typing import TYPE_CHECKING, ClassVar, List, Type

from pydantic import BaseModel

if TYPE_CHECKING:
    from exdrf_pd.visitor import ExModelVisitor


class ExModel(BaseModel):
    """A Pydantic BaseModel that automatically registers its subclasses."""

    _registry: ClassVar[List[Type["ExModel"]]] = []

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        ExModel._registry.append(cls)

    @classmethod
    def get_subclasses(cls):
        """Return all registered subclasses."""
        return cls._registry

    @classmethod
    def visit(cls, visitor: "ExModelVisitor"):
        """Visit all the models derived from this class."""
        for model in cls._registry:
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
            visitor.visit_model(
                model, model.__name__, categories  # type: ignore
            )

            # Then visit all fields of the model.
            for field_name, field_info in model.model_fields.items():
                visitor.visit_field(
                    model, field_name, field_info  # type: ignore
                )
