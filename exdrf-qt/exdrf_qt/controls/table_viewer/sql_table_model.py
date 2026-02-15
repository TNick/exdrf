"""Read-only table model that loads rows from a SQL table."""

import logging
from typing import TYPE_CHECKING, Any, List, Optional

from PyQt5.QtCore import QAbstractTableModel, QModelIndex, Qt
from sqlalchemy import MetaData, Table, select

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)
VERBOSE = 10


class SqlTableModel(QAbstractTableModel):
    """Simple read-only model loading rows from a table.

    Stores raw values internally; returns stringified values for display.

    Attributes:
        _headers: Column names, in column order.
        _rows: Table data cached as lists of raw values.
    """

    # Private attributes
    _headers: List[str]
    _rows: List[List[Any]]

    def __init__(
        self,
        *,
        engine: "Engine",
        schema: Optional[str],
        table: str,
        limit: int = 10000,
    ) -> None:
        """Initialize the table model and load initial data.

        Args:
            engine: SQLAlchemy engine to query.
            schema: Optional schema name.
            table: Table name to read.
            limit: Limit number of rows loaded initially.
        """
        super().__init__()
        self._headers = []
        self._rows = []
        self._load(engine, schema, table, limit)

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
                logger.log(1, "SqlTableModel.data: %s", e, exc_info=True)
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

    def raw_headers(self) -> List[str]:
        """Return a copy of the column headers list."""
        return list(self._headers)

    def raw_row(self, row: int) -> Optional[List[Any]]:
        """Return the raw row values for a given row index, if present."""
        if 0 <= row < len(self._rows):
            return self._rows[row]
        return None

    def _load(
        self, engine: "Engine", schema: Optional[str], table: str, limit: int
    ) -> None:
        """Load headers and initial rows into memory.

        Args:
            engine: SQLAlchemy engine.
            schema: Optional schema.
            table: Table name.
            limit: Row limit for the preview.
        """
        logger.log(
            VERBOSE,
            "SqlTableModel: load table=%s schema=%s limit=%s",
            table,
            schema,
            limit,
        )
        meta = MetaData()
        t = Table(table, meta, autoload_with=engine, schema=schema)
        self._headers = [c.name for c in t.columns]
        stmt = select(t)
        if limit > 0:
            stmt = stmt.limit(limit)
        with engine.connect() as conn:
            rs = conn.execute(stmt)
            for row in rs:
                mapping = row._mapping  # SQLAlchemy RowMapping view
                self._rows.append([mapping[h] for h in self._headers])
        logger.log(
            VERBOSE,
            "SqlTableModel: loaded rows=%d cols=%d",
            len(self._rows),
            len(self._headers),
        )
