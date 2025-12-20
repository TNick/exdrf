import logging
from copy import copy
from typing import TYPE_CHECKING, Generator, Generic, Mapping, TypeVar

import openpyxl.cell._writer as www
import openpyxl.worksheet._writer as ww2
from attrs import define, field
from openpyxl.cell._writer import _set_attributes
from openpyxl.cell.rich_text import CellRichText
from openpyxl.compat import safe_string
from openpyxl.styles import Alignment, PatternFill
from openpyxl.styles.colors import Color
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.formula import ArrayFormula, DataTableFormula
from openpyxl.worksheet.table import Table, TableColumn, TableStyleInfo
from openpyxl.xml.functions import XML_NS, Element
from sqlalchemy import func, select

if TYPE_CHECKING:
    from openpyxl.worksheet.worksheet import Worksheet
    from sqlalchemy.orm import Session
    from sqlalchemy.sql import Select

    from .column import XlColumn
    from .schema import XlSchema

T = TypeVar("T")
logger = logging.getLogger(__name__)


def _normalize_rgb_color(value: str) -> str:
    """Normalize a color string into an 8-digit ARGB hex format.

    Args:
        value: A hex color value, in "RRGGBB" or "AARRGGBB" format. The leading
            "#" is optional.

    Returns:
        An 8-digit ARGB hex string (e.g., "FFFF0000").

    Raises:
        ValueError: If the provided value is not a supported hex color format.
    """
    normalized = value.strip().lstrip("#").upper()
    if len(normalized) == 6:
        return "FF" + normalized
    if len(normalized) == 8:
        return normalized
    raise ValueError(
        "Invalid color value %r; expected RRGGBB or AARRGGBB" % value
    )


def lxml_write_cell_o(xf, worksheet, cell, styled=False):
    """Write a cell using lxml, preserving whitespace for strings.

    This is a lightly modified copy of openpyxl's cell writer, patched into
    openpyxl's writer module at import time.

    Args:
        xf: XML generator/writer.
        worksheet: Target worksheet instance.
        cell: Cell to serialize.
        styled: Whether to include style information for the cell.
    """
    value, attributes = _set_attributes(cell, styled)

    if value == "" or value is None:
        with xf.element("c", attributes):
            return

    if isinstance(value, tuple) and cell.data_type == "f":
        attributes["t"] = "str"

    with xf.element("c", attributes):
        if cell.data_type == "f":
            attrib = {}

            final_value = None

            if isinstance(value, ArrayFormula):
                attrib = dict(value)
                value = value.text

            elif isinstance(value, DataTableFormula):
                attrib = dict(value)
                value = None

            elif isinstance(value, tuple):
                assert len(value) == 2
                final_value = value[1]
                value = value[0]

            with xf.element("f", attrib):
                if value is not None and not attrib.get("t") == "dataTable":
                    xf.write(value[1:])
                    value = final_value

        if cell.data_type == "s":
            if isinstance(value, CellRichText):
                el = value.to_tree()
                xf.write(el)
            else:
                with xf.element("is"):
                    if isinstance(value, str):
                        attrs = {}
                        if value != value.strip():
                            attrs["{%s}space" % XML_NS] = "preserve"
                        el = Element("t", attrs)  # lxml can't handle xml-ns
                        el.text = value
                        xf.write(el)

        else:
            with xf.element("v"):
                if value is not None:
                    xf.write(safe_string(value))


www.write_cell = lxml_write_cell_o
www.lxml_write_cell = lxml_write_cell_o
ww2.write_cell = lxml_write_cell_o


@define
class XlTable(Generic[T]):
    """Describes the mapping between a database table and an
    Excel sheet.

    Attributes:
        schema: The schema that contains the table.
        sheet_name: Worksheet name to create in the workbook.
        xl_name: Structured table name (Excel "Table" displayName).
        columns: Column definitions in display order.

            Notes:
            - Only columns where `XlColumn.is_included()` returns `True` are
              written.
            - Column formatting (widths, alignments, optional font/fill colors)
              is applied to data rows (starting at row 2), not the header row.
    """

    schema: "XlSchema" = field(repr=False)
    sheet_name: str
    xl_name: str
    columns: list["XlColumn"] = field(factory=list, repr=False)

    def __attrs_post_init__(self):
        for c in self.columns:
            c.table = self

    def get_selector(self) -> "Select":
        """Returns the SQLAlchemy selector for the table."""
        raise NotImplementedError("Subclasses must implement this method")

    def get_rows(self, session: "Session") -> Generator[T, None, None]:
        """Returns the rows of the table.

        Args:
            session: SQLAlchemy session used to execute the selector.
        """
        for row in session.scalars(self.get_selector()):
            yield row

    def get_rows_count(self, session: "Session") -> int:
        """Returns the number of rows in the table.

        Args:
            session: SQLAlchemy session used to execute the selector.
        """
        result = session.scalar(
            select(func.count()).select_from(self.get_selector())
        )  # type: ignore
        if result is None:
            logger.error(
                f"Failed to retrieve rows count for table {self.xl_name}"
            )
            return 0
        return result

    def write_to_sheet(self, sheet: "Worksheet", session: "Session"):
        """Creates the table in the sheet.

        Args:
            sheet: Target worksheet.
            session: SQLAlchemy session used to load rows for export.
        """
        if len(self.columns) == 0:
            logger.warning(f"Table {self.xl_name} has no columns")
            # return

        included = self.get_included_columns()
        for c, column in enumerate(included):
            sheet.cell(row=1, column=c + 1, value=column.xl_name)

        row_count = 0
        for row_idx, record in enumerate(self.get_rows(session)):
            row_count += 1
            for column in included:
                # Write data rows starting at row 2 (row 1 is the header).
                column.write_to_sheet(sheet, row_idx, record)

        table_obj = self.create_excel_table(sheet, row_count)
        assert table_obj
        sheet.add_table(table_obj)

        self.apply_column_widths(sheet, {})
        self.apply_alignments(sheet)
        self.apply_cell_styles(sheet, row_count)

        row_count = 0
        for row_idx, record in enumerate(self.get_rows(session)):
            row_count += 1
            for column in included:
                column.post_table_created(sheet, table_obj, row_idx, record)

    def create_excel_table(self, ws: "Worksheet", row_count: int) -> "Table":
        """Create the Excel structured table object on worksheet.

        Args:
            ws: Excel worksheet object.
            row_count: Number of data rows (excluding header).

        Returns:
            The created structured table object.
        """
        # if not self.columns or row_count == 0:
        #     return None
        columns = self.get_included_columns()
        num_cols = len(columns)
        last_col = get_column_letter(num_cols)
        num_rows = row_count + 1  # include header row
        ref = f"A1:{last_col}{num_rows}"

        table_obj = Table(displayName=self.xl_name, ref=ref)
        table_obj._initialise_columns()  # type: ignore

        style = TableStyleInfo(
            name="TableStyleMedium9",
            showFirstColumn=False,
            showLastColumn=False,
            showRowStripes=True,
            showColumnStripes=False,
        )
        table_obj.tableStyleInfo = style
        table_obj.tableColumns = [
            TableColumn(id=i + 1, name=h.xl_name) for i, h in enumerate(columns)
        ]
        return table_obj

    def apply_column_widths(
        self, ws: "Worksheet", widths: Mapping[str, float | None]
    ):
        """Apply saved column widths from previous export.

        Args:
            ws: Excel worksheet object.
            widths: Dictionary mapping column names to widths.
        """
        # Apply widths to all columns.
        for col_idx, col_def in enumerate(self.get_included_columns(), start=1):
            col_name = col_def.xl_name
            col_letter = get_column_letter(col_idx)
            col = ws.column_dimensions[col_letter]

            override_width = widths.get(col_name, None)
            if override_width is None:
                col.width = col_def.col_width
            else:
                col.width = override_width

    def apply_alignments(self, ws: "Worksheet"):
        """Apply column alignment settings to data cells.

        Args:
            ws: Excel worksheet object.
        """
        for col_idx, col_def in enumerate(self.get_included_columns(), start=1):
            align = Alignment(
                wrap_text=col_def.wrap_text,
                horizontal=col_def.h_align,
                vertical=col_def.v_align,
            )
            for row in ws.iter_rows(
                min_col=col_idx, max_col=col_idx, min_row=2
            ):
                row[0].alignment = align

    def apply_cell_styles(self, ws: "Worksheet", row_count: int):
        """Apply per-column cell styles (font color and background fill).

        Args:
            ws: Excel worksheet object.
            row_count: Number of data rows (excluding the header).
        """
        if row_count <= 0:
            return

        max_row = row_count + 1  # include header row at 1; data starts at 2

        for col_idx, col_def in enumerate(self.get_included_columns(), start=1):
            if col_def.font_color is None and col_def.bg_color is None:
                continue

            font_color = None
            if col_def.font_color is not None:
                font_color = Color(rgb=_normalize_rgb_color(col_def.font_color))

            fill = None
            if col_def.bg_color is not None:
                rgb = _normalize_rgb_color(col_def.bg_color)
                fill = PatternFill(
                    fill_type="solid",
                    start_color=rgb,
                    end_color=rgb,
                )

            for row in ws.iter_rows(
                min_col=col_idx,
                max_col=col_idx,
                min_row=2,
                max_row=max_row,
            ):
                cell = row[0]

                if font_color is not None:
                    font = copy(cell.font)
                    font.color = font_color
                    cell.font = font

                if fill is not None:
                    cell.fill = fill

    def get_included_columns(self) -> list["XlColumn"]:
        """Returns the columns that are included in the table."""
        return [c for c in self.columns if c.is_included()]

    def get_column_index(self, column: "XlColumn | str") -> int:
        """Returns the index of the column in the table.

        Args:
            column: Column reference, either by `XlColumn` instance (identity)
                or by column name (`XlColumn.xl_name`).

        Returns:
            0-based index in the *included* columns list, or -1 if not found.
        """
        idx = 0

        if isinstance(column, str):
            for idx, c in enumerate(self.get_included_columns()):
                if c.xl_name == column:
                    return idx
            return -1
        else:
            for idx, c in enumerate(self.get_included_columns()):
                if c is column:
                    return idx
            return -1
