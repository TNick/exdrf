import json
from typing import Any, Tuple

from PyQt5 import QtWidgets

from exdrf_qt.controls.json_editor.editor import JsonEditor


class JsonEditorDialog(QtWidgets.QDialog):
    def __init__(
        self,
        data=None,
        nullable=False,
        read_only_keys=None,
        undeletable_keys=None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("JSON Editor")

        self.editor = JsonEditor(
            data, nullable, read_only_keys, undeletable_keys
        )

        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.editor)
        layout.addWidget(self.button_box)

        self.resize(600, 500)

    def get_data(self):
        return self.editor.to_python()

    @staticmethod
    def edit_json(
        data,
        nullable=False,
        read_only_keys=None,
        undeletable_keys=None,
        parent=None,
    ) -> Tuple[bool, Any]:
        dialog = JsonEditorDialog(
            data, nullable, read_only_keys, undeletable_keys, parent
        )
        result = dialog.exec()
        if result == QtWidgets.QDialog.Accepted:
            return True, dialog.get_data()
        return False, None


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)

    # Example usage
    initial_data = {
        "name": "John Doe",
        "age": 30,
        "isStudent": False,
        "courses": [
            {"title": "History", "credits": 3},
            {"title": "Math", "credits": 4},
        ],
        "address": {"street": "123 Main St", "city": "Anytown"},
        "metadata": None,
    }

    read_only = ["address.city"]
    undeletable = ["name"]

    ok, new_data = JsonEditorDialog.edit_json(
        initial_data,
        nullable=True,
        read_only_keys=read_only,
        undeletable_keys=undeletable,
    )

    if ok:
        print("Editing successful:")
        print(json.dumps(new_data, indent=2))
    else:
        print("Editing cancelled.")

    sys.exit(app.exec())
