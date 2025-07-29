from typing import TYPE_CHECKING, Any, Dict, List

from attrs import define, field
from exdrf.constants import RecIdType
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QBrush, QColor

if TYPE_CHECKING:
    from PyQt5.QtCore import QModelIndex

    from exdrf_qt.models.model import QtModel  # noqa: F401

LOADING_BRUSH = QBrush(QColor("lightgray"), Qt.BrushStyle.Dense4Pattern)
ERROR_BRUSH = QBrush(QColor("lightred"), Qt.BrushStyle.SolidPattern)
ERROR_COLOR = QColor("red")


@define
class QtRecord:
    """Base class for records (rows) inside a model.

    Attributes:
        model: The parent model that contains the record.
        db_id: The database ID of the record.
        values: first level contains the column key mapped to column data.
            Column data consists of a dictionary that maps the role to the data.
        loaded: A flag that indicates if the record has been loaded from the
            database or not. Stubs have this flag set to false.
    """

    model: "QtModel"
    db_id: RecIdType = field(default=None)
    values: Dict[int, Dict[Qt.ItemDataRole, Any]] = field(
        factory=dict, repr=False
    )
    _loaded: bool = field(default=False)
    _error: bool = field(default=False)

    def __attrs_post_init__(self) -> None:
        """Post-initialization method to set the loaded flag."""
        # Create records for each column.
        for i in range(len(self.model.column_fields)):
            self.values[i] = {}

        # Mark it as loaded if it has a db_id.
        if self.db_id is None or self.db_id == -1:
            self.loaded = False
        else:
            self.loaded = True

    def display_text(self) -> str:
        """Return the display text for the record."""
        if self.error:
            return self.model.t("cmn.error", "Error")
        if not self.loaded:
            return self.model.t("cmn.loading", "Loading...")
        return str(
            self.values.get(
                Qt.ItemDataRole.DisplayRole,
                self.values.get(
                    Qt.ItemDataRole.EditRole, self.model.t("cmn.null", "NULL")
                ),
            )
        )

    def data(self, column: int, role: Qt.ItemDataRole) -> Any:
        """Return the data for the given column and role.

        Args:
            column: The column index.
            role: The role to get the data for.

        Returns:
            The data for the given column and role that the model should
            return in its `data()` method.
        """
        if self.error or not self.loaded:
            if role == Qt.ItemDataRole.BackgroundColorRole:
                return ERROR_BRUSH if self.error else LOADING_BRUSH
            elif role == Qt.ItemDataRole.ForegroundRole:
                return ERROR_COLOR
            elif role == Qt.ItemDataRole.DisplayRole:
                return "error" if self.error else " "
            elif role == Qt.ItemDataRole.EditRole:
                return None
            elif role == Qt.ItemDataRole.TextAlignmentRole:
                return (
                    Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
                )
        column_data = self.values.get(column, None)
        if column_data is None:
            return None
        return column_data.get(role, None)

    @property
    def index(self) -> "QModelIndex":
        """The model index of the first column in the record.

        For computing the row the record is in we search the cache of
        the model for this record.
        """
        return self.model.index(self.model.cache.index(self), 0)  # type: ignore

    @property
    def loaded(self) -> bool:
        """Return if the record has been loaded from the database."""
        return self._loaded

    @loaded.setter
    def loaded(self, value: bool) -> None:
        """Set the loaded flag."""
        self._loaded = value
        if not value:
            # Indicate that this is a stub record.
            for i in range(len(self.model.column_fields)):
                self.values[i][Qt.ItemDataRole.BackgroundRole] = LOADING_BRUSH

    @property
    def error(self) -> bool:
        """Return if the record has an error."""
        return self._error

    @error.setter
    def error(self, value: bool) -> None:
        """Set the error flag."""
        self._error = value
        if not value:
            # Indicate that this is a stub record.
            for i in range(len(self.model.column_fields)):
                self.values[i][Qt.ItemDataRole.BackgroundRole] = ERROR_BRUSH

    def cell_index(self, col: int) -> "QModelIndex":
        """Return the index for the given column.

        For computing the row the record is in we search the cache of
        the model for this record.
        """
        return self.model.index(
            self.model.cache.index(self), col  # type: ignore
        )

    def get_row_data(self, role=Qt.ItemDataRole.DisplayRole) -> List[Any]:
        """Return the data for the given role for all columns.

        Args:
            role: The role to get the data for.

        Returns:
            A list with None in the columns that have no data for the
            given role.
        """
        return [
            self.values.get(i, {}).get(role, None)
            for i in range(max(self.values.keys()) + 1)
        ]
