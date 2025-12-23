from typing import TYPE_CHECKING, Any, Callable, Sequence, TypeAlias

from attrs import define, field
from openpyxl import Workbook, load_workbook
from sqlalchemy.exc import DataError

if TYPE_CHECKING:
    from exdrf_al.connection import DbConn
    from openpyxl.worksheet.table import Table
    from sqlalchemy.orm import Session

    from .table import XlTable


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

    def export_to_file(self, db: "DbConn", path: str):
        """Exports the content of the selected tables to an Excel file.

        Args:
            db: Database connection used to create a session for exporting.
            path: Output `.xlsx` file path.
        """
        wb = Workbook()
        with db.same_session() as session:
            self.before_export(wb, session)
            for table in self.tables:
                sheet = wb.create_sheet(title=table.sheet_name[0:31])
                table.write_to_sheet(sheet, session)
            self.after_export(wb, session)
        wb.calculation.fullCalcOnLoad = True  # type: ignore
        wb.save(path)

    def import_from_file(
        self,
        db: "DbConn",
        path: str,
        validate_changes: (
            Callable[[Sequence[TableChanges]], bool] | None
        ) = None,
    ):
        """Imports data from an Excel file and applies it to the database.

        This method reads each configured `XlTable` from the workbook, compares
        Excel rows to database rows using `XlTable.find_db_rec()`, and then
        applies changes using `XlTable.apply_xl_to_db()`. New rows are created
        via `XlTable.create_new_db_record()`.

        Args:
            db: Database connection used to create a session for import.
            path: Input `.xlsx` file path.
            validate_changes: Optional callable that receives the collected
                changes and returns `True` if they should be applied.

                The collected changes are a sequence of `(table, new_records,
                old_records)` tuples where:
                - `table` is the `XlTable` instance
                - `new_records` is a list of Excel row dicts
                - `old_records` is a list of `(db_record, excel_row_dict)` pairs

                If `None`, changes are applied without validation.
        """
        wb = load_workbook(filename=path, read_only=False, data_only=True)
        with db.same_session() as session:
            changes: SchemaChanges = []
            for table in self.tables:
                ws = wb[table.sheet_name]
                ws_table: "Table" = ws.tables[table.xl_name]
                new_records = []
                old_records = []
                for xl_rec in table.iter_excel_table(ws, ws_table):
                    try:
                        db_rec = table.find_db_rec(session, xl_rec)
                    except DataError:
                        # An invalid value for the key signifies that the
                        # record is new.
                        db_rec = None
                    if db_rec:
                        old_records.append((db_rec, xl_rec))
                    else:
                        new_records.append(xl_rec)

                if old_records or new_records:
                    changes.append((table, new_records, old_records))

            if validate_changes is None or validate_changes(changes):
                for table, new_records, old_records in changes:
                    for db_rec, xl_rec in old_records:
                        table.apply_xl_to_db(session, db_rec, xl_rec)
                    for xl_rec in new_records:
                        db_rec = table.create_new_db_record(session, xl_rec)
                        table.apply_xl_to_db(session, db_rec, xl_rec)

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
