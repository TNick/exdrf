from typing import TYPE_CHECKING, List, Type, Union

from attrs import define, field

from exdrf.resource import ExResource

if TYPE_CHECKING:
    from exdrf.visitor import ExVisitor


@define
class ExDataset:
    """A set of resources.

    The resources are stored in a list to ensure a consistent enumeration
    order. To access a resource in the dataset, you can use the `dataset[key]`
    syntax, where `key` can be either the index of the resource in the list
    of models or the name of the resource.

    Attributes:
        name: The name of the dataset.
        resources: A list of resources in the dataset.
        category_map: A tree of categories, where each key is a category and
            the value is a dictionary of subcategories or resources.
    """

    name: str = field(default="Dataset")
    resources: List["ExResource"] = field(factory=list, repr=False)
    category_map: dict = field(factory=dict, repr=False)
    res_class: Type["ExResource"] = field(
        default=ExResource, repr=False, kw_only=True
    )

    def __hash__(self):
        return hash(self.name)

    def __getitem__(self, key: Union[int, str]) -> "ExResource":
        # Attempt to use the key as an index first.
        if isinstance(key, int):
            return self.resources[key]

        # If the key is not an index, treat it as a name.
        for m in self.resources:
            if m.name == key:
                return m

        raise KeyError(
            f"No resource found for key: {key}; valid indices are "
            f"from 0 to {len(self.resources) - 1}. "
            f"Valid names are: {[m.name for m in self.resources]}"
        )

    def add_resource(self, resource: "ExResource") -> None:
        """Add a resource to the dataset.

        Args:
            resource: The resource to add.
        """
        if not isinstance(resource, self.res_class):
            raise TypeError(
                f"Expected resource of type {self.res_class}, "
                f"but got {type(resource)}."
            )
        self.resources.append(resource)

    def visit(self, visitor: "ExVisitor") -> bool:
        """Visit the dataset and its resources.

        Args:
            visitor: The visitor to use.

        Returns:
            bool: True if the visit should continue, False otherwise.
        """
        if not visitor.visit_dataset(self):  # type: ignore
            return False

        for resource in self.resources:
            if not resource.visit(visitor):
                return False

        return True
