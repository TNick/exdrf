from __future__ import annotations

import logging
import os.path
from typing import Any, Callable, TypeAlias

from attrs import define, field
from exdrf_util.rotate_backups import rotate_backups
from openpyxl import Workbook, load_workbook  # type: ignore[import]
from sqlalchemy.orm import Session

from exdrf_xl.ingest.apply_import_plan import apply_import_plan
from exdrf_xl.ingest.import_plan import ImportPlan
from exdrf_xl.ingest.plan_import_from_file import plan_import_from_file
from exdrf_xl.ingest.tools import default_is_db_pk
from exdrf_xl.utils.col_widths import read_column_widths_from_existing_file

from .table import XlTable

logger = logging.getLogger(__name__)


XlRecord: TypeAlias = dict[str, Any]
DbRecord: TypeAlias = Any
OldRecord: TypeAlias = tuple[DbRecord, XlRecord]
TableChanges: TypeAlias = tuple["XlTable[Any]", list[XlRecord], list[OldRecord]]
SchemaChanges: TypeAlias = list[TableChanges]


@define
class XlSchema:
    """Describes the mapping between a database schema and an
    Excel workbook.

    Attributes:
        tables: The tables in the schema, exported in order.
    """

    tables: list["XlTable"] = field(factory=list, repr=False)

    def export_to_file(self, db: Any, path: str, max_backups: int = 10):
        """Exports the content of the selected tables to an Excel file.

        Args:
            db: Database connection used to create a session for exporting.
            path: Output `.xlsx` file path.
        """
        widths_map = {}
        if os.path.exists(path):
            try:
                wb = load_workbook(path, data_only=True)
                widths_map = read_column_widths_from_existing_file(wb)
            except Exception:
                logger.error(
                    "Failed to retrieve information from previous version",
                    exc_info=True,
                )
            rotate_backups(path, max_backups=max_backups)

        wb = Workbook()
        with db.same_session() as session:
            self.before_export(wb, session)
            for table in self.tables:
                sheet = wb.create_sheet(title=table.sheet_name[0:31])
                table.write_to_sheet(
                    sheet, session, col_widths=widths_map.get(table.xl_name, {})
                )
            self.after_export(wb, session)
        wb.calculation.fullCalcOnLoad = True  # type: ignore
        wb.save(path)

    def import_from_file(
        self,
        db: Any,
        path: str,
        *,
        accept_new: bool = True,
        accept_modified: bool = True,
        is_db_pk: Callable[[Any], bool] | None = None,
    ):
        """Import data from an Excel file into the database.

        This is a non-interactive apply step; review/selection should be done
        by calling `plan_import_from_file()` + `render_review_html()` first.

        Args:
            db: Database connection used to create a session for import.
            path: Input `.xlsx` file path.
            accept_new: Whether to insert new rows.
            accept_modified: Whether to apply modifications to existing rows.
            is_db_pk: Optional predicate used during planning. Defaults to
                `default_is_db_pk`.
        """
        plan = plan_import_from_file(self, db, path, is_db_pk=is_db_pk)
        apply_import_plan(
            db,
            plan,
            accept_new=accept_new,
            accept_modified=accept_modified,
            is_db_pk=is_db_pk,
        )

    def has_table(self, name: str) -> bool:
        """Returns True if the schema has a table with the given name.

        Args:
            name: Structured table name (`XlTable.xl_name`).
        """
        return any(table.xl_name == name for table in self.tables)

    def get_table(self, name: str) -> "XlTable | None":
        """Returns the table with the given name.

        Args:
            name: Structured table name (`XlTable.xl_name`).

        Returns:
            The matching table instance, or `None` if it does not exist.
        """
        for table in self.tables:
            if table.xl_name == name:
                return table
        return None

    def before_export(self, wb: "Workbook", session: "Session"):
        """Hook called once before exporting tables.

        Args:
            wb: Workbook that will be written to disk.
            session: SQLAlchemy session used for export queries.
        """

    def after_export(self, wb: "Workbook", session: "Session"):
        """Hook called once after exporting tables.

        Args:
            wb: Workbook that will be written to disk.
            session: SQLAlchemy session used for export queries.
        """

    def update_excel_with_allocated_ids(
        self,
        path: str,
        plan: ImportPlan,
        placeholder_to_id: dict[tuple[str, str], int],
        *,
        is_db_pk: Callable[[Any], bool] | None = None,
        wb: Any | None = None,
    ) -> None:
        """Update an Excel file with allocated database IDs.

        This method updates the Excel file in-place, replacing temporary
        placeholder IDs (e.g., "x1", "x2") with the actual integer IDs allocated
        by the database during import.

        Args:
            path: Path to the Excel file to update (used if `wb` is None).
            plan: Import plan that was applied.
            placeholder_to_id: Mapping from (table_name, placeholder_string) to
                allocated integer ID.
            is_db_pk: Predicate used to determine DB IDs. Defaults to
                `default_is_db_pk`.
            wb: Optional workbook to update. If provided, `path` is only used
                for saving. If None, the workbook is loaded from `path`.
        """
        from openpyxl.utils.cell import range_boundaries  # type: ignore[import]

        if not placeholder_to_id:
            return

        is_db_pk = is_db_pk or default_is_db_pk
        should_close = False
        if wb is None:
            wb = load_workbook(filename=path, read_only=False, data_only=True)
            should_close = True

        try:
            for table_plan in plan.tables:
                table = table_plan.table
                ws_name = table.sheet_name[0:31]
                if ws_name not in wb.sheetnames:
                    continue
                ws = wb[ws_name]

                ws_table = ws.tables.get(table.xl_name)
                if ws_table is None:
                    continue

                if not ws_table.ref:
                    continue

                # Get table boundaries.
                min_col, min_row, max_col, max_row = range_boundaries(
                    ws_table.ref
                )
                if (
                    min_col is None
                    or min_row is None
                    or max_col is None
                    or max_row is None
                ):
                    continue

                # Exclude Excel "Totals" rows when present.
                totals_row_count = int(
                    getattr(ws_table, "totalsRowCount", 0) or 0
                )
                if totals_row_count:
                    max_row = max(min_row, max_row - totals_row_count)

                # Build column name to index mapping.
                header_row = next(
                    ws.iter_rows(
                        min_row=min_row,
                        max_row=min_row,
                        min_col=min_col,
                        max_col=max_col,
                    )
                )
                col_name_to_idx: dict[str, int] = {}
                for cell in header_row:
                    col_name = str(cell.value) if cell.value else ""
                    if col_name:
                        try:
                            ws_col_idx = table._get_ws_col_idx(cell)
                            col_idx = ws_col_idx - min_col
                            col_name_to_idx[col_name] = col_idx
                        except (TypeError, AttributeError):
                            continue

                # Build column objects lookup.
                col_by_name: dict[str, Any] = {}
                for c in table.get_included_columns():
                    col_by_name[c.xl_name] = c

                # Track which rows had placeholders and need updates.
                rows_to_update: dict[int, dict[str, int]] = {}
                # Map: data row index -> {column_name: new_id}

                # Iterate through all data rows and check for placeholders.
                data_row_idx = 0
                for row in ws.iter_rows(
                    min_row=min_row + 1,
                    max_row=max_row,
                    min_col=min_col,
                    max_col=max_col,
                ):
                    row_updates: dict[str, int] = {}
                    for col_name, col_idx in col_name_to_idx.items():
                        if col_idx >= len(row):
                            continue
                        cell = row[col_idx]
                        value = cell.value

                        # Skip if not a string (placeholders are strings).
                        if not isinstance(value, str):
                            continue

                        placeholder = value.strip()
                        if not placeholder:
                            continue

                        col = col_by_name.get(col_name)
                        if col is None:
                            continue

                        # Check if this is a primary key column with a
                        # placeholder.
                        if col.primary and col_name == "id":
                            placeholder_key = (table.xl_name, placeholder)
                            new_id = placeholder_to_id.get(placeholder_key)
                            if new_id is not None:
                                row_updates[col_name] = new_id
                                continue

                        # Check if this is a foreign key column with a
                        # placeholder.
                        fk_table_name = getattr(col, "fk_table", None)
                        if fk_table_name:
                            placeholder_key = (fk_table_name, placeholder)
                            new_id = placeholder_to_id.get(placeholder_key)
                            if new_id is not None:
                                row_updates[col_name] = new_id

                    if row_updates:
                        rows_to_update[data_row_idx] = row_updates
                    data_row_idx += 1

                # Apply updates to cells.
                for data_row_idx, updates in rows_to_update.items():
                    excel_row = min_row + 1 + data_row_idx
                    for col_name, new_id in updates.items():
                        col_idx_opt = col_name_to_idx.get(col_name)
                        if col_idx_opt is None:
                            continue
                        col_idx = col_idx_opt
                        cell = ws.cell(
                            row=excel_row,
                            column=min_col + col_idx + 1,
                        )
                        # Skip merged cells (they are read-only).
                        # Check by class name to avoid import dependency.
                        if (
                            hasattr(cell, "__class__")
                            and cell.__class__.__name__ == "MergedCell"
                        ):
                            continue
                        # Type checker may complain, but we've checked above.
                        cell.value = new_id  # type: ignore[assignment]

            # Rotate backups before saving.
            from exdrf_util.rotate_backups import (  # type: ignore[import]
                rotate_backups,
            )

            rotate_backups(path)

            wb.save(path)
        finally:
            if should_close:
                wb.close()
