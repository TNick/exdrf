from typing import TYPE_CHECKING, Any, Dict, Generic, List, Optional, TypeVar

from attrs import define, field
from exdrf.api import ExField
from exdrf.filter import FieldFilter
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QBrush, QColor, QFont
from sqlalchemy.sql.operators import or_, regexp_match_op
from unidecode import unidecode

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

    def values(self, record: DBM) -> Dict[Qt.ItemDataRole, Any]:
        """Return the values for this field.

        Args:
            record: The database record.

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

    def apply_sub_filter(
        self, item: "FieldFilter", selector: "Selector", path: List[str]
    ) -> Any:
        """Compute the filtering by this field."""
        raise NotImplementedError()

    def apply_filter(
        self,
        item: "FieldFilter",
        selector: "Selector",
        no_dia: Optional[str] = None,
    ) -> Any:
        """Compute the filtering by this field.

        The default implementation is suitable for fields that map to columns.
        Reimplement this method if you want something else.

        Args:
            item: The filter item.
            selector: The selector context (not used in default implementation).

        Returns:
            The SQLAlchemy filtering expression for this field. If you want the
            result to be ignored, return None.
        """
        from exdrf.constants import FIELD_TYPE_STRING

        column = getattr(self.resource.db_model, self.name)

        # SQLite doesn't support the flags parameter for regexp_match_op.
        # Instead, we need to embed the flags inline in the pattern using
        # Python's inline flag syntax: (?im) for case-insensitive and
        # multi-line matching.
        if (
            selector.dialect == "sqlite"
            and item.op == "regex"
            and isinstance(item.vl, str)
        ):
            # Prepend inline flags to the pattern for SQLite.
            pattern = f"(?im){item.vl}".replace("(?im)(?im)", "(?im)")
            return regexp_match_op(column, pattern, flags=None)

        if self.type_name == FIELD_TYPE_STRING and no_dia:
            ua_column = getattr(self.resource.db_model, no_dia)
            return or_(
                filter_op_registry[item.op].predicate(
                    column,
                    item.vl,
                ),
                filter_op_registry[item.op].predicate(
                    ua_column,
                    unidecode(item.vl),
                ),
            )
        else:
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
            value: The value that is not implemented.

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

        - If the value is None, the display role is set to a translated NULL
            label with italic font and grey foreground.

        Args:
            value: The raw value to set.
            **kwargs: Optional role overrides. Keys should be role names from
                ROLE_MAP (e.g., "DisplayRole", "FontRole").

        Returns:
            A dictionary that maps Qt.ItemDataRole to the appropriate data
            values for all roles.
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
