import json
import logging
from datetime import datetime
from typing import (
    Any,
    Callable,
    Generic,
    Literal,
    Type,
    TypeVar,
    Union,
)

from attrs import define, field
from exdrf.constants import FIELD_TYPE_DT  # type: ignore[import]

T = TypeVar("T")
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
        primary: Whether this column participates in the "primary key" used by
            import logic to decide whether a row is usable and to find existing
            database records.
        col_width: Column width to apply on export when no external override is
            provided.
        wrap_text: Whether cell text should wrap (applied to data cells).
        number_format: Optional Excel number format to apply to data cells in
            this column. If `None`, the number format is not changed.
            Valid examples: `"0"`, `"0.00"`, `"#,##0"`, `"yyyy-mm-dd"`.
        font_color: Optional font color for data cells in this column. If
            `None`, the font color is not changed.
            Valid examples: `"FF0000"`, `"#FF0000"`, `"FFFF0000"`,
            `"#FFFF0000"`.
        bg_color: Optional background fill color for data cells in this column.
            If `None`, the fill is not changed.
            Valid examples: `"00FF00"`, `"#00FF00"`, `"FF00FF00"`,
            `"#FF00FF00"`.
        hidden: Whether the worksheet column should be hidden on export.
        h_align: Horizontal alignment for data cells (`"left"`, `"center"`,
            `"right"`).
        v_align: Vertical alignment for data cells (`"top"`, `"center"`,
            `"bottom"`).
    """

    table: Any = field(default=None, repr=False)
    xl_name: str
    primary: bool = field(default=False, repr=False)
    read_only: bool = field(init=False, default=False, repr=False)
    nullable: bool = field(init=False, default=True, repr=False)
    type_name: str = field(init=False, default="string", repr=False)
    col_width: float = field(default=10.0, repr=False)
    wrap_text: bool = field(default=False, repr=False)
    number_format: str | None = field(default=None, repr=False)
    font_color: str | None = field(default=None, repr=False)
    bg_color: str | None = field(default=None, repr=False)
    hidden: bool = field(default=False, repr=False)
    h_align: Literal["left", "center", "right"] = field(
        default="left", repr=False
    )
    v_align: Literal["top", "center", "bottom"] = field(
        default="center", repr=False
    )
    fk_table: str | None = field(
        init=False,
        default=None,
        repr=False,
    )
    is_generated_pk: bool = field(
        init=False,
        default=False,
        repr=False,
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

    def write_to_sheet(self, sheet: Any, row_index: int, record: DB):
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

        # Render unknown date-time sentinel outside Excel range as "x".
        if (
            str(getattr(self, "type_name", None))
            in ("datetime", "date-time", FIELD_TYPE_DT)
            and isinstance(value, datetime)
            and value.year == 1000
            and value.month == 2
            and value.day == 3
            and value.hour == 4
            and value.minute == 5
            and value.second == 6
        ):
            value = "x"
        col = self.table.get_column_index(self)
        if col == -1:
            logger.warning(
                "Column %s not found in table %s",
                self.xl_name,
                self.table.xl_name,
            )
            return
        cell = sheet.cell(
            # Row 1 is reserved for the header; data begins at row 2.
            row=row_index + 2,
            column=col + 1,
            value=value,
        )

        if self.number_format is None:
            return

        cell.number_format = self.number_format

    def post_table_created(self, ws: Any, table_obj: T, row_count: int):
        """Called after the table is created.

        Args:
            ws: Target worksheet.
            table_obj: The Excel structured table object created for the sheet.
            row_count: the number of rows written in the sheet.
        """

    def apply_duplicate_values_conditional_formatting(
        self, ws: Any, row_count: int
    ):
        """Apply "duplicate values" conditional formatting for this column.

        This is a convenience wrapper around
        `XlTable.apply_duplicate_values_conditional_formatting()` that targets
        included columns whose `xl_name` matches this column name (case- and
        whitespace-normalized).

        Args:
            ws: Target worksheet.
            row_count: Number of data rows written (excluding the header).
        """
        self.table.apply_duplicate_values_conditional_formatting(
            ws=ws,
            row_count=row_count,
            predicate=lambda c: c.xl_name.strip().lower() == self.xl_name,
            fill_color="FFFFC7CE",
            font_color="FFFF0000",
        )

    def apply_xl_to_db(self, session: Any, db_rec: DB, xl_value: Any):
        """Apply an Excel value to a database record.

        Subclasses can override this to do validation, lookups, or type
        conversions before assigning to the destination record.

        Args:
            session: SQLAlchemy session, available for lookups and related
                queries.
            db_rec: Database record to update.
            xl_value: Value parsed from Excel for this column.
        """
        setattr(db_rec, self.xl_name, xl_value)


@define(slots=True, kw_only=True)
class XlReadOnlyColumn(XlColumn[T, DB]):
    """A column that is not editable and is ignored on import.

    This is intended for columns that contain formulas or derived values that
    should be visible in Excel but must not be written back into the database.
    """

    read_only: bool = field(init=False, default=True, repr=False)


@define(slots=True, kw_only=True)
class Change:
    """Describes a structural modification to a table's column list.

    Attributes:
        ref_type: Column reference that identifies where to apply the change.
            This can be a column name (`str`) or a column class/type.
        constructor: Callable used to construct the column being inserted or
            used as a replacement.
        kind: How to apply the change relative to the referenced column:
            `"before"`, `"after"`, or `"replace"`.
    """

    ref_type: Union[str, Type[XlColumn]]
    constructor: Callable[..., "XlColumn"]
    kind: Literal["before", "after", "replace"]
