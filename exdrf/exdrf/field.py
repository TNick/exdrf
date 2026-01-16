import enum
from datetime import datetime
from typing import TYPE_CHECKING, Any, List, Optional, Tuple

from attrs import define, field
from pydantic import BaseModel

from exdrf.constants import (
    FIELD_TYPE_BOOL,
    FIELD_TYPE_DATE,
    FIELD_TYPE_DT,
    FIELD_TYPE_FLOAT,
    FIELD_TYPE_FLOAT_LIST,
    FIELD_TYPE_INT_LIST,
    FIELD_TYPE_INTEGER,
    FIELD_TYPE_REF_MANY_TO_MANY,
    FIELD_TYPE_REF_MANY_TO_ONE,
    FIELD_TYPE_REF_ONE_TO_MANY,
    FIELD_TYPE_REF_ONE_TO_ONE,
    FIELD_TYPE_STRING,
    FIELD_TYPE_STRING_LIST,
)
from exdrf.utils import doc_lines, inflect_e

if TYPE_CHECKING:
    from exdrf.dataset import ExDataset  # noqa: F401
    from exdrf.resource import ExResource  # noqa: F401
    from exdrf.visitor import ExVisitor  # noqa: F401

NO_DIACRITICS = "no_diacritics"


@define
class ExFieldBase:
    """The minimal set of attributes for a field.

    Attributes:
        name: The name of the field inside the resource. This is expected to be
            in snake_case.
        title: A string suitable to be used as a title for the field.
        description: A longer description of the field.
        category: The category of the field. This should be a short
            string; nested categories using the dot notation are not supported.
        type_name: The unique type name of the field.
        nullable: Whether the field is nullable.
    """

    name: str = field(default="")
    title: str = field(default="")
    description: str = field(default="")
    category: str = field(default="")
    type_name: str = field(default="")
    nullable: bool = field(default=True)


@define
class ExField(ExFieldBase):
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
        derived: If the field is derived from another field, this property
            holds the name of that field and the type of derivation.
            For now the only supported type is NO_DIACRITICS which indicates
            that the value of this field results from the text value of another
            field without diacritics (unidecode is used to convert the text).
    """

    resource: "ExResource" = field(default=None)
    src: Any = field(default=None)

    is_list: bool = field(default=False)
    primary: bool = field(default=False)
    visible: bool = field(default=True)
    read_only: bool = field(default=False)
    sortable: bool = field(default=True)
    filterable: bool = field(default=True)
    exportable: bool = field(default=True)
    qsearch: bool = field(default=True)
    resizable: bool = field(default=True)
    fk_to: Optional["ExField"] = field(default=None)
    fk_from: Optional["ExField"] = field(default=None)
    derived: Optional[Tuple[str, str]] = field(default=None)

    def field_properties(self, explicit: bool = False) -> dict[str, Any]:
        """Get the properties of the field.

        Args:
            explicit: Whether to include explicit properties.
        """
        if explicit:
            return {
                "name": self.name,
                "resource": self.resource.name,
                "title": self.title,
                "description": self.description,
                "category": self.category,
                "type_name": self.type_name,
                "is_list": self.is_list,
                "primary": self.primary,
                "visible": self.visible,
                "read_only": self.read_only,
                "nullable": self.nullable,
                "sortable": self.sortable,
                "filterable": self.filterable,
                "exportable": self.exportable,
                "qsearch": self.qsearch,
                "resizable": self.resizable,
                "fk_to": self.fk_to.name if self.fk_to else None,
                "fk_from": self.fk_from.name if self.fk_from else None,
                "derived": self.derived,
            }
        else:
            result: dict[str, Any] = {
                "name": self.name,
                "resource": self.resource.name,
                "type_name": self.type_name,
                "nullable": self.nullable,
            }
            if self.title:
                result["title"] = self.title
            if self.description:
                result["description"] = self.description
            if self.category:
                result["category"] = self.category
            if self.is_list:
                result["is_list"] = self.is_list
            if self.primary:
                result["primary"] = self.primary
            if not self.visible:
                result["visible"] = self.visible
            if not self.read_only:
                result["read_only"] = self.read_only
            if not self.sortable:
                result["sortable"] = self.sortable
            if not self.filterable:
                result["filterable"] = self.filterable
            if not self.exportable:
                result["exportable"] = self.exportable
            if not self.qsearch:
                result["qsearch"] = self.qsearch
            if not self.resizable:
                result["resizable"] = self.resizable
            if self.fk_to:
                result["fk_to"] = self.fk_to.name
            if self.fk_from:
                result["fk_from"] = self.fk_from.name
            if self.derived:
                result["derived"] = self.derived
            return result

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

    @property
    def related_resource(self) -> Optional["ExResource"]:
        """Get the resource that this field is related to.

        Returns:
            The resource that this field is related to.
        """
        return self.ref if hasattr(self, "ref") else None  # type: ignore

    @property
    def is_derived(self) -> bool:
        """Check if the field is derived from another field.

        Returns:
            True if the field is derived from another field, False otherwise.
        """
        return self.derived is not None

    @property
    def derived_from(self) -> Optional[str]:
        """Get the name of the field that this field is derived from.

        Returns:
            The name of the field that this field is derived from.
        """
        return self.derived[0] if self.derived else None

    @property
    def derived_type(self) -> Optional[str]:
        """Get the type of derivation of the field.

        Returns:
            The type of derivation of the field.
        """
        return self.derived[1] if self.derived else None

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

    def value_to_str(self, value: Any) -> str:
        """Convert a value of this type to a string.

        Args:
            value: The value to convert.

        Returns:
            A string representation of the value.
        """
        if isinstance(value, (list, tuple)):
            return ", ".join(str(v) for v in value)
        elif isinstance(value, dict):
            return ", ".join(f"{k}: {v}" for k, v in value.items())
        else:
            return str(value)

    def value_from_str(self, value: str) -> Any:
        """Convert a string to a value of this type."""
        if self.type_name == FIELD_TYPE_STRING:
            return value
        elif self.type_name == FIELD_TYPE_INTEGER:
            return int(value)
        elif self.type_name == FIELD_TYPE_FLOAT:
            return float(value)
        elif self.type_name == FIELD_TYPE_BOOL:
            return bool(value)
        elif self.type_name == FIELD_TYPE_DATE:
            return datetime.strptime(value, "%Y-%m-%d").date()
        elif self.type_name == FIELD_TYPE_DT:
            return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
        elif self.type_name == FIELD_TYPE_REF_ONE_TO_MANY:
            if isinstance(value, (tuple, list)):
                return list(value)
            elif isinstance(value, str):
                return value.split(",")
            else:
                raise ValueError(
                    f"Invalid value for one-to-many: {value} of "
                    f"type {type(value)}"
                )
        elif self.type_name == FIELD_TYPE_REF_MANY_TO_MANY:
            if isinstance(value, (tuple, list)):
                return list(value)
            elif isinstance(value, str):
                return value.split(",")
            else:
                raise ValueError(
                    f"Invalid value for many-to-many: {value} of "
                    f"type {type(value)}"
                )
        elif self.type_name == FIELD_TYPE_INT_LIST:
            if isinstance(value, (tuple, list)):
                return list(value)
            elif isinstance(value, str):
                return [int(v) for v in value.split(",")]
            else:
                raise ValueError(
                    f"Invalid value for int list: {value} of "
                    f"type {type(value)}"
                )
        elif self.type_name == FIELD_TYPE_FLOAT_LIST:
            if isinstance(value, (tuple, list)):
                return list(value)
            elif isinstance(value, str):
                return [float(v) for v in value.split(",")]
            else:
                raise ValueError(
                    f"Invalid value for float list: {value} of "
                    f"type {type(value)}"
                )
        elif self.type_name == FIELD_TYPE_STRING_LIST:
            if isinstance(value, (tuple, list)):
                return list(value)
            elif isinstance(value, str):
                return value.split(",")
            else:
                raise ValueError(
                    f"Invalid value for string list: {value} of "
                    f"type {type(value)}"
                )
        else:
            return value


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
    derived: Optional[Tuple[str, str]] = None

    @staticmethod
    def validate_enum_with_type(v, value_type: type) -> List[Tuple[Any, str]]:
        """Validate the enum values.

        Accepts either a list of (value_type, str) tuples or an Enum class.
        """
        if isinstance(v, type) and issubclass(v, enum.Enum):
            # Convert Enum class to list of (value, name) tuples
            return [
                (
                    value_type(member.value),
                    member.name.replace("_", " ").title(),
                )
                for member in v
            ]
        elif isinstance(v, list):
            # Ensure all elements are (value_type, str) tuples
            for item in v:
                if (
                    not isinstance(item, tuple)
                    or len(item) != 2
                    or not isinstance(item[0], value_type)
                    or not isinstance(item[1], str)
                ):
                    raise TypeError(
                        "Each item in enum_values must be a tuple of "
                        f"({value_type}, str)"
                    )
            return v
        elif v is None:
            return []
        else:
            raise TypeError(
                f"enum_values must be a list of ({value_type}, str) "
                "tuples or an Enum class"
            )
