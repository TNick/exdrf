from typing import Optional

from attrs import define, field

from exdrf.constants import FIELD_TYPE_BLOB
from exdrf.field import ExField, FieldInfo


@define
class BlobField(ExField):
    """A field that stores binary data.

    The field cannot be used for filtering or sorting, and it is not usually
    visible to the user.

    Attributes:
        mime_type: The MIME type of the data stored in the field.
    """

    type_name: str = field(default=FIELD_TYPE_BLOB)
    visible: bool = field(default=False)
    sortable: bool = field(default=False)
    filterable: bool = field(default=False)

    mime_type: str = field(default="")

    def __repr__(self) -> str:
        return f"BlobF(" f"{self.resource.name}.{self.name})"


class BlobInfo(FieldInfo):
    """Parser for information about a blob field.

    Attributes:
        mime_type: The MIME type of the data stored in the field.
    """

    mime_type: Optional[str] = None
