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
from exdrf_xl.ingest.update_excel_with_allocated_ids import (
    update_excel_with_allocated_ids,
)
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
        wb: Any,
        plan: ImportPlan,
        placeholder_to_id: dict[tuple[str, str], int],
        *,
        path: str | None = None,
        is_db_pk: Callable[[Any], bool] | None = None,
    ) -> None:
        """Update an Excel file with allocated database IDs.

        This method updates the workbook in-place, replacing temporary
        placeholder IDs (e.g., "x1", "x2") with the actual integer IDs allocated
        by the database during import.

        Args:
            wb: Workbook to update (must be provided, already loaded).
            plan: Import plan that was applied.
            placeholder_to_id: Mapping from (table_name, placeholder_string) to
                allocated integer ID.
            path: Optional path to save the workbook to. If provided, the
                workbook will be saved and backups rotated. If None, updates are
                made in memory only.
            is_db_pk: Predicate used to determine DB IDs. Defaults to
                `default_is_db_pk`.
        """
        update_excel_with_allocated_ids(
            wb, plan, placeholder_to_id, path=path, is_db_pk=is_db_pk
        )
