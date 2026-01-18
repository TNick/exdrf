from typing import Any, List, Optional, Tuple

from attrs import define, field
from pydantic import Field, field_validator

from exdrf.constants import FIELD_TYPE_STRING
from exdrf.field import ExField, FieldInfo


@define
class StrField(ExField):
    """A field that stores strings.

    Attributes:
        multiline: Whether the string can span multiple lines.
        min_length: The minimum length of the string.
        max_length: The maximum length of the string.
        enum_values: The list of predefined (named) values for the field. The
            first element of the tuple is the value, the second element is the
            display name.
        no_dia_field: The name of the field that is used to store the value
            of this field without diacritics.
    """

    type_name: str = field(default=FIELD_TYPE_STRING)

    multiline: bool = field(default=False)
    min_length: int = field(default=None)
    max_length: int = field(default=None)
    enum_values: List[Tuple[str, str]] = field(factory=list)

    no_dia_field: Optional["ExField"] = field(default=None)

    def __repr__(self) -> str:
        return f"StrF(" f"{self.resource.name}.{self.name})"

    def field_properties(self, explicit: bool = False) -> dict[str, Any]:
        result = super().field_properties(explicit)
        if self.multiline or explicit:
            result["multiline"] = self.multiline
        if self.min_length is not None or explicit:
            result["min_length"] = self.min_length
        if self.max_length is not None or explicit:
            result["max_length"] = self.max_length
        if self.enum_values or explicit:
            result["enum_values"] = self.enum_values
        return result


class StrInfo(FieldInfo):
    """Parser for information about a string field.

    Attributes:
        multiline: Whether the string can span multiple lines.
        min_length: The minimum length of the string.
        max_length: The maximum length of the string. Note that providing a
            value for this attribute will override the derived value from the
            database column (like `VARCHAR(255)`; see `field_from_sql_col()`
            implementation).
        enum_values: The list of predefined (named) values for the field. The
            first element of the tuple is the value, the second element is the
            display name.
    """

    multiline: Optional[bool] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    enum_values: List[Tuple[str, str]] = Field(default_factory=list)

    @field_validator("enum_values", mode="before")
    @classmethod
    def validate_enum_values(cls, v):
        """Validate the enum values.

        Accepts either a list of (int, str) tuples or an Enum class.
        """
        return cls.validate_enum_with_type(v, str)
