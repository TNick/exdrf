from typing import TYPE_CHECKING, Any, Dict, Generic, TypeVar

from attrs import define, field
from exdrf.api import ExField
from exdrf.filter import FieldFilter
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QBrush, QColor, QFont

from exdrf_qt.context_use import QtUseContext
from exdrf_qt.models.fi_op import filter_op_registry

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401
    from exdrf_qt.models.model import QtModel  # noqa: F401
    from exdrf_qt.models.selector import Selector

DBM = TypeVar("DBM")

ROLE_MAP = {
    "DisplayRole": Qt.ItemDataRole.DisplayRole,
    "DecorationRole": Qt.ItemDataRole.DecorationRole,
    "EditRole": Qt.ItemDataRole.EditRole,
    "ToolTipRole": Qt.ItemDataRole.ToolTipRole,
    "StatusTipRole": Qt.ItemDataRole.StatusTipRole,
    "WhatsThisRole": Qt.ItemDataRole.WhatsThisRole,
    "FontRole": Qt.ItemDataRole.FontRole,
    "TextAlignmentRole": Qt.ItemDataRole.TextAlignmentRole,
    "BackgroundRole": Qt.ItemDataRole.BackgroundRole,
    "ForegroundRole": Qt.ItemDataRole.ForegroundRole,
    "CheckStateRole": Qt.ItemDataRole.CheckStateRole,
    "AccessibleTextRole": Qt.ItemDataRole.AccessibleTextRole,
    "AccessibleDescriptionRole": Qt.ItemDataRole.AccessibleDescriptionRole,
    "SizeHintRole": Qt.ItemDataRole.SizeHintRole,
    "InitialSortOrderRole": Qt.ItemDataRole.InitialSortOrderRole,
    "UserRole": Qt.ItemDataRole.UserRole,
}

regular_font = QFont("Arial", 10, QFont.Normal)
italic_font = QFont("Arial", 10, QFont.Normal)
italic_font.setItalic(True)
small_font = QFont("Arial", 8, QFont.Normal)
dark_grey = QBrush(QColor(50, 50, 50))
light_grey = QBrush(QColor(200, 200, 200))


@define(slots=False)
class QtField(ExField, QtUseContext, Generic[DBM]):
    """Base class for fields (columns) inside a model.

    Attributes:
        ctx: The context object.
        resource: The model that this field belongs to.
        preferred_width: The preferred width of the field in pixels.
    """

    ctx: "QtContext" = field(default=None)
    resource: "QtModel" = field(default=None)  # type: ignore[assignment]
    preferred_width: int = field(default=100)

    def values(self, item: DBM) -> Dict[Qt.ItemDataRole, Any]:
        """Return the values for this field.

        Args:
            item: The database record.

        Returns:
            A dictionary that maps the role to the data.
        """
        raise NotImplementedError()

    def apply_sorting(self, ascending: bool) -> Any:
        """Compute the sorting by this field.

        The default implementation is suitable for fields that map to columns.
        Reimplement this method if you want something else.

        Args:
            ascending: True if the sorting should be ascending, False otherwise.

        Returns:
            The SQLAlchemy sorting expression for this field. If you want the
            result to be ignored, return None.
        """
        column = getattr(self.resource.db_model, self.name)
        return column.asc() if ascending else column.desc()

    def apply_filter(self, item: "FieldFilter", selector: "Selector") -> Any:
        """Compute the filtering by this field.

        The default implementation is suitable for fields that map to columns.
        Reimplement this method if you want something else.

        Args:
            item: The filter item.

        Returns:
            The SQLAlchemy filtering expression for this field. If you want the
            result to be ignored, return None.
        """
        column = getattr(self.resource.db_model, self.name)

        return filter_op_registry[item.op].predicate(
            column,
            item.vl,
        )

    def blob_values(self, value: bytes) -> Dict[Qt.ItemDataRole, Any]:
        """Return the values for a blob field.

        Args:
            value: The blob value.

        Returns:
            A dictionary that maps the role to the data.
        """
        return {
            Qt.ItemDataRole.EditRole: value,
            Qt.ItemDataRole.DisplayRole: "BLOB",
            Qt.ItemDataRole.ToolTipRole: "BLOB",
        }

    def not_implemented_values(self, value: Any) -> Dict[Qt.ItemDataRole, Any]:
        """Return the values for a field that is not implemented.

        Args:
            item: The database record.

        Returns:
            A dictionary that maps the role to the data.
        """
        return {
            Qt.ItemDataRole.EditRole: value,
            Qt.ItemDataRole.DisplayRole: "NOT IMPLEMENTED",
            Qt.ItemDataRole.ToolTipRole: "NOT IMPLEMENTED",
        }

    def expand_value(self, value: Any, **kwargs) -> Dict[Qt.ItemDataRole, Any]:
        """Common way of dealing with values.

        In your `values()` method you will usually provide this method with the
        value of the field in the model and it will expand it with appropriate
        values for the various roles.

        Following cases are handled:

        - If the value is None, the display role is set to an empty string.

        Args:
            value: The raw value to set.
        """
        result = {
            Qt.ItemDataRole.DisplayRole: value,
            Qt.ItemDataRole.DecorationRole: None,
            Qt.ItemDataRole.EditRole: value,
            Qt.ItemDataRole.ToolTipRole: value,
            Qt.ItemDataRole.StatusTipRole: value,
            Qt.ItemDataRole.WhatsThisRole: None,
            Qt.ItemDataRole.FontRole: regular_font,
            Qt.ItemDataRole.TextAlignmentRole: (
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            ),
            Qt.ItemDataRole.BackgroundRole: None,
            Qt.ItemDataRole.ForegroundRole: None,
            Qt.ItemDataRole.CheckStateRole: None,
            Qt.ItemDataRole.AccessibleTextRole: value,
            Qt.ItemDataRole.AccessibleDescriptionRole: value,
            Qt.ItemDataRole.SizeHintRole: QSize(self.preferred_width, 24),
        }

        # Handle the case where the value is None.
        if value is None:
            label = self.t("cmn.null", "NULL")
            description = self.t("cmn.null_tip", "The value is not set")
            result[Qt.ItemDataRole.FontRole] = italic_font
            result[Qt.ItemDataRole.ForegroundRole] = light_grey
            result[Qt.ItemDataRole.AccessibleTextRole] = label
            result[Qt.ItemDataRole.DisplayRole] = label
            result[Qt.ItemDataRole.ToolTipRole] = description
            result[Qt.ItemDataRole.StatusTipRole] = description
            result[Qt.ItemDataRole.TextAlignmentRole] = (
                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
            )
            result[Qt.ItemDataRole.SizeHintRole] = QSize(24, 24)

        # Allow overrides by the user.
        for k in kwargs:
            result[ROLE_MAP[k]] = kwargs[k]

        return result
