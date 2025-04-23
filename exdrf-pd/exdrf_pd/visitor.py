import textwrap
from typing import List, Type

from attrs import define, field
from pydantic.fields import FieldInfo

from exdrf_pd.base import ExModel


@define
class ExModelVisitor:
    """A visitor that can be used to traverse a hierarchy of ExModels.

    Attributes:
        categ_map: Tree of categories, where each key is a category and the
            value is a dictionary of subcategories or models. The tree is built
            by the `visit` method, so it is not complete until that method
            has been called.
    """

    categ_map: dict = field(factory=dict)

    def visit_model(
        self, model: Type["ExModel"], name: str, categories: List[str]
    ):
        """Visit a model."""

    def visit_field(
        self, model: Type["ExModel"], name: str, field: "FieldInfo"
    ):
        """Visit a field."""

    @staticmethod
    def category(model) -> List[str]:
        """Get the category of a module.

        This is the list of nested python modules in which the pydantic model
        is defined, except for the first (package name) and the last (the file
        name, which is usually the same as the resource name).
        """
        return model.__module__.split(".")[1:-1]

    @staticmethod
    def get_docs(thing):
        """Retrieve the documentation of a pydantic model or field."""
        doc = textwrap.dedent(thing.__doc__).strip() if thing.__doc__ else ""

        doc_lines = doc.split("\n")
        for i in range(1, len(doc_lines)):
            if doc_lines[i].startswith("    "):
                doc_lines[i] = doc_lines[i][4:]
        return doc, doc_lines

    @classmethod
    def run(cls, *args, **kwargs):
        """Run the visitor."""
        v = cls(*args, **kwargs)
        ExModel.visit(v)  # type: ignore[call-arg]
        return v
