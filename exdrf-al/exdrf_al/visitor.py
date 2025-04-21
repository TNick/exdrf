import textwrap
from typing import TYPE_CHECKING, Any, List, Optional, Type

from attrs import define, field
from exdrf.resource import ResExtraInfo
from sqlalchemy.orm.relationships import RelationshipProperty
from sqlalchemy.sql.elements import KeyedColumnElement

if TYPE_CHECKING:
    from exdrf_al.base import Base


@define
class DbVisitor:
    """A visitor that can be used to traverse a hierarchy of models.

    Attributes:
        categ_map: Tree of categories, where each key is a category and the
            value is a dictionary of subcategories or models. The tree is built
            by the `visit` method, so it is not complete until that method
            has been called.
    """

    categ_map: dict = field(factory=dict, init=False)

    def visit_model(self, model: Type["Base"]) -> None:
        """Visit a model.

        Args:
            model: The model that is being visited.
        """

    def visit_column(
        self, model: Type["Base"], column: "KeyedColumnElement[Any]"
    ) -> None:
        """Visit a column.

        Args:
            model: The model that contains the column.
            column: The column that is being visited.
        """

    def visit_relation(
        self, model: Type["Base"], relation: "RelationshipProperty"
    ) -> None:
        """Visit a relationship.

        Args:
            model: The model that contains the relationship.
            relationship: The relationship that is being visited.
        """

    @staticmethod
    def get_docs(thing):
        """Retrieve the documentation of a pydantic model or field."""
        doc = textwrap.dedent(thing.__doc__).strip() if thing.__doc__ else ""

        doc_lines = doc.split("\n")
        for i in range(1, len(doc_lines)):
            if doc_lines[i].startswith("    "):
                doc_lines[i] = doc_lines[i][4:]
        return doc, doc_lines

    @staticmethod
    def category(model) -> List[str]:
        """Get the category of a module.

        This is the list of nested python modules in which the pydantic model
        is defined, except for the first (package name) and the last (the file
        name, which is usually the same as the resource name).
        """
        return model.__module__.split(".")[1:-1]

    @classmethod
    def run(cls, base: Optional[Type["Base"]] = None, *args, **kwargs):
        """Run the visitor."""
        from exdrf_al.base import Base as DbBase

        v = cls(*args, **kwargs)
        if base is None:
            base = DbBase
        base.visit(v)  # type: ignore
        return v

    @staticmethod
    def extra_info(model: Type["Base"]) -> "ResExtraInfo":
        """Get the extra information for a model.

        Args:
            model: The model that is being visited.

        Returns:
            The extra information for the model.
        """
        return ResExtraInfo.model_validate(model.__table_args__.get("info", {}))
