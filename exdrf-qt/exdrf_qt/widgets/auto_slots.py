from PyQt5 import QtWidgets

from exdrf_qt.widgets.selectors import MultiSelDb, SingleSelDb


def get_change_signal(widget: QtWidgets.QWidget):
    """Get the signal that is emitted when the widget's value changes.

    Args:
        widget: The widget to get the signal from.

    Returns:
        The signal that is emitted when the widget's value changes.
    """

    if isinstance(widget, (SingleSelDb, MultiSelDb)):
        return widget.selectedItemsChanged
    if isinstance(widget, QtWidgets.QLineEdit):
        return widget.textChanged
    if isinstance(widget, QtWidgets.QDateEdit):
        return widget.dateChanged
    if isinstance(widget, QtWidgets.QCheckBox):
        return widget.stateChanged
    if isinstance(widget, QtWidgets.QSpinBox):
        return widget.valueChanged
    if isinstance(widget, QtWidgets.QDoubleSpinBox):
        return widget.valueChanged
    if isinstance(widget, QtWidgets.QSlider):
        return widget.valueChanged
    if isinstance(widget, QtWidgets.QComboBox):
        return widget.currentIndexChanged
    if isinstance(widget, QtWidgets.QRadioButton):
        return widget.toggled
    if isinstance(widget, QtWidgets.QTextEdit):
        return widget.textChanged
    if isinstance(widget, QtWidgets.QPlainTextEdit):
        return widget.textChanged
    if isinstance(widget, QtWidgets.QTimeEdit):
        return widget.timeChanged
    if isinstance(widget, QtWidgets.QDateTimeEdit):
        return widget.dateTimeChanged

    raise ValueError(
        f"Unsupported type: {type(widget)} of widget {widget.objectName()}"
    )


def auto_connect_change_signals(widget: QtWidgets.QWidget, slot):
    """Connect the change signal of all controls to a change slot.

    `enum_controls` is a method introduced by the `gen_ui_file.py` script.

    Args:
        widget: The container widget to connect the signal from.
        slot: The slot to connect the signal to.
    """
    for w in widget.enum_controls():
        if type(w) is QtWidgets.QWidget:
            continue
        if isinstance(w, (QtWidgets.QTabWidget)):
            continue
        get_change_signal(w).connect(slot)
