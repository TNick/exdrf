import io
import os
import re
from typing import List, Set, Tuple

import click

var_def = re.compile(r"^self\.([a-zA-Z_][a-zA-Z0-9_]+)\s*=\s*([\.a-zA-Z0-9_]+)")


def auto_field_description(var_name: str, var_type: str) -> str:
    if "Layout" in var_name:
        return "The layout for the widget."
    if var_name.startswith("le_"):
        return (
            f"Single line text editor for the "
            f"{var_name.replace('le_', '')} field."
        )
    if var_name.startswith("de_"):
        return f"Date editor for the {var_name.replace('de_', '')} field."
    if var_name.startswith("ck_"):
        return f"Checkbox for the {var_name.replace('ck_', '')} field."
    if var_name.startswith("sp_"):
        return f"Integer spinner for the {var_name.replace('sp_', '')} field."
    if var_name.startswith("dsp_"):
        return (
            f"Real (float) spinner for the {var_name.replace('sp_', '')} field."
        )
    if var_name.startswith("b_"):
        return f"Button for the {var_name.replace('sp_', '')} field."
    if var_name.startswith("te_"):
        return (
            f"Multiline text editor for the "
            f"{var_name.replace('te_', '')} field."
        )
    return var_name.replace("_", " ").capitalize() + "."


class Fixer:
    initial_text: str
    _modified_text: List[str]
    _custom_widgets: List[str]
    _var_defs: List[Tuple[str, str]]
    _imports: List[str]
    _has_qt_core: bool
    _has_qt_gui: bool
    _has_qt_widgets: bool
    _class_idx: int
    _setup_idx = 0

    def __init__(self, initial_text: str, custom_widgets: List[str]):
        self.initial_text = initial_text
        self._modified_text = initial_text.splitlines(False)
        self._imports = []
        self._has_qt_core = False
        self._has_qt_gui = False
        self._has_qt_widgets = False
        self._custom_widgets = custom_widgets
        self._var_defs = []
        self._class_idx = 0
        self._setup_idx = 0

    @property
    def control_defs(self):
        return [
            (var_name, var_type)
            for var_name, var_type in self._var_defs
            if not (
                var_name.startswith("label_")
                or var_name in ("label", "line")
                or "QLabel" in var_type
                or "QFrame" in var_type
            )
        ]

    @property
    def control_defs_pure(self):
        return [
            (var_name, var_type)
            for var_name, var_type in self._var_defs
            if not (
                var_name.startswith("label_")
                or var_name in ("label", "line")
                or "QLabel" in var_type
                or "QFrame" in var_type
                or "Layout" in var_type
            )
        ]

    def fix(self):
        changed = []
        prefix = ""
        in_setup_ui = False
        for line in self._modified_text:
            line = prefix + line
            prefix = ""

            # Get rid of the comments.
            if line.startswith("#"):
                continue
            if line == "from ":
                prefix = line
                continue
            if line.startswith("from "):
                if "PyQt5" not in line:
                    self._imports.append(line)
                continue

            s_line = line.strip()
            if not s_line:
                if not changed or changed[-1]:
                    changed.append(line)
                continue

            if "QtCore" in line:
                self._has_qt_core = True
            if "QtGui" in line:
                self._has_qt_gui = True
            if "QtWidgets" in line:
                self._has_qt_widgets = True

            if line.endswith("(object):"):
                line = line.replace("(object)", "")
            elif "def setupUi" in line:
                line = line.replace("def setupUi", "def setup_ui")

            line = line.replace("retranslateUi", "retranslate_ui")
            line = line.replace("centralwidget", "central_widget")
            s_line = line.strip()

            if s_line.startswith("def setup_ui"):
                in_setup_ui = True
                self._setup_idx = len(changed) + 1
            elif s_line.startswith("def "):
                in_setup_ui = False
            elif line.startswith("class "):
                self._class_idx = len(changed) + 1
                in_setup_ui = False

            if in_setup_ui:
                m = var_def.match(s_line)
                if m:
                    self._var_defs.append((m.group(1), m.group(2)))

            for cw in self._custom_widgets:
                matcher = f" = {cw}("
                if matcher in line:
                    line = (
                        line[:-1].replace("(", "(parent=") + ", ctx=self.ctx)"
                    )

            changed.append(line)

        py_import = []
        if self._has_qt_core:
            py_import.append("QtCore")
        if self._has_qt_gui:
            py_import.append("QtGui")
        if self._has_qt_widgets:
            py_import.append("QtWidgets")

        before_class = changed[: self._class_idx]  # noqa: E203
        after_class = changed[self._class_idx : self._setup_idx]  # noqa: E203
        after_setup = changed[self._setup_idx :]  # noqa: E203
        var_decl = [
            f'    {var_name}: "{var_type}"'
            for var_name, var_type in self._var_defs
        ]

        var_description = [
            f"        {var_name}: {auto_field_description(var_name, var_type)}"
            for var_name, var_type in self.control_defs
        ]

        self._modified_text = []
        if len(self._imports):
            self._modified_text.append(
                "from typing import TYPE_CHECKING\n",
            )
        self._modified_text.append("from PyQt5 import " + ", ".join(py_import))

        if len(self._imports):
            self._modified_text.append("if TYPE_CHECKING:")
            for i in self._imports:
                self._modified_text.append(f"    {i}")
            self._modified_text.append("\n")

        self._modified_text += [
            "\n",
            *before_class,
            '    """Autogenerated content.',
            "",
            "    Attributes:",
            *var_description,
            "",
            '    """\n',
            *var_decl,
            "",
            *after_class,
            *[f"        {i}" for i in self._imports],
            "\n",
            *after_setup,
            "",
            "    def enum_controls(self):",
            '        """Enumerate the controls in the form."""',
            "        return [",
            *[
                f"            self.{var_name},"
                for var_name, _ in self.control_defs_pure
            ],
            "        ]",
        ]
        return self

    @property
    def modified_text(self):
        return ("\n".join(self._modified_text) + "\n").replace("\n\n\n", "\n\n")


def convert_pair(ui_file: str, py_file: str) -> int:
    from PyQt5 import uic

    if not os.path.exists(ui_file):
        print("File not found:", ui_file)
        return 1

    custom_widgets = []
    with open(ui_file, "r", encoding="utf-8") as f:
        in_custom_widget = False
        for line in f:
            s_line = line.strip()
            if s_line == "<customwidget>":
                in_custom_widget = True
                continue
            if in_custom_widget:
                if s_line == "</customwidget>":
                    in_custom_widget = False
                    continue

                if s_line.startswith("<class>"):
                    name = s_line[7:-8]
                    if name.startswith("QtWidgets"):
                        continue
                    custom_widgets.append(name)

    output = io.StringIO()
    try:
        uic.compileUi(ui_file, output)
    except Exception as e:
        print(f"Error compiling {ui_file}: {e}")
        return 1
    fx = Fixer(output.getvalue(), custom_widgets)
    if os.path.isfile(py_file):
        os.remove(py_file)
    output.close()

    with open(py_file, "w", encoding="utf-8") as f:
        f.write(fx.fix().modified_text)
    return 0


def convert_dir(
    src_dir: str, ex_file_names: Set[str], ex_dir_names: Set[str]
) -> int:
    """Convert all .ui files in the source directory to .py files."""
    if not os.path.isdir(src_dir):
        click.echo(f"Directory not found: {src_dir}", err=True)
        return 1
    for root, dirs, files in os.walk(src_dir):
        dirs[:] = [d for d in dirs if d not in ex_dir_names]
        for f in files:
            if f.endswith(".ui"):
                file_name = os.path.splitext(f)[0]
                if file_name in ex_file_names:
                    continue
                src_file = os.path.join(root, f)
                dst_file = os.path.join(root, file_name + "_ui.py")
                convert_pair(src_file, dst_file)
                # print(f"Converted {src_file} to {dst_file}")
    return 0


@click.group()
def cli():
    """Command line interface for the script."""


@cli.command(name="gen")
@click.argument("files", nargs=-1)
@click.option(
    "--ex-file-name",
    multiple=True,
    help="Specify file names to exclude (without path or extension).",
)
@click.option(
    "--ex-dir-name",
    multiple=True,
    help="Specify directory names to exclude (without path).",
)
def cli_gen_ui_file(files, ex_file_name, ex_dir_name):
    """Generate UI files from .ui files."""
    if len(files) == 1:
        if os.path.isdir(files[0]):
            convert_dir(files[0], set(ex_file_name), set(ex_dir_name))
            return
        elif os.path.isfile(files[0]):
            src_file = files[0]
            dst_file = os.path.splitext(src_file[0])[0] + "_ui.py"
    elif len(files) == 2:
        src_file = files[0]
        dst_file = files[1]
    else:
        click.echo("Invalid number of arguments.", err=True)
        click.echo(
            "Either provide one source directory or two files.", err=True
        )
        return
    convert_pair(src_file, dst_file)  # type: ignore[arg-type]


if __name__ == "__main__":
    cli()
