from collections import OrderedDict
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    Union,
    cast,
)

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
    category_map: dict = field(factory=OrderedDict, repr=False)
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
        resource.dataset = self  # type: ignore

        # Place the resource in the category map.
        crt = self.category_map
        for part in resource.categories:
            next_crt = crt.get(part)
            if next_crt is None:
                next_crt = OrderedDict()
                crt[part] = next_crt
            crt = next_crt
        crt[resource.name] = resource

    def visit(
        self,
        visitor: "ExVisitor",
        omit_fields: Optional[bool] = False,
        omit_categories: Optional[bool] = False,
    ) -> bool:
        """Visit the dataset and its resources.

        Args:
            visitor: The visitor to use.
            omit_fields: If True, resource fields will not be visited.
            omit_categories: If True, categories will not be visited.
                This means that the visitor will only visit the resources in
                the dataset, not the categories, making the process a bit more
                efficient.

        Returns:
            bool: True if the visit should continue, False otherwise.
        """
        if not visitor.visit_dataset(self):  # type: ignore
            return False

        if omit_categories:
            for res in self.resources:
                if not res.visit(visitor, omit_fields=omit_fields):
                    return False
            return True

        def do_category_map(crt_map: dict, level: int = 0) -> bool:
            for k, v in crt_map.items():
                if isinstance(v, dict):
                    visitor.visit_category(k, level, v)
                    do_category_map(v)
                else:
                    resource = cast("ExResource", v)
                    if not resource.visit(visitor, omit_fields=omit_fields):
                        return False
            return True

        return do_category_map(self.category_map)

    def zero_categories(self) -> List[Tuple[str, List["ExResource"]]]:
        """Get a list of top level categories and their resources."""
        result = []
        for ctg, ctg_data in self.category_map.items():
            models = []

            def do_data(crt_data: Any) -> None:
                if isinstance(crt_data, dict):
                    for subset in crt_data.values():
                        do_data(subset)
                else:
                    models.append(crt_data)

            do_data(ctg_data)
            result.append((ctg, models))
        return result

    def sorted_by_deps(self) -> List["ExResource"]:
        # Build a dependency map where key is the resource name and value is a
        # set of names of resources it depends on.
        deps: Dict[str, List["ExResource"]] = {}
        short_deps: Dict[str, List["ExResource"]] = {}
        name_to_resource: Dict[str, "ExResource"] = {}
        for resource in self.resources:
            deps[resource.name] = list(resource.get_dependencies())
            short_deps[resource.name] = list(
                resource.get_dependencies(fk_only=True)
            )
            name_to_resource[resource.name] = resource

        # Start with those that have no dependencies.
        result = OrderedDict(
            (name, name_to_resource[name])
            for name, deps in sorted(deps.items(), key=lambda x: x[0])
            if len(deps) == 0
        )

        def recursive(name: str, visited: List[str], fk_only: bool = False):
            """Examine the dependency chain of a resource."""
            if name in visited:
                print(
                    f"Circular dependency detected: {name} -> "
                    + " -> ".join(visited)
                )
                return

            if name in result:
                return

            if fk_only:
                my_deps = short_deps[name]
            else:
                my_deps = deps[name]
            for dep in my_deps:
                recursive(dep.name, visited + [name], fk_only=fk_only)

            # Add the resource to the sorted list.
            result[name] = name_to_resource[name]

        for name in sorted(short_deps.keys()):
            recursive(name, [], fk_only=True)

        if len(result) != len(deps):
            for name in sorted(deps.keys()):
                recursive(name, [], fk_only=False)

        return list(result.values())
