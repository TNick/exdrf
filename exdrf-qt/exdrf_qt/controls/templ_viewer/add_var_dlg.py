import logging
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Type,
)

from exdrf.field_types.api import (
    BoolField,
    DateField,
    DateTimeField,
    DurationField,
    FloatField,
    FloatListField,
    IntField,
    IntListField,
    RefManyToManyField,
    RefManyToOneField,
    RefOneToManyField,
    RefOneToOneField,
    SortField,
    StrField,
    StrListField,
    TimeField,
)
from PyQt5.QtCore import QDate, QDateTime, Qt, QTime
from PyQt5.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDateTimeEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QSpinBox,
    QTimeEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from exdrf_qt.context_use import QtUseContext

if TYPE_CHECKING:
    from exdrf.field import ExField

    from exdrf_qt.context import QtContext

logger = logging.getLogger(__name__)


class ListEditWidget(QWidget, QtUseContext):
    def __init__(
        self,
        ctx: "QtContext",
        value_type: Type[Any] = str,
        parent=None,
        placeholder=None,
    ):
        super().__init__(parent)
        self.ctx = ctx
        self.value_type = value_type
        layout = QVBoxLayout(self)
        self.list_widget = QListWidget()
        self.list_widget.setDragDropMode(QListWidget.InternalMove)
        layout.addWidget(self.list_widget)
        self.list_widget.itemDoubleClicked.connect(self.on_item_double_clicked)

        add_layout = QHBoxLayout()
        self.add_edit = QLineEdit()
        self.add_edit.textChanged.connect(self.on_text_changed)
        self.add_edit.returnPressed.connect(self.add_item)
        if placeholder:
            self.add_edit.setPlaceholderText(placeholder)
        self.add_btn = QToolButton()
        self.add_btn.setText("+")
        self.add_btn.clicked.connect(self.add_item)
        add_layout.addWidget(self.add_edit)
        add_layout.addWidget(self.add_btn)
        layout.addLayout(add_layout)
        self.setLayout(layout)

    def add_item(self):
        text = self.add_edit.text().strip()
        if not text:
            return

        try:
            _ = self.value_type(text)
            self.add_edit.setStyleSheet("QLineEdit { color: black; }")
        except Exception:
            self.add_edit.setStyleSheet("QLineEdit { color: red; }")
            return

        item = QListWidgetItem(text)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsDragEnabled)
        self.add_edit.clear()
        self.list_widget.addItem(item)

    def _add_remove_button(self, item, value):
        item_widget = QWidget()
        layout = QHBoxLayout(item_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        label = QLabel(str(value))
        layout.addWidget(label, 1)  # stretch=1 so label expands
        btn = QToolButton()
        btn.setText("-")
        btn.setFixedSize(22, 22)
        btn.clicked.connect(lambda: self._remove_item(item))
        layout.addWidget(btn, 0)
        item_widget.setMinimumHeight(28)
        self.list_widget.setItemWidget(item, item_widget)

    def on_item_double_clicked(self, item):
        self.add_edit.setText(item.text())
        self._remove_item(item)
        self.add_edit.setFocus()

    def _remove_item(self, item):
        row = self.list_widget.row(item)
        self.list_widget.takeItem(row)

    def items(self):
        result = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item is not None:
                try:
                    result.append(self.value_type(item.text()))
                except Exception:
                    pass
        return result

    def on_text_changed(self, text):
        try:
            if len(text) > 0:
                _ = self.value_type(text)
            self.add_edit.setStyleSheet("QLineEdit { color: black; }")
        except Exception:
            self.add_edit.setStyleSheet("QLineEdit { color: red; }")


class NewVariableDialog(QDialog, QtUseContext):
    """Dialog for adding a new variable to a template editor.

    Attributes:
        field_types: A dictionary of field types and their display names.
        type_editors: A dictionary of type keys to editor factory methods.
        current_value_widget: The current value editor widget.
        name_edit: The name editor widget.
        type_combo: The type combo box.
        type_keys: The list of type keys.
        button_box: The button box.
    """

    invalid_names: Set[str]
    field_types: Dict[str, Tuple[str, Type["ExField"]]]
    type_editors: Dict[str, Callable[[], QWidget]]
    current_value_widget: QWidget
    name_edit: QLineEdit
    type_combo: QComboBox
    type_keys: List[str]
    button_box: QDialogButtonBox

    def __init__(
        self,
        ctx: "QtContext",
        invalid_names: Set[str],
        parent=None,
    ):
        super().__init__(parent)
        self.ctx = ctx
        self.invalid_names = invalid_names
        self.setWindowTitle("Create New Variable")

        self.field_types = {
            "boolean": (self.t("cmn.stype.boolean", "Boolean"), BoolField),
            "date": (self.t("cmn.stype.date", "Date"), DateField),
            "datetime": (
                self.t("cmn.stype.datetime", "DateTime"),
                DateTimeField,
            ),
            "duration": (
                self.t("cmn.stype.duration", "Duration"),
                DurationField,
            ),
            "float": (self.t("cmn.stype.float", "Float"), FloatField),
            "float-list": (
                self.t("cmn.stype.float-list", "FloatList"),
                FloatListField,
            ),
            "integer": (self.t("cmn.stype.integer", "Integer"), IntField),
            "integer-list": (
                self.t("cmn.stype.integer-list", "IntegerList"),
                IntListField,
            ),
            "string": (self.t("cmn.stype.string", "String"), StrField),
            "string-list": (
                self.t("cmn.stype.string-list", "StringList"),
                StrListField,
            ),
            "time": (self.t("cmn.stype.time", "Time"), TimeField),
        }

        # Map type key to editor widget class
        self.type_editors = {
            "boolean": self._make_bool_editor,
            "integer": self._make_int_editor,
            "integer-list": self._make_int_list_editor,
            "float": self._make_float_editor,
            "float-list": self._make_float_list_editor,
            "string": self._make_str_editor,
            "string-list": self._make_str_list_editor,
            "date": self._make_date_editor,
            "datetime": self._make_datetime_editor,
            "time": self._make_time_editor,
            # duration: fallback to string for now
            "duration": self._make_str_editor,
        }

        layout = QVBoxLayout(self)

        # Name
        name_layout = QHBoxLayout()
        name_label = QLabel(self.t("cmn.name", "Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.textChanged.connect(self.on_name_changed)
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)

        # Type
        type_layout = QHBoxLayout()
        type_label = QLabel(self.t("cmn.type", "Type:"))
        self.type_combo = QComboBox()
        self.type_keys = list(self.field_types.keys())
        self.type_combo.addItems(
            [value[0] for value in self.field_types.values()]
        )
        type_layout.addWidget(type_label)
        type_layout.addWidget(self.type_combo)
        layout.addLayout(type_layout)

        # Value (placeholder, will be replaced)
        self.value_editor_layout = QVBoxLayout()
        layout.addLayout(self.value_editor_layout)
        self.current_value_widget = None
        self.type_combo.currentIndexChanged.connect(self.update_value_editor)

        # Buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        self.update_value_editor()  # Initialize with the first type
        self.on_name_changed()  # Enable/disable OK button

    def validate_name(self, name: str) -> bool:
        """Validate the name of the variable."""
        if not name:
            return False
        if not name.isidentifier():
            return False
        if name in self.invalid_names:
            return False
        return True

    def on_name_changed(self):
        """Handle name changes."""
        ok_button = self.button_box.button(QDialogButtonBox.Ok)
        assert ok_button is not None
        valid = self.validate_name(self.name_edit.text())
        if valid:
            self.name_edit.setStyleSheet("QLineEdit { color: black; }")
        else:
            self.name_edit.setStyleSheet("QLineEdit { color: red; }")
        ok_button.setEnabled(valid)

    def update_value_editor(self):
        """Update the value editor based on the selected type."""
        # Remove previous editor
        for i in reversed(range(self.value_editor_layout.count())):
            item = self.value_editor_layout.itemAt(i)
            if item is not None:
                widget = item.widget()
                if widget is not None:
                    widget.setParent(None)
        self.current_value_widget = None

        idx = self.type_combo.currentIndex()
        type_key = self.type_keys[idx]
        editor_func = self.type_editors.get(type_key, self._make_str_editor)
        self.current_value_widget = editor_func()
        self.value_editor_layout.addWidget(self.current_value_widget)

    # Editor factory methods
    def _make_bool_editor(self):
        """Create a combo box for boolean values."""
        combo = QComboBox()
        combo.addItems(
            [
                self.t("cmn.false", "False"),
                self.t("cmn.true", "True"),
            ]
        )
        return combo

    def _make_int_editor(self):
        """Create a spin box for integer values."""
        spin = QSpinBox()
        spin.setMinimum(-(2**31))
        spin.setMaximum(2**31 - 1)
        return spin

    def _make_int_list_editor(self):
        """Create a list editor for integer lists."""
        return ListEditWidget(
            ctx=self.ctx,
            value_type=int,
            placeholder=self.t(
                "cmn.int_list_placeholder", "Add an item to the list"
            ),
        )

    def _make_float_editor(self):
        """Create a double spin box for floating-point values."""
        spin = QDoubleSpinBox()
        spin.setMinimum(-1e12)
        spin.setMaximum(1e12)
        spin.setDecimals(6)
        return spin

    def _make_float_list_editor(self):
        """Create a list editor for float lists."""
        return ListEditWidget(
            ctx=self.ctx,
            value_type=float,
            placeholder=self.t(
                "cmn.float_list_placeholder", "Add an item to the list"
            ),
        )

    def _make_str_editor(self):
        """Create a line edit for string values."""
        return QLineEdit()

    def _make_str_list_editor(self):
        """Create a list editor for string lists."""
        return ListEditWidget(
            ctx=self.ctx,
            value_type=str,
            placeholder=self.t(
                "cmn.str_list_placeholder", "Add an item to the list"
            ),
        )

    def _make_date_editor(self):
        """Create a date editor."""
        date_edit = QDateEdit()
        date_edit.setCalendarPopup(True)
        date_edit.setDate(QDate.currentDate())
        return date_edit

    def _make_datetime_editor(self):
        """Create a date time editor."""
        dt_edit = QDateTimeEdit()
        dt_edit.setCalendarPopup(True)
        dt_edit.setDateTime(QDateTime.currentDateTime())
        return dt_edit

    def _make_time_editor(self):
        """Create a time editor."""
        t_edit = QTimeEdit()
        t_edit.setTime(QTime.currentTime())
        return t_edit

    def get_variable_data(self):
        """Get the variable data from the dialog."""
        name = self.name_edit.text()
        if not name:
            logger.error("Name is required.")
            return None

        idx = self.type_combo.currentIndex()
        type_key = self.type_keys[idx]
        field_class = self.field_types[type_key][1]
        widget = self.current_value_widget
        if widget is None:
            logger.error(f"No value widget for type {type_key}")
            return None
        value = None
        try:
            if type_key == "boolean":
                value = widget.currentText() == self.t("cmn.true", "True")
            elif type_key == "integer":
                value = widget.value()
            elif type_key == "integer-list":
                value = widget.items()
            elif type_key == "float":
                value = widget.value()
            elif type_key == "float-list":
                value = widget.items()
            elif type_key == "string":
                value = widget.text()
            elif type_key == "string-list":
                value = widget.items()
            elif type_key == "date":
                value = widget.date().toPyDate()
            elif type_key == "datetime":
                value = widget.dateTime().toPyDateTime()
            elif type_key == "time":
                value = widget.time().toPyTime()
            else:
                value = widget.text() if hasattr(widget, "text") else None
        except Exception as e:
            logger.error(
                f"Error reading value for {name} of type {type_key}: {e}"
            )
            return None

        # Create an instance of the field
        try:
            if field_class in [
                RefManyToManyField,
                RefManyToOneField,
                RefOneToManyField,
                RefOneToOneField,
                SortField,
            ]:
                logger.error(f"Cannot create {type_key} due to complex deps.")
                return None
            field_instance = field_class(name=name)
        except TypeError as e:
            logger.error(f"Error creating instance of {type_key}: {e}")
            try:
                field_instance = field_class()
                field_instance.name = name
            except Exception as e_inner:
                err_msg = f"Fallback instantiation failed for {type_key}"
                logger.error(f"{err_msg}: {e_inner}")
                return None

        return field_instance, value

    def get_field(self) -> Tuple[Optional["ExField"], Any]:
        """Get the field from the dialog."""
        data = self.get_variable_data()
        if data:
            field_instance, value = data
            return field_instance, value
        return None, None
