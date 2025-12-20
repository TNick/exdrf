import json
import logging
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Generic,
    Literal,
    Type,
    TypeVar,
    Union,
)

from attrs import define, field

if TYPE_CHECKING:
    from openpyxl.worksheet.table import Table
    from openpyxl.worksheet.worksheet import Worksheet

    from .table import XlTable

T = TypeVar("T", bound="XlTable")
DB = TypeVar("DB")

logger = logging.getLogger(__name__)


@define(slots=True, kw_only=True)
class XlColumn(Generic[T, DB]):
    """A column in an Excel table.

    Attributes:
        table: Back-reference to the owning table. This is set automatically
            by `XlTable.__attrs_post_init__`.
        xl_name: Column header name written into the first row of the sheet and
            used for the structured table column name.
        col_width: Column width to apply on export when no external override is
            provided.
        wrap_text: Whether cell text should wrap (applied to data cells).
        font_color: Optional font color for data cells in this column. If
            `None`, the font color is not changed.
            Valid examples: `"FF0000"`, `"#FF0000"`, `"FFFF0000"`,
            `"#FFFF0000"`.
        bg_color: Optional background fill color for data cells in this column.
            If `None`, the fill is not changed.
            Valid examples: `"00FF00"`, `"#00FF00"`, `"FF00FF00"`,
            `"#FF00FF00"`.
        h_align: Horizontal alignment for data cells (`"left"`, `"center"`,
            `"right"`).
        v_align: Vertical alignment for data cells (`"top"`, `"center"`,
            `"bottom"`).
    """

    table: T = field(default=None, repr=False)
    xl_name: str
    col_width: float = field(default=10.0, repr=False)
    wrap_text: bool = field(default=False, repr=False)
    font_color: str | None = field(default=None, repr=False)
    bg_color: str | None = field(default=None, repr=False)
    h_align: Literal["left", "center", "right"] = field(
        default="left", repr=False
    )
    v_align: Literal["top", "center", "bottom"] = field(
        default="center", repr=False
    )

    def is_included(self) -> bool:
        """Returns True if the column is included in the table.

        Classes can implement this method to control if the column is
        included in the table at runtime.
        """
        return True

    def value_from_record(self, record: DB) -> Any:
        """Returns the value to use in the cell for the given record.

        Args:
            record: Source record.

        Returns:
            The value to write into the cell for this column.
        """
        raise NotImplementedError("Subclasses must implement this method")

    def write_to_sheet(self, sheet: "Worksheet", row_index: int, record: DB):
        """Writes the column to the sheet.

        Args:
            sheet: Target worksheet.
            row_index: 0-based index of the data row in the table.
            record: Source record.
        """
        value = self.value_from_record(record)
        if value is None:
            return
        if isinstance(value, (list, dict)):
            value = json.dumps(value)
        col = self.table.get_column_index(self)
        if col == -1:
            logger.warning(
                f"Column {self.xl_name} not found in table {self.table.xl_name}"
            )
            return
        sheet.cell(
            # Row 1 is reserved for the header; data begins at row 2.
            row=row_index + 2,
            column=col + 1,
            value=value,
        )

    def post_table_created(
        self, sheet: "Worksheet", table_obj: "Table", row_index: int, record: DB
    ):
        """Called after the table is created.

        Args:
            sheet: Target worksheet.
            table_obj: The Excel structured table object created for the sheet.
            row_index: 0-based index of the data row in the table.
            record: Source record.
        """


@define(slots=True, kw_only=True)
class Change:
    ref_type: Union[str, Type[XlColumn]]
    constructor: Callable[..., "XlColumn"]
    kind: Literal["before", "after", "replace"]
