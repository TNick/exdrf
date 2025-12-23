import logging
from copy import copy
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Generator,
    Generic,
    Mapping,
    TypeVar,
    cast,
)

import openpyxl.cell._writer as www
import openpyxl.worksheet._writer as ww2
from attrs import define, field
from openpyxl.cell._writer import _set_attributes
from openpyxl.cell.rich_text import CellRichText
from openpyxl.compat import safe_string
from openpyxl.formatting.rule import Rule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.styles.colors import Color
from openpyxl.styles.differential import DifferentialStyle
from openpyxl.utils import get_column_letter
from openpyxl.utils.cell import column_index_from_string, range_boundaries
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
                        # lxml can't handle xml-ns
                        el = Element("t", attrs)
                        el.text = value
                        xf.write(el)

        else:
            with xf.element("v"):
                if value is not None:
                    xf.write(safe_string(value))


www.write_cell = lxml_write_cell_o  # type: ignore
www.lxml_write_cell = lxml_write_cell_o  # type: ignore
ww2.write_cell = lxml_write_cell_o  # type: ignore


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
        _included_columns_cache: Cached list of included columns (those where
            `XlColumn.is_included()` is `True`). This is an internal cache.
        _included_index_by_name_cache: Cached mapping from column name
            (`XlColumn.xl_name`) to 0-based index in the included columns list.
            This is an internal cache.
        _included_index_by_objid_cache: Cached mapping from column object id
            (`id(column)`) to 0-based index in the included columns list. This
            is an internal cache.
    """

    schema: "XlSchema" = field(repr=False)
    sheet_name: str
    xl_name: str
    columns: list["XlColumn"] = field(factory=list, repr=False)
    _included_columns_cache: list["XlColumn"] | None = field(
        default=None, init=False, repr=False
    )
    _included_index_by_name_cache: dict[str, int] | None = field(
        default=None, init=False, repr=False
    )
    _included_index_by_objid_cache: dict[int, int] | None = field(
        default=None, init=False, repr=False
    )

    def __attrs_post_init__(self):
        """Finalize initialization after attrs has constructed the instance.

        This wires each column definition back to this table and initializes
        the included-column caches.
        """
        for c in self.columns:
            c.table = self
        self._invalidate_column_caches()

    def _invalidate_column_caches(self) -> None:
        """Invalidate cached included-columns data structures.

        This should be called after mutating `columns` or when any column's
        `is_included()` behavior can change.
        """
        self._included_columns_cache = None
        self._included_index_by_name_cache = None
        self._included_index_by_objid_cache = None

    def _ensure_column_caches(self) -> None:
        """Build cached included-columns data structures if missing.

        The caches store:
        - The list of included columns (in display order).
        - Fast lookup by column name and by column object identity.
        """
        if (
            self._included_columns_cache is not None
            and self._included_index_by_name_cache is not None
            and self._included_index_by_objid_cache is not None
        ):
            return

        included = [c for c in self.columns if c.is_included()]
        index_by_name: dict[str, int] = {}
        index_by_objid: dict[int, int] = {}

        for idx, c in enumerate(included):
            # Keep the first match for a name, consistent with prior behavior.
            index_by_name.setdefault(c.xl_name, idx)
            index_by_objid[id(c)] = idx

        self._included_columns_cache = included
        self._included_index_by_name_cache = index_by_name
        self._included_index_by_objid_cache = index_by_objid

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
        # Count rows from the selector by wrapping it as a subquery so it
        # becomes a valid FROM clause (and satisfies static type checkers).
        subq = self.get_selector().subquery()
        result = session.scalar(select(func.count()).select_from(subq))
        if result is None:
            logger.error(
                "Failed to retrieve rows count for table %s", self.xl_name
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
            logger.warning("Table %s has no columns", self.xl_name)
            # return

        included = self.get_included_columns()

        # Format header row.
        sheet.row_dimensions[1].height = 30
        header_align = Alignment(
            wrap_text=False,
            horizontal="center",
            vertical="top",
        )
        for c, column in enumerate(included):
            cell = sheet.cell(row=1, column=c + 1, value=column.xl_name)
            cell.alignment = header_align

        # Generate data rows.
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
        self.apply_duplicate_id_conditional_formatting(sheet, row_count)

        for column in included:
            column.post_table_created(sheet, table_obj, row_count)

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

            # Hide columns that are marked as hidden.
            col.hidden = col_def.hidden

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
                    # `cell.font` is a StyleProxy. Copy to a real Font and
                    # reassign so we don't mutate the proxy.
                    new_font = cast(Font, copy(cell.font))
                    new_font.color = font_color  # type: ignore
                    cell.font = new_font

                if fill is not None:
                    cell.fill = fill

    def apply_duplicate_id_conditional_formatting(
        self, ws: "Worksheet", row_count: int
    ):
        """Highlight duplicate values in columns named `id`.

        This is a convenience wrapper around
        `apply_duplicate_values_conditional_formatting()` that targets columns
        whose `xl_name` is `"id"` (case-insensitive).

        Args:
            ws: Excel worksheet object.
            row_count: Number of data rows (excluding the header).
        """
        self.apply_duplicate_values_conditional_formatting(
            ws=ws,
            row_count=row_count,
            predicate=lambda c: c.xl_name.strip().lower() == "id",
            fill_color="FFFFC7CE",
            font_color="FFFF0000",
        )

    def apply_duplicate_values_conditional_formatting(
        self,
        ws: "Worksheet",
        row_count: int,
        predicate: Callable[["XlColumn"], bool],
        fill_color: str,
        font_color: str,
    ):
        """Add Excel "duplicate values" conditional formatting for columns.

        This adds a native Excel conditional formatting rule of type
        `"duplicateValues"` to each included column that matches `predicate`.
        The rule is applied to the current data range (rows 2..N).

        Args:
            ws: Excel worksheet object.
            row_count: Number of data rows (excluding the header).
            predicate: Function that receives an included `XlColumn` and returns
                True if the rule should be applied to that column.
            fill_color: Background fill color (ARGB hex, e.g. `"FFFFC7CE"`).
            font_color: Font color (ARGB hex, e.g. `"FFFF0000"`).
        """
        if row_count <= 0:
            return

        max_row = row_count + 1  # include header row at 1; data starts at 2

        fill = PatternFill(
            fill_type="solid",
            start_color=fill_color,
            end_color=fill_color,
        )
        font = Font(color=font_color)
        dxf = DifferentialStyle(font=font, fill=fill)

        for col_idx, col_def in enumerate(self.get_included_columns(), start=1):
            if not predicate(col_def):
                continue

            col_letter = get_column_letter(col_idx)
            range_ref = f"{col_letter}2:{col_letter}{max_row}"

            rule = Rule(type="duplicateValues")
            rule.dxf = dxf
            ws.conditional_formatting.add(range_ref, rule)

    def __getitem__(self, key: int | str) -> "XlColumn":
        """Get an included column by index or by name.

        Args:
            key: Either a 0-based index into the included columns list, or the
                column name (`XlColumn.xl_name`).

        Returns:
            The matching included column.

        Raises:
            IndexError: If an integer index is out of range.
            KeyError: If a string name does not match any included column.
            TypeError: If `key` is not an `int` or `str`.
        """
        self._ensure_column_caches()

        if isinstance(key, int):
            assert self._included_columns_cache is not None
            return self._included_columns_cache[key]

        if isinstance(key, str):
            assert self._included_index_by_name_cache is not None
            idx = self._included_index_by_name_cache.get(key, None)
            if idx is None:
                raise KeyError(key)
            assert self._included_columns_cache is not None
            return self._included_columns_cache[idx]

        raise TypeError("Invalid key type %r; expected int or str" % type(key))

    def get_included_columns(self) -> list["XlColumn"]:
        """Returns the columns that are included in the table."""
        self._ensure_column_caches()
        assert self._included_columns_cache is not None
        return self._included_columns_cache

    def get_column_index(self, column: "XlColumn | str") -> int:
        """Returns the index of the column in the table.

        Args:
            column: Column reference, either by `XlColumn` instance (identity)
                or by column name (`XlColumn.xl_name`).

        Returns:
            0-based index in the *included* columns list, or -1 if not found.
        """
        self._ensure_column_caches()
        assert self._included_index_by_name_cache is not None
        assert self._included_index_by_objid_cache is not None

        if isinstance(column, str):
            return self._included_index_by_name_cache.get(column, -1)
        else:
            return self._included_index_by_objid_cache.get(id(column), -1)

    @staticmethod
    def _get_ws_col_idx(cell: object) -> int:
        """Return the 1-based worksheet column index for an openpyxl cell.

        Some openpyxl cell-like classes (e.g. `MergedCell`) do not expose
        `col_idx` in their type information, even though a column index can
        always be derived via `column`.
        """
        col_idx = getattr(cell, "col_idx", None)
        if isinstance(col_idx, int):
            return col_idx

        column = getattr(cell, "column", None)
        if isinstance(column, int):
            return column
        if isinstance(column, str):
            return column_index_from_string(column)

        raise TypeError(
            "Unsupported cell column type %r for cell %r" % (type(column), cell)
        )

    def iter_excel_table(self, ws: "Worksheet", table: "Table"):
        """Iterate rows from an Excel structured table and yield row dicts.

        Args:
            ws: Worksheet that contains the structured table.
            table: The openpyxl structured table object to iterate.

        Yields:
            A dictionary mapping `XlColumn.xl_name` to the cell value for that
            row. Only columns present in both the table definition and the
            worksheet are included.

            Rows are skipped if:
            - A `primary` column is missing from the worksheet table, or
            - A `primary` column has an empty/falsy value, or
            - The resulting record dict would be empty.
        """
        if not table.ref:
            return
        min_col, min_row, max_col, max_row = range_boundaries(
            cast(str, table.ref)
        )
        assert (
            min_col is not None
            and min_row is not None
            and max_col is not None
            and max_row is not None
        )

        # Build map: table header name -> 0-based column index in worksheet.
        header_row = next(
            ws.iter_rows(
                min_row=min_row,
                max_row=min_row,
                min_col=min_col,
                max_col=max_col,
            )
        )
        col_name_to_idx = {
            str(cell.value): (self._get_ws_col_idx(cell) - min_col)
            for cell in header_row
        }

        for row in ws.iter_rows(
            min_row=min_row + 1,
            max_row=max_row,
            min_col=min_col,
            max_col=max_col,
        ):
            ignore_row = False
            xl_record = {}
            for c in self.columns:
                c_index = col_name_to_idx.get(c.xl_name, None)
                if c_index is None:
                    if c.primary:
                        # One of the primary columns is missing so
                        # we're not going to be able to work with the database.
                        ignore_row = True
                        break
                    continue
                value = row[c_index].value

                if not value and c.primary:
                    # The primary key is incomplete.
                    ignore_row = True
                    break

                xl_record[c.xl_name] = value

            if ignore_row or not xl_record:
                continue

            yield xl_record

    def find_db_rec(
        self,
        session: "Session",
        xl_rec: Dict[str, Any],
        is_db_pk: Callable[[Any], bool],
    ) -> "T | None":
        """Locate the corresponding database record for an Excel row.

        Implementations typically use the table's primary columns to build a
        lookup query.

        Args:
            session: SQLAlchemy session used to query the database.
            xl_rec: Excel row dictionary mapping column names to values.
            is_db_pk: a function that can determine if the value is a
                is a database primary key (True) or a temporary key that
                will be replaced by the true value in the insertion process.
                If this function returns False for any primary key value the
                record will be considered to be a new record.

        Returns:
            The matching database record, or `None` if no match is found.
        """
        raise NotImplementedError

    def create_new_db_record(
        self, session: "Session", xl_rec: Dict[str, Any]
    ) -> T:
        """Create a new database record.

        Note that after this call each column in turn will get a chance to
        update this record.

        Args:
            session: SQLAlchemy session used for persistence and related
                lookups.
            xl_rec: Excel row dictionary mapping column names to values.

        Returns:
            The newly created database record instance.
        """
        raise NotImplementedError

    def apply_xl_to_db(
        self, session: "Session", db_rec: T, xl_rec: Dict[str, Any]
    ):
        """Apply an Excel row dictionary to a database record.

        This delegates to each column's `XlColumn.apply_xl_to_db()` with the
        corresponding value from `xl_rec` (or `None` if missing).

        Args:
            session: SQLAlchemy session used for lookups and persistence.
            db_rec: Database record to update.
            xl_rec: Excel row dictionary mapping column names to values.
        """
        for c in self.columns:
            c.apply_xl_to_db(session, db_rec, xl_rec.get(c.xl_name, None))
