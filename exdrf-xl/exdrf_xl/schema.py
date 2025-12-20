from typing import TYPE_CHECKING

from attrs import define, field
from openpyxl import Workbook

if TYPE_CHECKING:
    from exdrf_al.connection import DbConn
    from sqlalchemy.orm import Session

    from .table import XlTable


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
        pass

    def after_export(self, wb: "Workbook", session: "Session"):
        pass
