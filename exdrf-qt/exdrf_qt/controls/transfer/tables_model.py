"""Table list model with row counts for source/destination panes.

Counts are loaded synchronously in the main thread when the connection
changes; both models are updated by the transfer widget.
"""

import logging
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from exdrf_al.connection import DbConn
from PyQt5.QtCore import QAbstractTableModel, QModelIndex, Qt, pyqtSignal
from PyQt5.QtGui import QBrush, QColor, QFont
from sqlalchemy import (
    MetaData,
    Table,
    func,
    inspect,
    literal,
    select,
    union_all,
)

from exdrf_qt.context_use import QtUseContext
from exdrf_qt.controls.transfer.tbl_row import TblRow

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection

    from exdrf_qt.context import QtContext

logger = logging.getLogger(__name__)
VERBOSE = 1


class TablesModel(QAbstractTableModel, QtUseContext):
    """List model with 2 columns: table name and counts (src/dst).

    The instance is parameterized with which side it represents ("src" or
    "dst"). Counts are displayed as "a (b)" where a is the count for the
    current connection and b is the difference vs the other side. Counts
    are loaded synchronously in the main thread when the widget runs
    counting after a connection change.

    Attributes:
        ctx: The application context.

    Private Attributes:
        _side: Either "src" or "dst"; informational only.
        _src_conn: Source connection used to compute counts.
        _dst_conn: Destination connection used to compute counts.
        _rows: Backing storage with table entries.
    """

    count_failed = pyqtSignal(str)

    # Public attributes
    ctx: "QtContext"

    # Private attributes
    _side: str
    _src_conn: Optional["DbConn"]
    _dst_conn: Optional["DbConn"]
    _rows: List[TblRow]

    def __init__(
        self,
        *,
        ctx,
        side: str,
        src_conn: Optional[DbConn] = None,
        dst_conn: Optional[DbConn] = None,
    ) -> None:
        """Initialize the model.

        Args:
            ctx: The application context.
            side: The side of the model ("src" or "dst").
            src_conn: The source connection or None.
            dst_conn: The destination connection or None.
        """
        super().__init__()
        self.ctx = ctx
        assert side in ("src", "dst")
        self._side = side
        self._src_conn = src_conn
        self._dst_conn = dst_conn
        self._rows = []
        logger.log(VERBOSE, "TablesModel: initialized side=%s", side)

    # Public API
    def set_connections(
        self, src: Optional["DbConn"], dst: Optional["DbConn"]
    ) -> None:
        """Set the source and destination connections.

        Args:
            src: The source connection or None.
            dst: The destination connection or None.
        """
        self._src_conn = src
        self._dst_conn = dst

    def refresh(self) -> None:
        """Rebuild the table list with names only; counts are filled by the
        widget via set_count after running synchronous counting.
        """
        self.beginResetModel()
        self._rows = []
        try:
            src_tables: List[str] = []
            if self._src_conn and self._src_conn.connect():
                assert self._src_conn.engine is not None
                ins = inspect(self._src_conn.engine)
                src_tables = ins.get_table_names(schema=self._src_conn.schema)

            for name in sorted(src_tables):
                self._rows.append(TblRow(name=name, cnt_src=None, cnt_dst=None))

            logger.log(VERBOSE, "TablesModel.refresh: rows=%d", len(self._rows))
        except Exception as e:
            logger.error("Failed to refresh tables: %s", e, exc_info=True)
        finally:
            self.endResetModel()

    # Model API
    def rowCount(
        self, parent: QModelIndex = QModelIndex()
    ) -> int:  # noqa: N802
        """Number of rows in the model.

        Args:
            parent: Required by Qt; unused for flat models.

        Returns:
            Count of table entries.
        """
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(
        self, parent: QModelIndex = QModelIndex()
    ) -> int:  # noqa: N802
        """Number of columns in the model.

        Args:
            parent: Required by Qt; unused for flat models.

        Returns:
            Always 2 (name, counts).
        """
        return 0 if parent.isValid() else 2

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ):
        """Header data for given section/orientation.

        Args:
            section: Section index.
            orientation: Horizontal or Vertical.
            role: Qt data role.

        Returns:
            The header text for display role.
        """
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return [
                self.t("tr.tables.name", "Table"),
                self.t("tr.tables.counts", "Rows"),
            ][section]
        return section + 1

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        """Cell data for requested index/role.

        Args:
            index: The model index.
            role: The Qt data role (defaults to DisplayRole).

        Returns:
            An appropriate value for the role, or None.
        """
        if not index.isValid():
            return None

        row = self._rows[index.row()]
        is_pending = (self._side == "src" and row.cnt_src is None) or (
            self._side == "dst" and row.cnt_dst is None
        )
        cur = row.cnt_src if self._side == "src" else row.cnt_dst
        other = row.cnt_dst if self._side == "src" else row.cnt_src

        if role == Qt.ItemDataRole.FontRole:
            if is_pending and index.column() == 1:
                f = QFont()
                f.setItalic(True)
                return f
            return None
        if role == Qt.ItemDataRole.EditRole:
            if index.column() == 1:
                if cur is None:
                    return None
                return int(cur)
            return None
        if role == Qt.ItemDataRole.ForegroundRole:
            # Pending styling (dark gray) for counts column
            if index.column() == 1 and is_pending:
                return QBrush(QColor(Qt.GlobalColor.darkGray))
            # Color rules for counts column when both connections exist and
            # values are known
            if index.column() == 1 and cur is not None:
                # Require both source and destination connections present
                if self._src_conn is None or self._dst_conn is None:
                    return None
                if other is None:
                    return None
                # Missing table on other side or error => red
                if int(other) < 0:
                    return QBrush(QColor(Qt.GlobalColor.red))
                # Both sides known and valid => delta-based coloring
                try:
                    a = int(cur)
                    b = int(other)
                except Exception:
                    return None
                if a > b:
                    return QBrush(QColor(Qt.GlobalColor.darkGreen))
                if a < b:
                    return QBrush(QColor(Qt.GlobalColor.blue))
                # Equal => default (black)
                return QBrush(QColor(Qt.GlobalColor.black))
            return None
        if role == Qt.ItemDataRole.DisplayRole:
            if index.column() == 0:
                return row.name
            if index.column() == 1:
                if cur is None:
                    return ""
                # Current count value (a)
                if cur < 0:
                    return "-"
                a = int(cur)
                # If both connections exist and both sides are known and valid,
                # append (+b) or (-b)
                if (
                    self._src_conn is not None
                    and self._dst_conn is not None
                    and other is not None
                    and other >= 0
                ):
                    b = int(other)
                    delta = a - b
                    if delta > 0:
                        return f"{a} (+{delta})"
                    if delta < 0:
                        return f"{a} ({delta})"
                    # Equal: no (b) part
                    return str(a)
                # If other side missing (negative), just show 'a'
                return str(a)
        return None

    # Public count API for the widget
    def set_count(self, row: int, side: str, value: int) -> None:
        """Set the count for one side at the given row and emit dataChanged.

        Args:
            row: Row index.
            side: "src" or "dst".
            value: Count value (use -1 for error/missing).
        """
        if row < 0 or row >= len(self._rows):
            return
        assert side in ("src", "dst")
        if side == "src":
            self._rows[row].cnt_src = value
        else:
            self._rows[row].cnt_dst = value
        left = self.index(row, 1)
        right = self.index(row, 1)
        self.dataChanged.emit(
            left,
            right,
            [
                Qt.ItemDataRole.DisplayRole,
                Qt.ItemDataRole.EditRole,
                Qt.ItemDataRole.ForegroundRole,
                Qt.ItemDataRole.FontRole,
            ],
        )

    def count_table(self, conn: Optional["DbConn"], table: str) -> int:
        """Run COUNT(*) for a table using the given connection (main thread).

        Args:
            conn: The database connection or None.
            table: The table name.

        Returns:
            Row count, or -1 on error or if conn is None.
        """
        if conn is None:
            return -1
        cnt = self._count_for(conn, table)
        return cnt if cnt is not None else -1

    # Helpers
    def table_name(self, row: int) -> Optional[str]:
        """Get the table name at a given row.

        Args:
            row: Row index.

        Returns:
            Table name or None if out of bounds.
        """
        if 0 <= row < len(self._rows):
            return self._rows[row].name
        return None

    @staticmethod
    def _count_error_is_fatal(exc: Exception) -> bool:
        """Return True if this count error should abort counting for all tables.

        Non-fatal (return False): table not found, missing object; we continue
        with other tables. Fatal (return True): permission denied, schema
        access; we abort and show toast once per connection.
        """
        msg = str(exc).lower()
        if "no such table" in msg or "does not exist" in msg:
            return False
        if "permission denied" in msg or "insufficient privilege" in msg:
            return True
        try:
            if getattr(exc, "pgcode", None) == "42501":
                return True
        except Exception as e:
            logger.log(VERBOSE, "Checking pgcode failed: %s", e, exc_info=True)
        return False

    def _count_with_connection(
        self, db: "Connection", schema: str, table: str
    ) -> Tuple[Optional[int], Optional[str], bool]:
        """Run COUNT(*) for a table using an existing connection
        (no reflection).

        SQLite does not support schema-qualified table names; schema is omitted
        for SQLite so the table name is not prefixed.

        Args:
            db: An open SQLAlchemy Connection (same thread).
            schema: Schema name (ignored for SQLite).
            table: Table name.

        Returns:
            (count, None, False) on success; (None, error_message, is_fatal)
            on failure. When is_fatal is True we abort counting and show toast.
        """
        try:
            # SQLite: do not use schema (no such table: schema.tablename)
            table_schema = (
                None
                if db.engine.dialect.name == "sqlite"
                else (schema if schema else None)
            )
            t = Table(table, MetaData(), schema=table_schema)
            cnt = db.scalar(select(func.count()).select_from(t))
            return (int(cnt or 0), None, False)
        except Exception as e:
            is_fatal = self._count_error_is_fatal(e)
            if is_fatal:
                logger.warning("Count failed for %s.%s: %s", schema, table, e)
            else:
                logger.log(
                    VERBOSE,
                    "Count skipped (table missing or not accessible) %s.%s: %s",
                    schema,
                    table,
                    e,
                )
            # Isolate failed query: roll back so next count runs in a new
            # transaction (e.g. PostgreSQL: "current transaction is aborted")
            try:
                db.rollback()
            except Exception as rb_e:
                logger.log(
                    VERBOSE,
                    "Rollback after count failure failed: %s",
                    rb_e,
                    exc_info=True,
                )
            return (None, str(e), is_fatal)

    def _count_for(self, conn: Optional["DbConn"], table: str) -> Optional[int]:
        """Synchronous count helper used where blocking is acceptable.

        Uses a single connection and no table reflection.

        Args:
            conn: The database connection.
            table: The table name.

        Returns:
            Row count or None if error.
        """
        if conn is None:
            return None

        engine = conn.connect()
        assert engine is not None
        try:
            with engine.connect() as db:
                cnt, _err, _fatal = self._count_with_connection(
                    db, conn.schema, table
                )
                return cnt
        except Exception as e:
            logger.warning("Count failed for %s.%s: %s", conn.schema, table, e)
            return None

    def _count_all_tables_with_connection(
        self,
        db: "Connection",
        schema: Optional[str],
        table_names: List[str],
    ) -> Dict[str, int]:
        """Run a single query that returns row counts for all tables.

        Builds UNION ALL of SELECT name, (SELECT COUNT(*) FROM schema.name)
        for each table. SQLite uses no schema.

        Args:
            db: An open SQLAlchemy Connection.
            schema: Schema name (None for SQLite).
            table_names: List of table names (from inspector, not user input).

        Returns:
            Dict mapping table name to count. Missing or failed tables are not
            in the dict (caller should treat as -1). On full query failure
            returns empty dict.
        """
        if not table_names:
            return {}
        dialect_name = db.engine.dialect.name
        use_schema = (
            None if dialect_name == "sqlite" else (schema if schema else None)
        )
        selects = []
        for name in table_names:
            t = Table(name, MetaData(), schema=use_schema)
            sub = select(func.count()).select_from(t).scalar_subquery()
            selects.append(
                select(literal(name).label("tname"), sub.label("cnt"))
            )
        stmt = union_all(*selects)
        try:
            result = db.execute(stmt)
            rows = result.all()
            return {row[0]: int(row[1] or 0) for row in rows}
        except Exception as e:
            logger.warning(
                "Count-all query failed for %s: %s",
                schema or "(no schema)",
                e,
                exc_info=True,
            )
            try:
                db.rollback()
            except Exception as rb_e:
                logger.log(
                    VERBOSE,
                    "Rollback after count-all failure: %s",
                    rb_e,
                    exc_info=True,
                )
            return {}

    def count_all_tables(
        self,
        conn: Optional["DbConn"],
        table_names: List[str],
    ) -> Dict[str, int]:
        """Run one query to get row counts for all tables.

        Args:
            conn: The database connection or None.
            table_names: List of table names to count.

        Returns:
            Dict mapping table name to count. On connection/query failure
            returns empty dict (caller should use -1 for missing keys).
        """
        if conn is None or not table_names:
            return {}
        engine = conn.connect()
        if engine is None:
            return {}
        try:
            with engine.connect() as db:
                return self._count_all_tables_with_connection(
                    db,
                    conn.schema or None,
                    table_names,
                )
        except Exception as e:
            logger.warning(
                "Count-all failed for %s: %s",
                conn.schema,
                e,
                exc_info=True,
            )
            return {}

    def invalidate_counts(self) -> None:
        """Clear all counts in this model; widget should run sync count after."""
        for r in self._rows:
            r.cnt_src = None
            r.cnt_dst = None
        if not self._rows:
            return
        top_left = self.index(0, 1)
        bottom_right = self.index(len(self._rows) - 1, 1)
        self.dataChanged.emit(
            top_left,
            bottom_right,
            [
                Qt.ItemDataRole.DisplayRole,
                Qt.ItemDataRole.EditRole,
                Qt.ItemDataRole.ForegroundRole,
                Qt.ItemDataRole.FontRole,
            ],
        )

    def invalidate_counts_side(self, clear_side: str) -> None:
        """Clear counts for one side only; widget runs sync count for that side.

        Args:
            clear_side: "src" or "dst".
        """
        assert clear_side in ("src", "dst")
        if not self._rows:
            return
        for r in self._rows:
            if clear_side == "src":
                r.cnt_src = None
            else:
                r.cnt_dst = None
        top_left = self.index(0, 1)
        bottom_right = self.index(len(self._rows) - 1, 1)
        self.dataChanged.emit(
            top_left,
            bottom_right,
            [
                Qt.ItemDataRole.DisplayRole,
                Qt.ItemDataRole.EditRole,
                Qt.ItemDataRole.ForegroundRole,
                Qt.ItemDataRole.FontRole,
            ],
        )
