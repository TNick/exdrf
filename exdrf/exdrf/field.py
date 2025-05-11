from typing import TYPE_CHECKING, Any, List, Optional

from attrs import define, field
from pydantic import BaseModel

from exdrf.constants import (
    FIELD_TYPE_REF_MANY_TO_MANY,
    FIELD_TYPE_REF_MANY_TO_ONE,
    FIELD_TYPE_REF_ONE_TO_MANY,
    FIELD_TYPE_REF_ONE_TO_ONE,
)
from exdrf.utils import doc_lines, inflect_e

if TYPE_CHECKING:
    from exdrf.dataset import ExDataset  # noqa: F401
    from exdrf.resource import ExResource  # noqa: F401
    from exdrf.visitor import ExVisitor  # noqa: F401


@define
class ExField:
    """A class representing a field in a resource.

    Attributes:
        name: The name of the field inside the resource. This is expected to be
            in snake_case.
        resource: The resource that the field belongs to.
        src: The source from which this field was derived. If the field
            was created from SqlAlchemy, this would be the SqlAlchemy column.
        title: A string suitable to be used as a title for the field.
        description: A longer description of the field.
        category: The category of the field. This should be a short
            string; nested categories using the dot notation are not supported.
        type_name: The unique type name of the field.
        is_list: Whether field contains multiple items (like when there are
            many-to-many relations or one-to-many relations).
        primary: Whether this filed contributes to constructing the identity
            of a record.
        visible: Whether the field is visible to the user. You may want to
            set this to `False` for password hashes or other sensitive data.
        read_only: An alternative to `visible` that shows the content of the
            field but does not allow the user to edit it.
        nullable: Whether the field is nullable.
        sortable: Whether the user can sort list results by this field.
        filterable: Whether the user can filter list results by this field.
        exportable: Whether the field is user exportable.
        qsearch: Whether the field is part of the quick search set.
        resizable: Whether the user can resize the column in the list view.
        fk_to: if this field is a foreign key, this property is the field
            representing the resolved resource (if this field is `parent_id`,
            the fk_to is `parent`).
        fk_from: if this field points to a resource, this property is the
            field representing the foreign key (if this field is `parent`,
            the fk_from field is `parent_id`).
    """

    name: str = field(default="")
    resource: "ExResource" = field(default=None)
    src: Any = field(default=None)
    title: str = field(default="")
    description: str = field(default="")
    category: str = field(default="")

    type_name: str = field(default="")

    is_list: bool = field(default=False)
    primary: bool = field(default=False)
    visible: bool = field(default=True)
    read_only: bool = field(default=False)
    nullable: bool = field(default=True)
    sortable: bool = field(default=True)
    filterable: bool = field(default=True)
    exportable: bool = field(default=True)
    qsearch: bool = field(default=True)
    resizable: bool = field(default=True)
    fk_to: Optional["ExField"] = field(default=None)
    fk_from: Optional["ExField"] = field(default=None)

    def __hash__(self):
        return hash(f"{self.resource.name}.{self.name}")

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        return f"{self.resource.name}.{self.name}"

    @property
    def pascal_case_name(self) -> str:
        """Return the name of the resource in PascalCase."""
        return "".join([c.title() for c in self.name.split("_")])

    @property
    def snake_case_name(self) -> str:
        """Return the name of the resource in snake_case."""
        return self.name

    @property
    def snake_case_name_plural(self) -> str:
        """Return the name of the resource in snake_case."""
        parts = self.name.split("_")
        parts[-1] = inflect_e.plural(parts[-1])  # type: ignore
        return "_".join(parts)

    @property
    def camel_case_name(self) -> str:
        """Return the name of the resource in camelCase."""
        return self.name[0].lower() + self.pascal_case_name[1:]

    @property
    def text_name(self) -> str:
        """Return the name of the resource in `Text case`."""
        parts = self.name.split("_")
        parts[0] = parts[0].title()
        return " ".join(parts)

    @property
    def doc_lines(self) -> List[str]:
        """Get the docstring of the field as a set of lines.

        Returns:
            The docstring of the field as a set of lines.
        """
        return doc_lines(self.description)

    @property
    def is_ref_type(self) -> bool:
        """Check if the field is a reference type.

        Returns:
            True if the field is a reference type, False otherwise.
        """
        return self.type_name in (
            FIELD_TYPE_REF_ONE_TO_MANY,
            FIELD_TYPE_REF_ONE_TO_ONE,
            FIELD_TYPE_REF_MANY_TO_MANY,
            FIELD_TYPE_REF_MANY_TO_ONE,
        )

    @property
    def is_one_to_many_type(self) -> bool:
        """Check if the field is a one-to-many type.

        In this type of relation there is one item of the present resource
        that is related to many items of the related resource.

        It is asserted that in this case the `is_list` attribute is set to
        `True`.

        Returns:
            True if the field is a one-to-many type, False otherwise.
        """
        return self.type_name == FIELD_TYPE_REF_ONE_TO_MANY

    @property
    def is_one_to_one_type(self) -> bool:
        """Check if the field is a one-to-one type.

        In this type of relation there is one item of the present resource
        that is related to one item of the related resource.

        It is asserted that in this case the `is_list` attribute is set to
        `False`.

        Returns:
            True if the field is a one-to-one type, False otherwise.
        """
        return self.type_name == FIELD_TYPE_REF_ONE_TO_ONE

    @property
    def is_many_to_many_type(self) -> bool:
        """Check if the field is a many-to-many type.

        In this type of relation there are many items of the present
        resource that are related to many items of the related resource.

        It is asserted that in this case the `is_list` attribute is set to
        `True`.

        Returns:
            True if the field is a many-to-many type, False otherwise.
        """
        return self.type_name == FIELD_TYPE_REF_MANY_TO_MANY

    @property
    def is_many_to_one_type(self) -> bool:
        """Check if the field is a many-to-one type.

        In this type of relation there are many items of the present
        resource that are related to one item of the related resource.

        It is asserted that in this case the `is_list` attribute is set to
        `False`.

        Returns:
            True if the field is a many-to-one type, False otherwise.
        """
        return self.type_name == FIELD_TYPE_REF_MANY_TO_ONE

    def visit(self: "ExField", visitor: "ExVisitor") -> bool:
        """Visit the resource and its fields.

        Args:
            visitor: The visitor to use.

        Returns:
            bool: True if the visit should continue, False otherwise.
        """
        return visitor.visit_field(self)  # type: ignore

    def extra_ref(self, d_set: "ExDataset") -> List["ExResource"]:
        """Additional dependencies of this field.

        Usually only dependencies that reference other fields generate
        dependencies (other resources that are used by a particular resource).

        This method allows the field to specify additional dependencies that
        are not automatically detected.

        See `Resource.get_dependencies()` for more details.

        Args:
            d_set: The dataset to which the resource belongs.

        Returns:
            A list of resources that this field depends on.
        """
        return []


class FieldInfo(BaseModel):
    """Base parser for information about a field.

    We use this mechanism when the information extracted from the source of the
    field needs to be supplemented with additional information.

    The attributes have exactly the same names as those in the `Field` class,
    so that they can be used to create a `Field` object.

    Attributes:
        title: A string suitable to be used as a title for the field. If
            not provided the default is the name of the field capitalized
            and with underscores replaced by spaces.
        description: A longer description of the field.
        category: The category of the field. This should be a short
            string; nested categories using the dot notation are not supported.
            For common cases the implementation may subclass the `Resource`
            class and reimplement the `get_default_category()` method.
        type_name: The unique type name of the field. If provided, it overrides
            the internal logic that determines the type name of the field.
            It should be one of the `FIELD_TYPE_*` constants defined in the
            `exdrf.constants` module.
        primary: Whether this filed contributes to constructing the identity
            of a record.
        visible: Whether the field is visible to the user. You may want to
            set this to `False` for password hashes or other sensitive data.
        read_only: An alternative to `visible` that shows the content of the
            field but does not allow the user to edit it.
        nullable: Whether the field is nullable.
        sortable: Whether the user can sort list results by this field.
        filterable: Whether the user can filter list results by this field.
        exportable: Whether the field is user exportable.
        qsearch: Whether the field is part of the quick search set.
        resizable: Whether the user can resize the column in the list view.
    """

    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    type_name: Optional[str] = None
    primary: Optional[bool] = None
    visible: Optional[bool] = None
    read_only: Optional[bool] = None
    nullable: Optional[bool] = None
    sortable: Optional[bool] = None
    filterable: Optional[bool] = None
    exportable: Optional[bool] = None
    qsearch: Optional[bool] = None
    resizable: Optional[bool] = None
