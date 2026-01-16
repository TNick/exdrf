import os
import re
from collections import OrderedDict as OrDict
from functools import cached_property
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Optional,
    OrderedDict,
    Set,
    Tuple,
    Union,
    cast,
)

from attrs import define, field
from pydantic import BaseModel, Field

from exdrf.constants import FIELD_TYPE_INTEGER
from exdrf.label_dsl import (
    generate_python_code,
    generate_typescript_code,
    get_used_fields,
    parse_expr,
)
from exdrf.utils import doc_lines, inflect_e

if TYPE_CHECKING:
    from exdrf.dataset import ExDataset
    from exdrf.field import ExField
    from exdrf.field_types.ref_base import RefBaseField
    from exdrf.label_dsl import ASTNode
    from exdrf.visitor import ExVisitor


@define
class ExResource:
    """The resource consists of a list of fields and is part of a dataset.

    You can retrieve a field using the `resource[key]` syntax, where key is
    either the name of the field or its index.

    Attributes:
        name: The name of the resource.
        dataset: The dataset that the resource is part of.
        fields: The fields that are part of this resource.
        categories: The categories of the resource.
        description: The description of the resource.
        src: The source of the resource. For sqlalchemy models this is the
            SQLAlchemy model class. For pydantic models this is the pydantic
            model class.
        label_ast: describes how to construct the label of a record.
        provides: The concepts that the resource provides.
        depends_on: The concepts that the resource depends on.
    """

    name: str
    dataset: "ExDataset" = field(default=None, repr=False)
    fields: List["ExField"] = field(factory=list)
    categories: List[str] = field(factory=list)
    description: str = ""
    src: Any = field(default=None)
    label_ast: "ASTNode" = field(default=None)
    provides: List[str] = field(factory=list)
    depends_on: List[Tuple[str, str]] = field(factory=list)

    def __attrs_post_init__(self):
        out = self.fields
        self.fields = []
        for fld in out:
            self.add_field(fld)

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        return f"<Resource {self.name} ({len(self.fields)} fields)>"

    def __hash__(self):
        return hash(f'{self.name}.{".".join(self.categories)}')

    def __contains__(self, key: Union[int, str]) -> bool:
        if isinstance(key, int):
            return 0 <= key < len(self.fields)
        return any(f.name == key for f in self.fields)

    def __iter__(self):
        """Make the resource iterable over its fields."""
        return iter(self.fields)

    def __len__(self) -> int:
        """Return the number of fields in the resource."""
        return len(self.fields)

    def __in__(self, key: Union[int, str]) -> bool:
        """Check if a field exists in the resource.

        Args:
            key: The key to check for. Can be either an index or field name.

        Returns:
            True if the field exists, False otherwise.
        """
        if isinstance(key, int):
            return key < len(self.fields)
        return any(f.name == key for f in self.fields)

    def __getitem__(self, key: Union[int, str]) -> "ExField":
        # If it is an index, return the field at that index.
        if isinstance(key, int):
            return self.fields[key]

        # Locate the field by name.
        for m in self.fields:
            if m.name == key:
                return m

        # If the field is not found, raise an error.
        raise KeyError(f"No field found for key `{key}` in model `{self.name}`")

    @cached_property
    def ref_fields(self) -> List["RefBaseField"]:
        """Get the fields that are references to other resources.

        Note that `get_dependencies` will return all related resources, even
        if they are not referenced in the fields of the resource.

        Returns:
            The fields that are references to other resources.
        """
        return cast(
            List["RefBaseField"],
            [fld for fld in self.fields if fld.is_ref_type],
        )

    @cached_property
    def derived_fields(self) -> List["ExField"]:
        """Get the fields that are derived from other fields."""
        return [fld for fld in self.fields if fld.is_derived]

    @cached_property
    def pascal_case_name(self) -> str:
        """Return the name of the resource in PascalCase."""
        return self.name

    @cached_property
    def snake_case_name(self) -> str:
        """Return the name of the resource in snake_case.

        Examples:
          If self.name == "ContractProposal", then:
              - snake_case_name -> "contract_proposal"
          If self.name == "IssItem", then:
              - snake_case_name -> "iss_item"
        """
        return re.sub(r"(?<!^)(?=[A-Z])", "_", self.name).lower()

    @cached_property
    def snake_case_name_plural(self) -> str:
        """Return the name of the resource in snake_case.

        Examples:
          If self.name == "ContractProposal", then:
              - snake_case_name_plural -> "contract_proposals"
          If self.name == "IssItem", then:
              - snake_case_name_plural -> "iss_items"
        """
        return inflect_e.plural(
            re.sub(r"(?<!^)(?=[A-Z])", "_", self.name).lower()  # type: ignore
        )

    @cached_property
    def camel_case_name(self) -> str:
        """Return the name of the resource in camelCase."""
        return self.name[0].lower() + self.name[1:]

    @cached_property
    def text_name(self) -> str:
        """Return the name of the resource in `Text case`."""
        tmp = re.sub(r"(?<!^)(?=[A-Z])", " ", self.name).lower()
        return tmp[0].upper() + tmp[1:]

    @cached_property
    def doc_lines(self) -> List[str]:
        """Get the docstring of the field as a set of lines.

        Returns:
            The docstring of the field as a set of lines.
        """
        return doc_lines(self.description)

    def add_field(self, fld: "ExField") -> None:
        """Add a field to the resource.

        Args:
            field: The field to add.
        """
        assert fld.name, "Field name must be set"
        assert fld.type_name, f"Field type must be set in {fld.name}"

        self.fields.append(fld)
        fld.resource = self  # type: ignore

        if not fld.category:
            fld.category = self.get_default_field_category(fld)

    def get_default_field_category(self, fld: "ExField") -> str:
        """Get the default category for a field.

        When adding a new field with an empty category the `add_field()`
        method will call this method to get the default category. Reimplement
        it if you want to assign categories to fields automatically.
        """
        return "keys" if fld.primary else "general"

    def get_fields_for_ref_filtering(self) -> List["ExField"]:
        """Get the fields that are going to be used with other models that
        reference this model when the user searches for text.
        """
        lst = self.minium_field_set_wo_primaries() or self.minimum_field_set()
        return [self[n] for n in lst if not self[n].is_ref_type]

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

    def get_dependencies(self, fk_only: bool = False) -> Set["ExResource"]:
        """Get the set of resources that this resource depends on.

        The method interrogates the fields of the resource and checks if any of
        them are references to other resources. If so, it adds them to the set
        of dependencies. This is useful for generating import statements or for
        determining the order in which resources should be processed.

        Note that only the first level of dependencies is considered so, if
        resource A depends on resource B, and resource B depends on resource C,
        resource C will not be reported by this method.

        Args:
            fk_only: If True, only dependencies that have their foreign key
                in the current resources are returned (ManyToOne and OneToOne).

        Returns:
            The set of resources that this resource depends on.
        """
        deps = set()
        for fld in self.fields:
            if fk_only:
                if fld.is_many_to_one_type or fld.is_one_to_one_type:
                    fld = cast("RefBaseField", fld)
                    if fld.ref is not self:
                        deps.add(fld.ref)

                # Extra dependencies are not included when fk_only is True.
                continue

            fld = cast("RefBaseField", fld)
            if fld.is_ref_type and fld.ref is not self:
                deps.add(fld.ref)
            for extra in fld.extra_ref(self.dataset):
                if extra is not self:
                    deps.add(extra)
        return deps

    def get_dep_fields(self, dep: "ExResource") -> List["ExField"]:
        """Get the fields that references a particular dependency.

        Args:
            dep: The dependency to look for.

        Returns:
            The fields that references the dependency.
        """
        return [fld for fld in self.ref_fields if fld.ref is dep]

    def minimum_field_set(self) -> List[str]:
        """Get the minimum set of fields that are used to represent the
        resource.

        This set includes all the fields that are used in the label definition
        and all the primary-key fields (fields that contribute to computing
        the identity of the resource).
        """
        names: Set[str] = set(get_used_fields(self.label_ast))
        for f in self.fields:
            if f.primary:
                names.add(f.name)
        return sorted(names)

    def minium_field_set_wo_primaries(self) -> List[str]:
        """Get the minimum set of fields that are used to represent the
        resource except those fields that are also primary keys.
        """
        names: Set[str] = set(
            [n.split(".")[0] for n in get_used_fields(self.label_ast)]
        )
        return sorted(
            n for n in names if self.__in__(n) and not self[n].primary
        )

    def primary_fields(self) -> List[str]:
        """Get the fields that are primary keys of the resource."""
        names: Set[str] = set()
        for f in self.fields:
            if f.primary:
                names.add(f.name)
        return sorted(names)

    def primary_inst_fields(self) -> List["ExField"]:
        """Get the fields that are primary keys of the resource."""
        names: Set[str] = set()
        for f in self.fields:
            if f.primary:
                names.add(f.name)
        return [self[n] for n in sorted(names)]

    @cached_property
    def is_primary_simple(self) -> bool:
        """Check if the resource has a simple primary key.

        A simple primary key is a single field that is used to identify the
        resource. If the resource has no primary key or more than one primary
        key, it is not a simple primary key.
        """
        return len(self.primary_fields()) == 1

    @cached_property
    def is_primary_simple_id(self) -> bool:
        """Check if the resource has a single primary key called `id`."""
        pf = self.primary_fields()
        return len(pf) == 1 and pf[0] == "id"

    @cached_property
    def is_connection_resource(self) -> bool:
        """Check if the resource is a connection resource.

        A connection resource is a resource that is used to connect two other
        resources. It is not a real resource and should not be included in the
        UI.
        """
        return all(f.primary for f in self.fields)

    @cached_property
    def is_join_table(self) -> bool:
        """A table that only contains two foreign key fields."""
        candidates = []
        for f in self.fields:
            if f.is_ref_type:
                continue
            if not f.primary:
                return False
            if f.type_name != FIELD_TYPE_INTEGER:
                return False
            if not f.name.endswith("_id"):
                return False
            candidates.append(f)
        if len(candidates) != 2:
            return False
        return True

    def rel_import(
        self,
        other: Union["ExResource", List[str]],
        path_up: str = "..",
        path_sep: str = "/",
    ) -> str:
        """Compute the import path for a resource relative to another resource.

        Resources are assumed to live at the end of the path indicated by the
        `categories` list. The import path is computed by finding the common
        prefix between the two resources and then computing the relative path
        from the other resource to this one.

        Args:
            other: The resource to import from or a path as a list of strings.
            path_up: The string to use to go up in the path. Defaults to '..'.
            path_sep: The string to use to separate the elements of the path.
                Defaults to '/'.

        Returns:
            The relative import path, with elements separated by slashes.
        """
        if isinstance(other, ExResource):
            other_categories = other.categories
        else:
            other_categories = other

        # Find the common prefix.
        i = 0
        while (
            i < len(self.categories)
            and i < len(other_categories)
            and self.categories[i] == other_categories[i]
        ):
            i += 1

        # Compute the relative path.
        path = [path_up] * (len(other_categories) - i)
        path.extend(other_categories[i:])

        return path_sep.join(path)

    def ensure_path(
        self, path: str, extension: str, name: Optional[str] = None
    ):
        """Ensure that a path exists and computes file path.

        The final path is computed by joining the base `path` with the
        categories of the resource and the name of the resource, and appending
        the `extension`.

        Args:
            path: The base path to write the file to.
            extension: The extension of the file without a dot.
            name: override the name of the resource; the resource name is
                stored as a Pascal-case string and you may want to use a
                different case convention for the file; also, there's nothing
                preventing you from including a prefix path with the name
                that will be applied at the end of the categories path.

        Returns:
            The full path to the file.
        """
        # Create the output file path.
        file_path = os.path.join(
            path, *self.categories, f"{name or self.name}.{extension}"
        )

        # Create the output directory if it doesn't exist.
        dir_path = os.path.dirname(file_path)
        os.makedirs(dir_path, exist_ok=True)

        return file_path

    def field_sort_key(self, fld: "ExField") -> str:
        """Get the sort key for a field.

        The sort key is used to sort the fields in the resource. By default it
        is computed by joining the categories of the resource with the name of
        the field.

        You may want to reimplement this method in a subclass if you want to
        the fields ranked before the alphabetical sort.

        Args:
            fld: The field to get the sort key for.

        Returns:
            The sort key for the field.
        """
        category = fld.category or ""
        return f"{category}.{fld.name}"

    def sorted_fields(self) -> List["ExField"]:
        """Get a sorted list of fields.

        You can customize the order of the fields by reimplementing the
        `field_sort_key` method.
        """
        return sorted(
            self.fields,
            key=self.field_sort_key,
        )

    def fields_by_category(
        self,
        exclude_names: Optional[Set[str]] = None,
        exclude_derived: Optional[bool] = False,
        exclude_ref_fields: Optional[bool] = False,
        exclude_fk_to: Optional[bool] = False,
        exclude_fk_from: Optional[bool] = False,
    ) -> Dict[str, List["ExField"]]:
        """Get a dictionary that maps categories to fields.

        The keys of the dictionary are the categories and the values are lists
        of sorted fields in that category. The fields are sorted using the
        `field_sort_key()` key.

        Args:
            exclude_names: The names of the fields to exclude.
            exclude_derived: If True, derived fields will not be included.
            exclude_ref_fields: If True, reference fields will not be included.
        """
        categories: Dict[str, List["ExField"]] = {}
        for f in self.sorted_fields():
            if exclude_names and f.name in exclude_names:
                continue
            if exclude_derived and f.is_derived:
                continue
            if exclude_ref_fields and f.is_ref_type:
                continue
            if exclude_fk_to and f.fk_to is not None:
                continue
            if exclude_fk_from and f.fk_from is not None:
                continue
            category = f.category
            lst = categories.get(category, None)
            if lst is None:
                categories[category] = lst = []
            lst.append(f)
        return categories

    def category_sort_key(self, cat: str) -> str:
        """Get the sort key for a category.

        The sort key is used to sort the categories in the resource. By
        default it is the category itself.

        You may want to reimplement this method in a subclass if you want to
        the categories ranked before the alphabetical sort.

        Args:
            cat: The category to get the sort key for.

        Returns:
            The sort key for the category.
        """
        if cat == "general":
            return "a-" + cat
        return "z-" + cat

    def sorted_fields_and_categories(
        self,
        exclude_names: Optional[Set[str]] = None,
        exclude_derived: Optional[bool] = False,
        exclude_ref_fields: Optional[bool] = False,
        exclude_fk_to: Optional[bool] = False,
        exclude_fk_from: Optional[bool] = False,
    ) -> OrderedDict[str, List["ExField"]]:
        """Get a dictionary that maps categories to fields.

        Both the fields and the categories are sorted:
        - the fields are sorted using the `field_sort_key()` key.
        - the categories are sorted using the `category_sort_key()` function.

        Args:
            exclude_names: The names of the fields to exclude.
            exclude_derived: If True, derived fields will not be included.
            exclude_ref_fields: If True, reference fields will not be included.
        """
        categories = self.fields_by_category(
            exclude_names=exclude_names,
            exclude_derived=exclude_derived,
            exclude_ref_fields=exclude_ref_fields,
            exclude_fk_to=exclude_fk_to,
            exclude_fk_from=exclude_fk_from,
        )
        result = OrDict()
        for k in sorted(categories.keys(), key=self.category_sort_key):
            result[k] = categories[k]
        return result

    def label_to_python(self) -> str:
        """Convert a label to python code."""
        return generate_python_code(self.label_ast)

    def label_to_typescript(self) -> str:
        """Convert a label to typescript code."""
        return generate_typescript_code(self.label_ast)


class ResExtraInfo(BaseModel):
    """The layout of the dictionary associated with resources in the model.

    Attributes:
        label: The string definition of the layer composition function using
            layer_dsl syntax.
        provides: The concepts that the resource provides. This can be used
            to indicate that the control's value has a certain meaning.
            This can be a hint that other resources that depend on this one
            should be updated when the value representing this resource changes.
        depends_on: The concepts that the resource depends on. A change
            in a resource listed here would change the meaning of this
            resource's value.
    """

    label: Optional[str] = None
    provides: Optional[List[str]] = Field(default_factory=list)
    depends_on: Optional[List[Tuple[str, str]]] = Field(default_factory=list)

    def get_layer_ast(self) -> "ASTNode":
        """Return the layer composition function using layer_dsl syntax."""
        if not self.label:
            return []
        return parse_expr(self.label)
