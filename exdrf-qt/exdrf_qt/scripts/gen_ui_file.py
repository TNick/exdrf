import os
import re
import subprocess
import tempfile
from typing import List, Optional, Set, Tuple

import click

var_def = re.compile(r"^self\.([a-zA-Z_][a-zA-Z0-9_]+)\s*=\s*([\.a-zA-Z0-9_]+)")

# Rewrite known obsolete import paths to their current locations.
IMPORT_PATH_REWRITES = {
    "exdrf_dev.qt.parents.widgets.parents_selector": (
        "exdrf_dev.qt_gen.db.parents.widgets.parent_selector"
    ),
}

# Maximum line length when splitting long string literals (Black default).
MAX_LINE_LENGTH = 80


def _split_long_string_line(
    line: str, max_length: int = MAX_LINE_LENGTH
) -> List[str]:
    """Split a long string line into multiple concatenated double-quoted lines.

    If the line is a single line containing one double- or triple-quoted string
    (e.g. from _translate(..., "long text")) and exceeds max_length, returns a
    list of lines with the string split at word boundaries into adjacent
    string literals. Triple-quoted strings are converted to multiple "xyz"
    lines. Otherwise returns [line].
    """
    if len(line) <= max_length:
        return [line]
    stripped = line.lstrip()
    indent = line[: len(line) - len(stripped)]
    quote_len = 1
    if stripped.startswith('"""'):
        quote_len = 3
    elif stripped.startswith("'''"):
        quote_len = 3
    elif not stripped.startswith('"'):
        return [line]
    # Find the closing quote(s), respecting backslash-escaped quotes.
    i = len(indent) + quote_len
    content_parts: List[str] = []
    close_quote = line[len(indent) : len(indent) + quote_len]
    while i < len(line):
        if line[i] == "\\" and i + 1 < len(line):
            content_parts.append(line[i : i + 2])
            i += 2
            continue
        if (
            i + quote_len <= len(line)
            and line[i : i + quote_len] == close_quote
        ):
            break
        content_parts.append(line[i])
        i += 1
    else:
        return [line]
    content = "".join(content_parts)
    tail = line[i + quote_len :]
    max_chunk = max_length - len(indent) - 2
    if max_chunk < 10:
        return [line]
    words = content.split(" ")
    chunks = _chunk_words(words, max_chunk)
    if len(chunks) <= 1:
        return [line]
    result = [indent + '"' + chunk + '"' for chunk in chunks[:-1]]
    result.append(indent + '"' + chunks[-1] + '"' + tail)
    return result


def _chunk_words(words: List[str], max_chunk: int) -> List[str]:
    """Split a list of words into chunks of at most max_chunk characters."""
    chunks: List[str] = []
    current: List[str] = []
    current_len = 0
    for w in words:
        need = len(w) + (1 if current else 0)
        if current and current_len + need > max_chunk:
            chunks.append(" ".join(current))
            current = [w]
            current_len = len(w)
        else:
            current.append(w)
            current_len += need
    if current:
        chunks.append(" ".join(current))
    return chunks


def _find_closing_quote(line: str, start: int) -> Optional[int]:
    """Return index of closing double-quote, respecting \\\"; None if not found."""
    i = start
    while i < len(line):
        if line[i] == "\\" and i + 1 < len(line):
            i += 2
            continue
        if line[i] == '"':
            return i
        i += 1
    return None


def _fallback_pyqt6_imports(
    has_qt_core: bool,
    has_qt_gui: bool,
    has_qt_widgets: bool,
    has_qt_web_engine_widgets: bool,
) -> List[str]:
    """Return PyQt6 import lines when pyuic6 did not emit any.

    Used as fallback so setup_ui can use QVBoxLayout, QLabel, etc.
    """
    lines: List[str] = []
    if has_qt_core:
        lines.append("from PyQt6.QtCore import QMetaObject, QSize, Qt")
    if has_qt_gui:
        lines.append("from PyQt6.QtGui import QAction")
    if has_qt_widgets:
        lines.append(
            "from PyQt6.QtWidgets import (\n"
            "    QAbstractItemView,\n"
            "    QComboBox,\n"
            "    QDialogButtonBox,\n"
            "    QFormLayout,\n"
            "    QHBoxLayout,\n"
            "    QHeaderView,\n"
            "    QLabel,\n"
            "    QLineEdit,\n"
            "    QProgressBar,\n"
            "    QPushButton,\n"
            "    QSizePolicy,\n"
            "    QSpacerItem,\n"
            "    QSpinBox,\n"
            "    QStackedWidget,\n"
            "    QTabWidget,\n"
            "    QToolButton,\n"
            "    QTreeView,\n"
            "    QVBoxLayout,\n"
            "    QWidget,\n"
            ")"
        )
    if has_qt_web_engine_widgets:
        lines.append("from PyQt6.QtWebEngineWidgets import QWebEngineView")
    return lines


def _split_translate_line(
    line: str, max_length: int = MAX_LINE_LENGTH
) -> List[str]:
    """Split a long line containing _translate(\"Context\", \"long string\") into multiple lines.

    If the line is too long and contains exactly one _translate(..., "second_arg")
    call, the second (translatable) string is split at word boundaries into
    multiple concatenated \"...\" lines. Otherwise returns [line].
    """
    if len(line) <= max_length:
        return [line]
    idx = line.find("_translate(")
    if idx < 0:
        return [line]
    # First quoted argument (context): after _translate(
    open_paren = idx + len("_translate(")
    if open_paren >= len(line) or line[open_paren] != '"':
        return [line]
    first_end = _find_closing_quote(line, open_paren + 1)
    if first_end is None:
        return [line]
    # Expect ", " then second string.
    after_first = first_end + 1
    if (
        after_first + 2 > len(line)
        or line[after_first : after_first + 2] != ", "
    ):
        return [line]
    second_start = after_first + 2
    if second_start >= len(line) or line[second_start] != '"':
        return [line]
    second_content_start = second_start + 1
    second_end = _find_closing_quote(line, second_content_start)
    if second_end is None:
        return [line]
    content = line[second_content_start:second_end]
    tail = line[second_end + 1 :]
    indent = line[: len(line) - len(line.lstrip())]
    cont_indent = indent + "    "
    max_chunk = max_length - len(cont_indent) - 2
    if max_chunk < 10:
        return [line]
    words = content.split(" ")
    chunks = _chunk_words(words, max_chunk)
    if len(chunks) <= 1:
        return [line]
    prefix = line[:second_start]
    if len(prefix) > max_length:
        return [line]
    result = [prefix]
    for chunk in chunks[:-1]:
        result.append(cont_indent + '"' + chunk + ' "')
    result.append(cont_indent + '"' + chunks[-1] + '"' + tail)
    return result


def _pascal_to_snake(name: str) -> str:
    """Convert PascalCase or CamelCase to snake_case."""
    result: List[str] = []
    for i, c in enumerate(name):
        if c.isupper():
            if result and (
                i == 0
                or name[i - 1].isupper()
                and i + 1 < len(name)
                and name[i + 1].islower()
            ):
                result.append("_")
            if result and result[-1] != "_":
                result.append("_")
            result.append(c.lower())
        else:
            result.append(c)
    return "".join(result).lstrip("_")


def _extract_ui_class_snake(lines: List[str]) -> Optional[str]:
    """Extract widget name in snake_case from class Ui_XXX declaration."""
    for line in lines:
        m = re.search(r"class\s+Ui_([a-zA-Z_][a-zA-Z0-9_]*)\s*:", line)
        if m:
            return _pascal_to_snake(m.group(1))
    return None


def _find_key_before_translate(text_before: str) -> str:
    """Derive translation key from the assignment nearest the translate call."""
    patterns = [
        (re.compile(r"\.setWindowTitle\s*\("), "window_title"),
        (
            re.compile(
                r"self\.([a-zA-Z_][a-zA-Z0-9_]*)\.set(?:Text|PlaceholderText|ToolTip|StatusTip)\s*\("
            ),
            1,
        ),
        (re.compile(r"indexOf\s*\(\s*self\.([a-zA-Z_][a-zA-Z0-9_]*)\s*\)"), 1),
    ]
    last_start = -1
    found_key = "text"
    for pat, key_or_group in patterns:
        for m in pat.finditer(text_before):
            if m.start() > last_start:
                last_start = m.start()
                found_key = (
                    m.group(key_or_group)
                    if isinstance(key_or_group, int)
                    else key_or_group
                )
    return found_key


def _extract_default_from_translate_args(args_match: str) -> str:
    """Extract the default string from translate's second argument (supports concatenation)."""
    parts: List[str] = []
    i = 0
    while i < len(args_match):
        if args_match[i] == '"':
            j = i + 1
            while j < len(args_match):
                if args_match[j] == "\\" and j + 1 < len(args_match):
                    j += 2
                    continue
                if args_match[j] == '"':
                    parts.append(args_match[i + 1 : j])
                    i = j + 1
                    break
                j += 1
            else:
                i += 1
        else:
            i += 1
    return "".join(parts)


def _replace_retranslate_translates(
    lines: List[str], widget_snake: str
) -> List[str]:
    """Replace QCoreApplication.translate and _translate with self.ctx.t()."""
    text = "\n".join(lines)
    # Allow [ub]? prefix (pyuic6 may output u"string" or b"string")
    translate_pattern = re.compile(
        r"(?:QCoreApplication\.translate|_translate)\s*\(\s*\"[^\"]*\"\s*,\s*"
        r"[ub]?\s*"
        r"(\"(?:[^\"\\]|\\.)*\"(?:\s*[ub]?\s*\"(?:[^\"\\]|\\.)*\")*)\s*"
        r"(?:,\s*None\s*)?\s*\)",
        re.DOTALL,
    )

    def replacer(match: "re.Match[str]") -> str:
        default_raw = match.group(1)
        default = _extract_default_from_translate_args(default_raw)
        before = text[: match.start()]
        key = _find_key_before_translate(before)
        full_key = f"gui.{widget_snake}.{key}"
        return f'self.ctx.t("{full_key}", {repr(default)})'

    result = translate_pattern.sub(replacer, text)
    lines_out = result.split("\n")
    # Remove the now-unused _translate assignment (replaced by self.ctx.t())
    _translate_assign = re.compile(
        r"^\s*_translate\s*=\s*QtCore\.QCoreApplication\.translate\s*$"
    )
    return [ln for ln in lines_out if not _translate_assign.match(ln)]


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
    _pyqt6_imports: List[str]
    _has_qt_core: bool
    _has_qt_gui: bool
    _has_qt_widgets: bool
    _has_qt_web_engine_widgets: bool
    _class_idx: int
    _setup_idx = 0

    def __init__(self, initial_text: str, custom_widgets: List[str]):
        self.initial_text = initial_text
        self._modified_text = initial_text.splitlines(False)
        self._imports = []
        self._pyqt6_imports = []
        self._has_qt_core = False
        self._has_qt_gui = False
        self._has_qt_widgets = False
        self._has_qt_web_engine_widgets = False
        self._custom_widgets = custom_widgets
        self._var_defs = []
        self._class_idx = 0
        self._setup_idx = 0

    @property
    def control_defs(self):
        return [
            (var_name, var_type)
            for var_name, var_type in sorted(self._var_defs, key=lambda x: x[0])
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
            for var_name, var_type in sorted(self._var_defs, key=lambda x: x[0])
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
        skip_import_continuation = False
        skip_pyqt6_import_continuation = False
        for line in self._modified_text:
            line = prefix + line
            prefix = ""

            # Skip continuation lines of multi-line PyQt6 import (...)
            if skip_pyqt6_import_continuation:
                if self._pyqt6_imports:
                    last = self._pyqt6_imports[-1]
                    if last.rstrip().endswith(",") or "(" in last:
                        self._pyqt6_imports[-1] = (
                            last.rstrip() + " " + line.strip()
                        )
                if ")" in line:
                    skip_pyqt6_import_continuation = False
                continue

            # Skip continuation lines of multi-line import (...)
            if skip_import_continuation:
                if self._imports and isinstance(self._imports[-1], str):
                    last = self._imports[-1]
                    if last.rstrip().endswith(",") or "(" in last:
                        self._imports[-1] = last.rstrip() + " " + line.strip()
                if ")" in line:
                    skip_import_continuation = False
                continue

            # Get rid of the comments.
            if line.startswith("#"):
                continue
            if line == "from ":
                prefix = line
                continue
            if line.startswith("from "):
                if "QtCore" in line:
                    self._has_qt_core = True
                if "QtGui" in line:
                    self._has_qt_gui = True
                if "QtWidgets" in line:
                    self._has_qt_widgets = True
                if "QtWebEngineWidgets" in line:
                    self._has_qt_web_engine_widgets = True
                if "PyQt6" not in line:
                    # Apply known import path rewrites (e.g. obsolete parents_selector)
                    for old_path, new_path in IMPORT_PATH_REWRITES.items():
                        line = line.replace(old_path, new_path)
                    self._imports.append(line)
                    # Skip continuation of "from X import (..."
                    if " import (" in line and not line.rstrip().endswith(")"):
                        skip_import_continuation = True
                else:
                    self._pyqt6_imports.append(line)
                    if " import (" in line and not line.rstrip().endswith(")"):
                        skip_pyqt6_import_continuation = True
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
            if "QtWebEngineWidgets" in line:
                self._has_qt_web_engine_widgets = True

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
                if matcher not in line:
                    continue
                idx = line.index(matcher)
                paren_start = idx + len(matcher) - 1
                args_start = paren_start + 1
                if line[args_start] == ")":
                    # No args: CustomWidget() -> CustomWidget(parent=self, ctx=self.ctx)
                    line = (
                        line[:args_start]
                        + "parent=self, ctx=self.ctx"
                        + line[args_start:]
                    )
                else:
                    # Has args. Find closing paren and add ctx; add parent= only
                    # if the first arg is positional (not already parent=xxx).
                    args_content = line[args_start:]
                    depth = 1
                    i = 1
                    while i < len(args_content) and depth > 0:
                        if args_content[i] == "(":
                            depth += 1
                        elif args_content[i] == ")":
                            depth -= 1
                        i += 1
                    if depth == 0:
                        close_idx = args_start + i - 1
                        before_close = line[args_start:close_idx].strip()
                        if not before_close.startswith("parent="):
                            line = (
                                line[:args_start]
                                + "parent="
                                + line[args_start:]
                            )
                            close_idx += 6
                        line = (
                            line[:close_idx]
                            + ", ctx=self.ctx"
                            + line[close_idx:]
                        )
                break

            split_lines = (
                _split_translate_line(line)
                if "_translate(" in line and len(line) > MAX_LINE_LENGTH
                else [line]
            )
            if len(split_lines) <= 1:
                split_lines = _split_long_string_line(line)
            changed.extend(split_lines)

        py_import = []
        if self._has_qt_core:
            py_import.append("QtCore")
        if self._has_qt_gui:
            py_import.append("QtGui")
        if self._has_qt_widgets:
            py_import.append("QtWidgets")
        if self._has_qt_web_engine_widgets:
            py_import.append("QtWebEngineWidgets")

        before_class = changed[: self._class_idx]  # noqa: E203
        after_class = changed[self._class_idx : self._setup_idx]  # noqa: E203
        after_setup = changed[self._setup_idx :]  # noqa: E203
        widget_snake = _extract_ui_class_snake(before_class)
        if widget_snake:
            after_setup = _replace_retranslate_translates(
                after_setup, widget_snake
            )
        uses_ctx = widget_snake is not None or len(self._custom_widgets) > 0
        var_decl = [
            f'    {var_name}: "{var_type}"'
            for var_name, var_type in sorted(self._var_defs, key=lambda x: x[0])
        ]
        if uses_ctx:
            var_decl.append(
                '    ctx: "Any"  # Injected by host widget when used as mixin'
            )

        var_description = [
            f"        {var_name}: {auto_field_description(var_name, var_type)}"
            for var_name, var_type in self.control_defs
        ]

        self._modified_text = []
        if len(self._imports):
            typing_import = (
                "from typing import TYPE_CHECKING, Any\n"
                if uses_ctx
                else "from typing import TYPE_CHECKING\n"
            )
            self._modified_text.append(typing_import)
        elif uses_ctx:
            self._modified_text.append("from typing import Any\n")
        if self._pyqt6_imports:
            for imp in self._pyqt6_imports:
                # Remove QCoreApplication when using ctx.t() for translation
                if "QtCore" in imp and "QCoreApplication" in imp:
                    imp = re.sub(
                        r",\s*QCoreApplication\s*",
                        " ",
                        re.sub(r"QCoreApplication\s*,\s*", "", imp),
                    ).replace("  ", " ")
                self._modified_text.append(imp)
        else:
            # Fallback: pyuic6 may not emit imports in some cases.
            # Emit explicit imports so setup_ui can use QVBoxLayout, etc.
            fallback_lines = _fallback_pyqt6_imports(
                self._has_qt_core,
                self._has_qt_gui,
                self._has_qt_widgets,
                self._has_qt_web_engine_widgets,
            )
            for line in fallback_lines:
                self._modified_text.append(line)

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


def convert_pair(
    ui_file: str, py_file: str, keep_original: Optional[str] = None
) -> int:
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

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False
    ) as tmp:
        tmp_path = tmp.name
    try:
        result = subprocess.run(
            ["pyuic6", ui_file, "-o", tmp_path],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print("pyuic6 error: %s" % (result.stderr or result.stdout))
            return 1
        with open(tmp_path, "r", encoding="utf-8") as f:
            original = f.read()
    finally:
        os.unlink(tmp_path)
    if keep_original:
        with open(keep_original, "w", encoding="utf-8") as f:
            f.write(original)

    fx = Fixer(original, custom_widgets)
    if os.path.isfile(py_file):
        os.remove(py_file)

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
    keep_original = None
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
    elif len(files) == 3:
        src_file = files[0]
        dst_file = files[1]
        keep_original = files[2]
    else:
        click.echo("Invalid number of arguments.", err=True)
        click.echo(
            "Either provide one source directory or two files.", err=True
        )
        return
    convert_pair(src_file, dst_file, keep_original)  # type: ignore[arg-type]


if __name__ == "__main__":
    cli()
