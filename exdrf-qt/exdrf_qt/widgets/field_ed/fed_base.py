from typing import Any, Dict, Generic, List, TypeVar, Union

from PyQt5.QtCore import pyqtProperty  # type: ignore
from PyQt5.QtWidgets import QAction, QMenu, QStyle  # type: ignore

DBM = TypeVar("DBM")


class QtFieldEditorBase(Generic[DBM]):
    """Base class for all field editors.

    A field editor is a control that can extract the value from a record,
    allows the user to edit it, and then set the value back to the record.
    """

    _field_name: List[str]
    _nullable: bool
    _is_null: bool
    clear_ac: QAction

    def get_field_name(self) -> str:
        return ".".join(self._field_name)

    def set_field_name(self, name: str) -> None:
        self._field_name = name.split(".")
        self.update()  # type: ignore

    def reset_field_name(self):
        self._field_name = []
        self.update()  # type: ignore

    color = pyqtProperty(
        str, fget=get_field_name, fset=set_field_name, reset=reset_field_name
    )

    def get_nullable(self) -> bool:
        return self._nullable

    def set_nullable(self, nullable: bool) -> None:
        self._nullable = nullable
        self.update()  # type: ignore

    def reset_nullable(self):
        self._nullable = False
        self.update()  # type: ignore

    nullable = pyqtProperty(
        bool, fget=get_nullable, fset=set_nullable, reset=reset_nullable
    )

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

    def create_clear_action(self, menu: QMenu) -> QAction:
        """Create a clear_to_null action for the field editor.

        Args:
            menu: The menu to add the action to.

        Returns:
            The created action.
        """
        style = self.style()  # type: ignore
        assert style is not None

        clear_action = menu.addAction(
            style.standardIcon(QStyle.StandardPixmap.SP_DialogResetButton),
            "Set to Null",
        )
        assert clear_action is not None
        clear_action.triggered.connect(self.clear_to_null)

        self.clear_ac = clear_action
        clear_action.setEnabled(self._nullable)
        return clear_action

    def clear_to_null(self):
        """Clear the value of the field editor to NULL."""
        if self._nullable:
            self._is_null = True
