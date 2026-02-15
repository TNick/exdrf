"""Read-only table model that loads rows from a SQL table.

When used with the table viewer's editing mode, supports setData to persist
cell changes via UPDATE statements (requires a primary key).
"""

import logging
from datetime import date, datetime
from typing import TYPE_CHECKING, Any, List, Optional, Tuple

from PyQt5.QtCore import QAbstractTableModel, QModelIndex, Qt
from sqlalchemy import MetaData, Table, select, update

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)
VERBOSE = 10


def get_foreign_key_columns(
    engine: "Engine",
    schema: Optional[str],
    table_name: str,
) -> List[Tuple[str, str, List[str]]]:
    """Return FK-based join options for a table.

    Reflects the table and each target table to list (fk_column, target_table,
    target_non_pk_column_names). Target tables are reflected to exclude
    primary key columns from the list.

    Args:
        engine: SQLAlchemy engine.
        schema: Optional schema (None for SQLite).
        table_name: Base table name.

    Returns:
        List of (fk_column, target_table_name, [target_col, ...]).
    """
    effective_schema = None if engine.dialect.name == "sqlite" else schema
    meta = MetaData()
    base_t = Table(
        table_name, meta, autoload_with=engine, schema=effective_schema
    )
    out: List[Tuple[str, str, List[str]]] = []
    for fk in base_t.foreign_keys:
        # fk.parent is the column in base_t, fk.column is in target table
        fk_col = fk.parent.name
        target_table = fk.column.table.name
        target_schema = (
            getattr(fk.column.table, "schema", None) or effective_schema
        )
        target_meta = MetaData()
        try:
            target_t = Table(
                target_table,
                target_meta,
                autoload_with=engine,
                schema=target_schema,
            )
        except Exception:
            logger.debug(
                "get_foreign_key_columns: could not reflect target %s",
                target_table,
                exc_info=True,
            )
            continue
        pk_names = {c.name for c in target_t.primary_key.columns}
        non_pk = [c.name for c in target_t.columns if c.name not in pk_names]
        if non_pk:
            out.append((fk_col, target_table, non_pk))
    return out


class SqlTableModel(QAbstractTableModel):
    """Simple table model loading rows from a SQL table.

    Stores raw values internally; returns stringified values for display.
    Supports optional editing via setData when the table has a primary key.

    Attributes:
        _headers: Column names, in column order.
        _rows: Table data cached as lists of raw values.
        _column_types: SQLAlchemy type for each column (from reflection).
        _primary_key_names: Column names that form the primary key.
        _engine: Engine used for load and updates.
        _schema: Schema name (None for SQLite).
        _table: Table name.
        _table_obj: Reflected Table object for UPDATE statements.
        _column_nullable: Whether each column accepts NULL (from reflection).
        _limit: Row limit used for load (for reload when adding join columns).
        _base_column_count: Number of base table columns (joined columns are
            read-only and follow).
    """

    # Private attributes
    _headers: List[str]
    _rows: List[List[Any]]
    _column_types: List[Any]
    _column_nullable: List[bool]
    _primary_key_names: List[str]
    _engine: "Engine"
    _schema: Optional[str]
    _table: str
    _table_obj: Any
    _limit: int
    _base_column_count: int

    def __init__(
        self,
        *,
        engine: "Engine",
        schema: Optional[str],
        table: str,
        limit: int = 1000000,
        extra_columns: Optional[List[Tuple[str, str, str]]] = None,
    ) -> None:
        """Initialize the table model and load initial data.

        Args:
            engine: SQLAlchemy engine to query.
            schema: Optional schema name.
            table: Table name to read.
            limit: Limit number of rows loaded initially.
            extra_columns: Optional list of (fk_column, target_table,
                target_column) to add as read-only joined columns.
        """
        super().__init__()
        self._headers = []
        self._rows = []
        self._column_types = []
        self._column_nullable = []
        self._primary_key_names = []
        self._engine = engine
        self._schema = schema or ""
        self._table = table
        self._table_obj = None  # Set in _load
        self._limit = limit
        self._base_column_count = 0
        self._load(engine, schema, table, limit, extra_columns or [])

    def rowCount(
        self, parent: QModelIndex = QModelIndex()
    ) -> int:  # noqa: N802
        """Number of rows in the table model.

        Args:
            parent: Required by Qt; unused for flat models.

        Returns:
            Number of records (may be truncated by limit).
        """
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(
        self, parent: QModelIndex = QModelIndex()
    ) -> int:  # noqa: N802
        """Number of columns.

        Args:
            parent: Required by Qt; unused.

        Returns:
            Number of columns.
        """
        return 0 if parent.isValid() else len(self._headers)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        """Cell data for requested index/role.

        Args:
            index: Model index.
            role: Qt role (Display/Edit).

        Returns:
            The textual representation for display/edit roles.
        """
        if not index.isValid():
            return None
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            try:
                val = self._rows[index.row()][index.column()]
                if val is None:
                    return ""
                return str(val)
            except Exception as e:
                logger.log(VERBOSE, "SqlTableModel.data: %s", e, exc_info=True)
                return ""
        return None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ):
        """Header values for the view.

        Args:
            section: Section index.
            orientation: Horizontal or Vertical.
            role: Qt role (Display role is used).
        """
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            if 0 <= section < len(self._headers):
                return self._headers[section]
        else:
            return section + 1
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        """Return item flags for the given index.

        Args:
            index: Model index.

        Returns:
            Item flags including ItemIsEditable so the view can open editors
            when edit triggers are enabled; the delegate controls which
            columns actually get editors.
        """
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags  # type: ignore[return-value]
        base = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if index.column() < self._base_column_count:
            base = base | Qt.ItemFlag.ItemIsEditable
        return base  # type: ignore[return-value]

    def get_limit(self) -> int:
        """Return the row limit used for loading (for reload with new joins)."""
        return self._limit

    def raw_headers(self) -> List[str]:
        """Return a copy of the column headers list."""
        return list(self._headers)

    def raw_column_type(self, column_index: int) -> Any:
        """Return the SQLAlchemy type for the column at the given index.

        Args:
            column_index: Zero-based column index.

        Returns:
            The column's type object from reflection, or None if out of range.
        """
        if 0 <= column_index < len(self._column_types):
            return self._column_types[column_index]
        return None

    def raw_column_nullable(self, column_index: int) -> bool:
        """Return whether the column at the given index accepts NULL.

        Args:
            column_index: Zero-based column index.

        Returns:
            True if the column is nullable; False otherwise.
        """
        if 0 <= column_index < len(self._column_nullable):
            return self._column_nullable[column_index]
        return False

    def raw_row(self, row: int) -> Optional[List[Any]]:
        """Return the raw row values for a given row index, if present."""
        if 0 <= row < len(self._rows):
            return self._rows[row]
        return None

    def setData(
        self,
        index: QModelIndex,
        value: Any,
        role: int = Qt.ItemDataRole.EditRole,
    ) -> bool:
        """Persist a cell value to the database and update the cache.

        Runs an UPDATE using the primary key for the row. Fails if the
        table has no primary key. Converts value according to column type.

        Args:
            index: Model index of the cell.
            value: New value (from editor; may be str, int, bool, date, etc.).
            role: Must be EditRole for the update to run.

        Returns:
            True if the update succeeded; False otherwise.
        """
        if role != Qt.ItemDataRole.EditRole or not index.isValid():
            return False
        if not self._primary_key_names:
            logger.log(
                VERBOSE,
                "SqlTableModel.setData: no primary key, cannot update",
            )
            return False
        row = index.row()
        col = index.column()
        if (
            row < 0
            or row >= len(self._rows)
            or col < 0
            or col >= self._base_column_count
        ):
            return False

        col_name = self._headers[col]
        try:
            converted = self._convert_value_for_column(col, value)
        except Exception as e:
            logger.debug(
                "SqlTableModel.setData: convert value for col %s: %s",
                col_name,
                e,
                exc_info=True,
            )
            return False

        current = self._rows[row][col]
        if converted == current:
            return True

        row_vals = self._rows[row]
        pk_vals = {
            self._headers[i]: row_vals[i]
            for i in range(len(self._headers))
            if self._headers[i] in self._primary_key_names
        }
        try:
            t = self._table_obj
            stmt = update(t).values(**{col_name: converted})
            for pk_name in self._primary_key_names:
                stmt = stmt.where(t.c[pk_name] == pk_vals[pk_name])
            with self._engine.begin() as conn:
                conn.execute(stmt)
        except Exception as e:
            logger.debug(
                "SqlTableModel.setData: UPDATE failed for %s: %s",
                col_name,
                e,
                exc_info=True,
            )
            return False

        self._rows[row][col] = converted
        self.dataChanged.emit(index, index, [role])
        return True

    def _convert_value_for_column(self, column_index: int, value: Any) -> Any:
        """Convert an editor value to the type expected by the column.

        For nullable columns, None or empty string is stored as NULL. For
        nullable text fields, empty string is stored as NULL in the database.

        Args:
            column_index: Column index.
            value: Value from the editor (often str from QLineEdit).

        Returns:
            Value suitable for the database (e.g. int, float, date, bool).
        """
        if value is None or (isinstance(value, str) and value.strip() == ""):
            if self.raw_column_nullable(column_index):
                return None
            return value
        col_type = self.raw_column_type(column_index)
        if col_type is None:
            return value

        type_name = type(col_type).__name__
        if type_name == "Boolean":
            if isinstance(value, bool):
                return value
            return str(value).strip().lower() in ("1", "true", "yes", "on")

        if type_name in ("Integer", "SmallInteger", "BigInteger"):
            if isinstance(value, int):
                return value
            return int(value)

        if type_name in ("Float", "Numeric", "DECIMAL"):
            if isinstance(value, (int, float)):
                return float(value)
            return float(value)

        if type_name == "Date":
            if isinstance(value, date):
                return value
            if isinstance(value, datetime):
                return value.date()
            return datetime.strptime(str(value).strip(), "%Y-%m-%d").date()

        if type_name in ("DateTime", "TIMESTAMP"):
            if isinstance(value, datetime):
                return value
            if isinstance(value, date):
                return datetime.combine(value, datetime.min.time())
            return datetime.fromisoformat(
                str(value).strip().replace("Z", "+00:00")
            )

        return value

    def _default_extra_loader(
        self,
        t: "Table",
        fk_col: str,
        target_table_name: str,
        target_col: str,
        engine: "Engine",
        effective_schema: Optional[str],
        stmt: Any,
        extra_headers: List[str],
    ) -> Any:
        target_meta = MetaData()
        target_t = Table(
            target_table_name,
            target_meta,
            autoload_with=engine,
            schema=effective_schema,
        )

        # Get the set of primary key columns from the foreign key table.
        target_pk_cols = list(target_t.primary_key.columns)
        if not target_pk_cols:
            return

        target_pk = target_pk_cols[0].name
        stmt = stmt.outerjoin(target_t, t.c[fk_col] == target_t.c[target_pk])
        label = "%s_%s" % (target_table_name, target_col)
        stmt = stmt.add_columns(target_t.c[target_col].label(label))
        extra_headers.append(label)

        return stmt

    def _load(
        self,
        engine: "Engine",
        schema: Optional[str],
        table: str,
        limit: int,
        extra_columns: List[Tuple[str, str, str]],
    ) -> None:
        """Load headers and initial rows into memory, with optional JOINs.

        Args:
            engine: SQLAlchemy engine.
            schema: Optional schema.
            table: Table name.
            limit: Row limit for the preview.
            extra_columns: List of (fk_column, target_table, target_column).
        """
        # SQLite does not support arbitrary schema names; it only uses None,
        # "main", or attached database names. Passing a non-existent schema
        # (e.g. a config id) causes "unknown database" on PRAGMA table_xinfo.
        effective_schema = None if engine.dialect.name == "sqlite" else schema
        logger.log(
            VERBOSE,
            "SqlTableModel: load table=%s schema=%s limit=%s",
            table,
            effective_schema,
            limit,
        )
        meta = MetaData()
        t = Table(table, meta, autoload_with=engine, schema=effective_schema)
        self._table_obj = t
        self._schema = effective_schema
        base_headers = [c.name for c in t.columns]
        self._column_types = [c.type for c in t.columns]
        self._column_nullable = [bool(c.nullable) for c in t.columns]
        self._primary_key_names = [c.name for c in t.primary_key.columns]
        self._base_column_count = len(base_headers)

        # Build select: base columns + optional joined columns
        stmt = select(*[t.c[h] for h in base_headers])
        extra_headers: List[str] = []
        for fk_col, target_table_name, target_col in extra_columns:
            # Check if the user wants to use a custom loader for the
            # extra column.
            if callable(target_col):
                stmt = target_col(
                    t,
                    fk_col,
                    target_table_name,
                    self,
                    engine,
                    effective_schema,
                    stmt,
                    extra_headers,
                )
            else:
                stmt = self._default_extra_loader(
                    t,
                    fk_col,
                    target_table_name,
                    target_col,
                    engine,
                    effective_schema,
                    stmt,
                    extra_headers,
                )

        self._headers = base_headers + extra_headers
        self._column_types.extend([None] * len(extra_headers))
        self._column_nullable.extend([True] * len(extra_headers))

        if limit > 0:
            stmt = stmt.limit(limit)

        with engine.connect() as conn:
            rs = conn.execute(stmt)
            for row in rs:
                self._rows.append([row[i] for i in range(len(self._headers))])

        logger.log(
            VERBOSE,
            "SqlTableModel: loaded rows=%d cols=%d",
            len(self._rows),
            len(self._headers),
        )
