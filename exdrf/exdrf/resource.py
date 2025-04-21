from typing import TYPE_CHECKING, Any, List, Optional

from attrs import define, field
from pydantic import BaseModel

from exdrf.label_dsl import parse_expr
from exdrf.utils import doc_lines

if TYPE_CHECKING:
    from exdrf.dataset import ExDataset
    from exdrf.field import ExField
    from exdrf.label_dsl import ASTNode
    from exdrf.visitor import ExVisitor


@define
class ExResource:
    """The resource consists of a list of fields and is part of a dataset.

    You can retrieve a field using the `resource[key]` syntax, where key is
    either the name of the field or its index.

    Attributes:
    """

    name: str
    dataset: "ExDataset" = field(default=None, repr=False)
    fields: List["ExField"] = field(factory=list)
    categories: List[str] = field(factory=list)
    description: str = ""
    src: Any = field(default=None)
    label_ast: ASTNode = field(default=None)

    @property
    def doc_lines(self) -> List[str]:
        """Get the docstring of the field as a set of lines.

        Returns:
            The docstring of the field as a set of lines.
        """
        return doc_lines(self.description)

    def visit(
        self,
        visitor: "ExVisitor",
        omit_fields: Optional[bool] = False,
    ) -> bool:
        """Visit the resource and its fields.

        Args:
            visitor: The visitor to use.
            omit_fields: If True, resource fields will not be visited.

        Returns:
            bool: True if the visit should continue, False otherwise.
        """
        if not visitor.visit_resource(self):  # type: ignore
            return False

        if not omit_fields:
            for fld in self.fields:
                if not fld.visit(visitor):
                    return False

        return True


class ResExtraInfo(BaseModel):
    """The layout of the dictionary associated with resources in the model.

    Attributes:
        label: The string definition of the layer composition function using
            layer_dsl syntax.
    """

    label: Optional[str] = None

    def get_layer_ast(self) -> ASTNode:
        """Return the layer composition function using layer_dsl syntax."""
        if not self.label:
            return []
        return parse_expr(self.label)
