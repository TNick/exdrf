"""Context object for one open table tab in the viewer."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from exdrf_qt.controls.table_viewer.column_filter_proxy import ColumnFilterProxy
from exdrf_qt.controls.table_viewer.sql_table_model import SqlTableModel

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QTableView
    from sqlalchemy.engine import Engine

    from exdrf_qt.controls.table_viewer.table_viewer import TableViewer


@dataclass(slots=True)
class TableViewCtx:
    """Context object with references for one open table tab.

    Attributes:
        viewer: Viewer instance that owns the tab.
        table: The opened table name.
        engine: The engine used to read.
        schema: Optional schema in use.
        view: The QTableView displaying the table.
        model: The underlying data model.
        proxy: The active filter proxy for the view.
    """

    viewer: "TableViewer"
    table: str
    engine: "Engine"
    schema: Optional[str]
    view: "QTableView"
    model: "SqlTableModel"
    proxy: "ColumnFilterProxy"

    def selected_records(self) -> List[Dict[str, Any]]:
        """Return raw dict rows for current row selection.

        Returns:
            List of dicts mapping column name to raw value.
        """
        sel = self.view.selectionModel()
        if not sel:
            return []
        headers = self.model.raw_headers()
        out: List[Dict[str, Any]] = []
        for prx_idx in sel.selectedRows():
            src_idx = self.proxy.mapToSource(prx_idx)
            raw = self.model.raw_row(src_idx.row())
            if raw is None:
                continue
            out.append({headers[i]: raw[i] for i in range(len(headers))})
        return out
