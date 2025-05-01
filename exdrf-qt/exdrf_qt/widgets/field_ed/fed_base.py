from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Generic,
    List,
    Optional,
    TypeVar,
    Union,
)

from PyQt5.QtCore import pyqtProperty  # type: ignore
from PyQt5.QtWidgets import QAction, QMenu  # type: ignore

from exdrf_qt.context_use import QtUseContext
from exdrf_qt.widgets.common.clear_action import create_clear_action
from exdrf_qt.widgets.common.nullable import NullableCtrl

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext

DBM = TypeVar("DBM")


class DrfFieldEditor(QtUseContext, Generic[DBM], NullableCtrl):
    """Base class for all field editors.

    A field editor is a control that can extract the value from a record,
    allows the user to edit it, and then set the value back to the record.
    """

    _field_name: List[str]
    clear_ac: QAction

    def __init__(self, ctx: "QtContext") -> None:
        self._field_name = []
        self._nullable = False
        self._is_null = False
        self.ctx = ctx
        self.clear_ac = None  # type: ignore

    def get_field_name(self) -> str:
        return ".".join(self._field_name)

    def set_field_name(self, name: str) -> None:
        self._field_name = name.split(".")
        self.update()  # type: ignore

    def reset_field_name(self):
        self._field_name = []
        self.update()  # type: ignore

    field_name = pyqtProperty(str, fget=get_field_name, fset=set_field_name)

    def read_value(self, record: DBM) -> None:
        """Read the value from the record and set it to the editor.

        Args:
            record: The record to read the value from.
        """
        raise NotImplementedError("Subclasses must implement set_value method.")

    def write_value(self, record: DBM) -> None:
        """Read the value from the editor and set it to the record.

        Args:
            record: The record to change the value of.
        """
        raise NotImplementedError("Subclasses must implement set_value method.")

    def _get_value(self, record: Union[Dict[str, Any], DBM]) -> Any:
        """Retrieve the value from the record.

        Args:
            record: The record to read the value from.
        """
        crt = record
        for part in self._field_name:
            if isinstance(crt, dict):
                crt = crt[part]
            else:
                if hasattr(crt, part):
                    crt = getattr(crt, part)
                else:
                    raise KeyError(f"Field '{part}' not found in record.")
        return crt

    def _set_value(self, record: DBM, value: Any) -> None:
        """Set the value to the record.

        Args:
            record: The record to change the value of.
            value: The value to set.
        """
        crt = record
        for part in self._field_name[:-1]:
            if isinstance(crt, dict):
                crt = crt[part]
            else:
                if hasattr(crt, part):
                    crt = getattr(crt, part)
                else:
                    raise KeyError(f"Field '{part}' not found in record.")
        if isinstance(crt, dict):
            crt[self._field_name[-1]] = value
        else:
            setattr(crt, self._field_name[-1], value)

    def create_clear_action(self, menu: Optional[QMenu] = None) -> QAction:
        """Create a clear_to_null action for the field editor.

        Args:
            menu: The menu to add the action to.

        Returns:
            The created action.
        """
        self.clear_ac = create_clear_action(self, menu=menu)  # type: ignore
        return self.clear_ac

    def clear_to_null(self):
        """Clear the value of the field editor to NULL."""
        if self._nullable:
            self._is_null = True
        if hasattr(self, "_clear_to_null_hook"):
            self._clear_to_null_hook()  # type: ignore
