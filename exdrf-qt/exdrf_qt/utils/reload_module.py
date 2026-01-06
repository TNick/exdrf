"""Reload modules widget for PyQt5.

This module provides a `ReloadModulesWidget` that lists currently loaded
Python modules (from `sys.modules`). Each list item shows:
  - The short module name (bold)
  - The full import path
  - The file path the module was loaded from (if any)

Items are checkable via a checkbox. A Reload button deletes and re-imports
the selected modules (using `del sys.modules[name]` then
`importlib.import_module(name)`). The list is sorted alphabetically by the
module import path.
"""

from __future__ import annotations

import importlib
import logging
import os
import re
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Optional

from PyQt5.QtCore import QPoint, QSize, Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QAction,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

try:  # when imported as a package module
    from .stay_open_menu import StayOpenMenu
except Exception:  # pragma: no cover - fallback for __main__ execution
    from stay_open_menu import StayOpenMenu


if TYPE_CHECKING:
    from exdrf_util.typedefs import HasTranslate

logger = logging.getLogger(__name__)

# Roles for storing per-item data
ROLE_IMPORT = int(Qt.ItemDataRole.UserRole)
ROLE_FILE = ROLE_IMPORT + 1
ROLE_NO_FILE = ROLE_IMPORT + 2


def _collect_stdlib_dirs() -> List[str]:
    import sysconfig

    dirs: List[str] = []
    try:
        paths = sysconfig.get_paths()
        for k in ("stdlib", "platstdlib"):
            d = paths.get(k)
            if d:
                dirs.append(os.path.abspath(d))
    except Exception:
        pass
    try:
        if getattr(sys, "base_prefix", None) and sys.base_prefix != sys.prefix:
            base_paths = sysconfig.get_paths(
                vars={"base": sys.base_prefix, "platbase": sys.base_prefix}
            )
            for k in ("stdlib", "platstdlib"):
                d = base_paths.get(k)
                if d:
                    dirs.append(os.path.abspath(d))
    except Exception:
        pass
    # Deduplicate
    seen = set()
    result: List[str] = []
    for d in dirs:
        nd = os.path.normcase(os.path.normpath(d))
        if nd not in seen:
            seen.add(nd)
            result.append(d)
    return result


_STDLIB_DIRS = tuple(_collect_stdlib_dirs())


def _is_subpath(child: str, parent: str) -> bool:
    try:
        child_p = os.path.normcase(os.path.abspath(child))
        parent_p = os.path.normcase(os.path.abspath(parent))
        common = os.path.commonpath([child_p, parent_p])
        return common == parent_p
    except Exception:
        return False


def _is_stdlib_file(path: str) -> bool:
    if not path:
        return False
    for d in _STDLIB_DIRS:
        if _is_subpath(path, d):
            return True
    return False


def _collect_site_dirs() -> List[str]:
    import sysconfig

    dirs: List[str] = []
    try:
        paths = sysconfig.get_paths()
        for k in ("purelib", "platlib"):
            d = paths.get(k)
            if d:
                dirs.append(os.path.abspath(d))
    except Exception:
        pass
    try:
        if getattr(sys, "base_prefix", None) and sys.base_prefix != sys.prefix:
            base_paths = sysconfig.get_paths(
                vars={"base": sys.base_prefix, "platbase": sys.base_prefix}
            )
            for k in ("purelib", "platlib"):
                d = base_paths.get(k)
                if d:
                    dirs.append(os.path.abspath(d))
    except Exception:
        pass
    # Deduplicate
    seen = set()
    result: List[str] = []
    for d in dirs:
        nd = os.path.normcase(os.path.normpath(d))
        if nd not in seen:
            seen.add(nd)
            result.append(d)
    return result


_SITELIB_DIRS = tuple(_collect_site_dirs())


def _is_site_file(path: str) -> bool:
    if not path:
        return False
    for d in _SITELIB_DIRS:
        if _is_subpath(path, d):
            return True
    return False


_C_EXT_SUFFIXES = (".so", ".pyd", ".dll", ".dylib")


def _is_c_extension_file(path: str) -> bool:
    try:
        return (
            bool(path) and os.path.splitext(path)[1].lower() in _C_EXT_SUFFIXES
        )
    except Exception:
        return False


_DEV_TOOL_PREFIXES = (
    "pip",
    "setuptools",
    "pkg_resources",
    "pytest",
    "IPython",
    "jedi",
    "build",
    "wheel",
    "twine",
    "coverage",
    "tox",
    "nox",
    "pluggy",
)


def _to_posix_lower(path: str) -> str:
    try:
        return (
            os.path.normcase(os.path.normpath(path)).replace("\\", "/").lower()
        )
    except Exception:
        return path.replace("\\", "/").lower()


def _has_qgis_loaded() -> bool:
    try:
        for name in sys.modules.keys():
            if isinstance(name, str) and name.startswith("qgis.core"):
                return True
    except Exception:
        pass
    return False


def _is_qgis_core_file(path: str) -> bool:
    if not path:
        return False
    p = _to_posix_lower(path)
    return (
        "/apps/qgis/python/qgis/" in p
        or "/apps/qgis/python/plugins/" in p
        or "/apps/qgis/python/console" in p
    )


def _is_qgis_user_plugin_file(path: str) -> bool:
    if not path:
        return False
    p = _to_posix_lower(path)
    # Windows: AppData/Roaming/QGIS/QGIS3/profiles/<name>/python/plugins
    # Linux: ~/.local/share/QGIS/QGIS3/profiles/<name>/python/plugins
    # macOS: ~/Library/Application Support/QGIS/QGIS3/profiles/<name>/python/plugins
    return "/qgis3/profiles/" in p and "/python/plugins/" in p


@dataclass
class ModuleInfo:
    short_name: str
    import_path: str
    file_path: str
    no_file: bool


def _module_file_info(mod: object) -> tuple[str, bool]:
    """Best-effort resolution of a module's file path.

    Returns absolute path when available, otherwise a descriptive placeholder.
    """
    try:
        file_attr = getattr(mod, "__file__", None)
        if file_attr:
            return os.path.abspath(file_attr), False
        spec = getattr(mod, "__spec__", None)
        if spec is not None:
            origin = getattr(spec, "origin", None)
            if origin:
                return str(origin), False
    except Exception:  # pragma: no cover - defensive
        logger.exception("Failed to read module file path")
    return "", True


def _loaded_modules_sorted() -> List[ModuleInfo]:
    """Collect loaded modules and return them sorted by import path."""
    entries: List[ModuleInfo] = []
    for name, mod in sys.modules.items():
        if not name or mod is None:
            continue
        short = name.rsplit(".", 1)[-1]
        file_path, no_file = _module_file_info(mod)
        entries.append(
            ModuleInfo(
                short_name=short,
                import_path=name,
                file_path=file_path,
                no_file=no_file,
            )
        )
    entries.sort(key=lambda m: m.import_path.lower())
    return entries


class _ModuleItemWidget(QWidget):
    """Custom widget displayed for each module entry in the list."""

    def __init__(
        self,
        info: ModuleInfo,
        ctx: "HasTranslate",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.checkbox = QCheckBox(self)
        self.title = QLabel(info.short_name, self)
        self.title.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        bold_font = QFont()
        bold_font.setBold(True)
        self.title.setFont(bold_font)

        self.import_path = QLabel(info.import_path, self)
        self.import_path.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.import_path.setWordWrap(True)

        file_text = (
            ctx.t(
                "utils.reload_modules.placeholder.no_file",
                "(built-in/namespace/no file)",
            )
            if info.no_file or not info.file_path
            else info.file_path
        )
        self.file_path = QLabel(file_text, self)
        self.file_path.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.file_path.setWordWrap(True)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.addWidget(self.checkbox)
        top_row.addWidget(self.title, 1)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(2)
        lay.addLayout(top_row)
        lay.addWidget(self.import_path)
        lay.addWidget(self.file_path)

    def isChecked(self) -> bool:
        return self.checkbox.isChecked()


class ReloadModulesWidget(QWidget):
    """Widget listing currently loaded modules with a Reload action."""

    def __init__(
        self,
        ctx: "HasTranslate",
        parent: Optional[QWidget] = None,
        project_prefixes: Optional[List[str]] = None,
    ) -> None:
        super().__init__(parent)
        self.ctx: "HasTranslate" = ctx
        # Default project prefix guessed from our own package
        if project_prefixes is None:
            pkg = (__package__ or "").split(".")[0]
            project_prefixes = [p for p in [pkg] if p]
        self._project_prefixes: List[str] = project_prefixes
        self.setObjectName("ReloadModulesWidget")

        # Filter UI
        self.filter_edit = QLineEdit(self)
        self.filter_edit.setPlaceholderText(
            self.ctx.t("utils.reload_modules.filter.placeholder", "Filter…")
        )
        try:
            # Available on Qt >= 5.2
            self.filter_edit.setClearButtonEnabled(True)  # type: ignore[attr-defined]
        except Exception:
            pass
        self.filter_edit.textChanged.connect(self._apply_filter)

        self.filter_regex_chk = QCheckBox(
            self.ctx.t("utils.reload_modules.filter.regex", "Regex"), self
        )
        self.filter_regex_chk.toggled.connect(self._apply_filter)

        self.filter_menu_btn = QToolButton(self)
        self.filter_menu_btn.setText("⋯")
        self.filter_menu_btn.setToolTip(
            self.ctx.t("utils.reload_modules.filter.options", "Filter options")
        )
        self.filter_menu = StayOpenMenu(self)
        # Create actions with explicit non-None asserts for type checkers
        ac = self.filter_menu.addAction(
            self.ctx.t("utils.reload_modules.filter.key", "Key")
        )
        assert ac is not None
        ac.setCheckable(True)
        ac.setChecked(True)
        ac.toggled.connect(self._apply_filter)
        self._filter_ac_key: QAction = ac

        ac = self.filter_menu.addAction(
            self.ctx.t("utils.reload_modules.filter.module_path", "Module path")
        )
        assert ac is not None
        ac.setCheckable(True)
        ac.setChecked(True)
        ac.toggled.connect(self._apply_filter)
        self._filter_ac_import: QAction = ac

        ac = self.filter_menu.addAction(
            self.ctx.t("utils.reload_modules.filter.file_path", "File path")
        )
        assert ac is not None
        ac.setCheckable(True)
        ac.setChecked(True)
        ac.toggled.connect(self._apply_filter)
        self._filter_ac_file: QAction = ac
        self.filter_menu_btn.setMenu(self.filter_menu)
        self.filter_menu_btn.setPopupMode(
            QToolButton.ToolButtonPopupMode.InstantPopup
        )

        # Additional hide options
        self.filter_menu.addSeparator()
        ac = self.filter_menu.addAction(
            self.ctx.t(
                "utils.reload_modules.filter.hide_system", "Hide system modules"
            )
        )
        assert ac is not None
        ac.setCheckable(True)
        ac.setChecked(True)
        ac.toggled.connect(self._apply_filter)
        self._filter_hide_system: QAction = ac

        ac = self.filter_menu.addAction(
            self.ctx.t(
                "utils.reload_modules.filter.hide_pyqt5", "Hide PyQt5 modules"
            )
        )
        assert ac is not None
        ac.setCheckable(True)
        ac.setChecked(True)
        ac.toggled.connect(self._apply_filter)
        self._filter_hide_pyqt5: QAction = ac

        ac = self.filter_menu.addAction(
            self.ctx.t(
                "utils.reload_modules.filter.hide_qt_bindings",
                "Hide PySide bindings",
            )
        )
        assert ac is not None
        ac.setCheckable(True)
        ac.setChecked(True)
        ac.toggled.connect(self._apply_filter)
        self._filter_hide_qt_bindings: QAction = ac

        ac = self.filter_menu.addAction(
            self.ctx.t(
                "utils.reload_modules.filter.hide_builtins", "Hide built-ins"
            )
        )
        assert ac is not None
        ac.setCheckable(True)
        ac.setChecked(False)
        ac.toggled.connect(self._apply_filter)
        self._filter_hide_builtins: QAction = ac

        ac = self.filter_menu.addAction(
            self.ctx.t(
                "utils.reload_modules.filter.hide_third_party",
                "Hide third-party",
            )
        )
        assert ac is not None
        ac.setCheckable(True)
        ac.setChecked(False)
        ac.toggled.connect(self._apply_filter)
        self._filter_hide_third_party: QAction = ac

        ac = self.filter_menu.addAction(
            self.ctx.t(
                "utils.reload_modules.filter.hide_project",
                "Hide project packages",
            )
        )
        assert ac is not None
        ac.setCheckable(True)
        ac.setChecked(False)
        ac.toggled.connect(self._apply_filter)
        self._filter_hide_project: QAction = ac

        ac = self.filter_menu.addAction(
            self.ctx.t(
                "utils.reload_modules.filter.hide_dev", "Hide dev tooling"
            )
        )
        assert ac is not None
        ac.setCheckable(True)
        ac.setChecked(True)
        ac.toggled.connect(self._apply_filter)
        self._filter_hide_dev: QAction = ac

        ac = self.filter_menu.addAction(
            self.ctx.t(
                "utils.reload_modules.filter.hide_c_ext", "Hide C extensions"
            )
        )
        assert ac is not None
        ac.setCheckable(True)
        ac.setChecked(True)
        ac.toggled.connect(self._apply_filter)
        self._filter_hide_c_ext: QAction = ac

        # Dynamic QGIS options (shown only if qgis.core is loaded)
        if _has_qgis_loaded():
            ac = self.filter_menu.addAction(
                self.ctx.t(
                    "utils.reload_modules.filter.hide_qgis", "Hide QGIS modules"
                )
            )
            assert ac is not None
            ac.setCheckable(True)
            ac.setChecked(True)
            ac.toggled.connect(self._apply_filter)
            self._filter_hide_qgis: QAction = ac

            ac = self.filter_menu.addAction(
                self.ctx.t(
                    "utils.reload_modules.filter.hide_qgis_user_plugins",
                    "Hide QGIS user plugins",
                )
            )
            assert ac is not None
            ac.setCheckable(True)
            ac.setChecked(True)
            ac.toggled.connect(self._apply_filter)
            self._filter_hide_qgis_user_plugins: QAction = ac

        filter_row = QHBoxLayout()
        filter_row.setContentsMargins(0, 0, 0, 0)
        filter_row.addWidget(self.filter_edit, 1)
        filter_row.addWidget(self.filter_regex_chk)
        filter_row.addWidget(self.filter_menu_btn)

        # List UI
        self.list_widget = QListWidget(self)
        self.list_widget.setObjectName("modulesList")
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.list_widget.customContextMenuRequested.connect(
            self._on_list_context_menu
        )
        self.reload_button = QPushButton(
            self.ctx.t("utils.reload_modules.reload", "Reload"), self
        )
        self.reload_button.clicked.connect(self._on_reload_clicked)
        self.status_label = QLabel("", self)

        layout = QVBoxLayout(self)
        layout.addLayout(filter_row)
        layout.addWidget(self.list_widget)
        footer_row = QHBoxLayout()
        footer_row.setContentsMargins(0, 0, 0, 0)
        footer_row.addWidget(self.status_label, 1)
        footer_row.addWidget(self.reload_button)
        layout.addLayout(footer_row)

        self._populate()
        self._apply_filter()

    # UI building ---------------------------------------------------------
    def _populate(self) -> None:
        self.list_widget.clear()
        for info in _loaded_modules_sorted():
            item = QListWidgetItem(self.list_widget)
            item.setData(ROLE_IMPORT, info.import_path)
            item.setData(ROLE_FILE, info.file_path)
            item.setData(ROLE_NO_FILE, info.no_file)
            widget = _ModuleItemWidget(info, self.ctx, self.list_widget)
            # Ensure item has enough height for 3 lines + checkbox
            item.setSizeHint(QSize(0, widget.sizeHint().height()))
            self.list_widget.setItemWidget(item, widget)

    # Actions --------------------------------------------------------------
    def _on_reload_clicked(self) -> None:
        self.reload_button.setEnabled(False)
        try:
            to_reload: List[str] = []
            for i in range(self.list_widget.count()):
                item = self.list_widget.item(i)
                if item is None:
                    continue
                widget = self.list_widget.itemWidget(item)
                if not isinstance(widget, _ModuleItemWidget):
                    continue
                if widget.isChecked():
                    mod_name = item.data(ROLE_IMPORT)
                    if isinstance(mod_name, str):
                        to_reload.append(mod_name)

            # Two-step reload: first unload all, then import all
            for name in to_reload:
                try:
                    if name in sys.modules:
                        del sys.modules[name]
                except Exception:  # pragma: no cover - defensive
                    logger.exception("Failed to unload module: %s", name)

            successes: List[str] = []
            failures: List[str] = []
            for name in to_reload:
                try:
                    importlib.import_module(name)
                    successes.append(name)
                except Exception:  # pragma: no cover - UI feedback
                    logger.exception("Failed to reload module: %s", name)
                    failures.append(name)

            # Refresh list to reflect any changed file paths, etc.
            self._populate()
            self._apply_filter()

            # Provide feedback
            if failures:
                QMessageBox.warning(
                    self,
                    self.ctx.t("utils.reload_modules.title", "Module reload"),
                    self.ctx.t(
                        "utils.reload_modules.reload_failed",
                        "Failed to reload the following modules:\n- {param}",
                        param="\n- ".join(failures),
                    ),
                )
            elif successes:
                QMessageBox.information(
                    self,
                    self.ctx.t("utils.reload_modules.title", "Module reload"),
                    self.ctx.t(
                        "utils.reload_modules.reload_ok",
                        "Reloaded {param} module(s).",
                        param=str(len(successes)),
                    ),
                )
        finally:
            self.reload_button.setEnabled(True)

    # Context menu ---------------------------------------------------------
    def _on_list_context_menu(self, pos: QPoint) -> None:
        menu = StayOpenMenu(self.list_widget)
        ac_select_all = menu.addAction(
            self.ctx.t("utils.reload_modules.select_all", "Select All")
        )
        assert ac_select_all is not None

        def do_select_all():
            for i in range(self.list_widget.count()):
                item = self.list_widget.item(i)
                if item is None:
                    continue
                if item.isHidden():
                    continue
                widget = self.list_widget.itemWidget(item)
                if isinstance(widget, _ModuleItemWidget):
                    widget.checkbox.setChecked(True)

        ac_select_all.triggered.connect(do_select_all)

        ac_select_none = menu.addAction(
            self.ctx.t("utils.reload_modules.select_none", "Select None")
        )
        assert ac_select_none is not None

        def do_select_none():
            for i in range(self.list_widget.count()):
                item = self.list_widget.item(i)
                if item is None:
                    continue
                if item.isHidden():
                    continue
                widget = self.list_widget.itemWidget(item)
                if isinstance(widget, _ModuleItemWidget):
                    widget.checkbox.setChecked(False)

        ac_select_none.triggered.connect(do_select_none)

        ac_invert = menu.addAction(
            self.ctx.t(
                "utils.reload_modules.invert_selection", "Invert Selection"
            )
        )
        assert ac_invert is not None

        def do_invert():
            for i in range(self.list_widget.count()):
                item = self.list_widget.item(i)
                if item is None:
                    continue
                if item.isHidden():
                    continue
                widget = self.list_widget.itemWidget(item)
                if isinstance(widget, _ModuleItemWidget):
                    widget.checkbox.setChecked(not widget.checkbox.isChecked())

        ac_invert.triggered.connect(do_invert)
        menu.exec_(self.list_widget.mapToGlobal(pos))

    # Filtering ------------------------------------------------------------
    def _apply_filter(self) -> None:
        text = self.filter_edit.text().strip()
        use_regex = self.filter_regex_chk.isChecked()

        # Determine which fields are enabled
        use_key = self._filter_ac_key.isChecked()
        use_import = self._filter_ac_import.isChecked()
        use_file = self._filter_ac_file.isChecked()

        # If none selected, default to all to avoid "hide everything"
        if not (use_key or use_import or use_file):
            use_key = use_import = use_file = True

        # Hide groups
        hide_system = self._filter_hide_system.isChecked()
        hide_pyqt5 = self._filter_hide_pyqt5.isChecked()
        hide_qt_bindings = self._filter_hide_qt_bindings.isChecked()
        hide_builtins = self._filter_hide_builtins.isChecked()
        hide_third_party = self._filter_hide_third_party.isChecked()
        hide_project = self._filter_hide_project.isChecked()
        hide_dev = self._filter_hide_dev.isChecked()
        hide_c_ext = self._filter_hide_c_ext.isChecked()
        hide_qgis = (
            bool(getattr(self, "_filter_hide_qgis", None))
            and getattr(self, "_filter_hide_qgis").isChecked()
        )
        hide_qgis_user = (
            bool(getattr(self, "_filter_hide_qgis_user_plugins", None))
            and getattr(self, "_filter_hide_qgis_user_plugins").isChecked()
        )

        pattern = None
        regex_error = False
        if use_regex and text:
            try:
                pattern = re.compile(text)
            except re.error:
                regex_error = True

        # Visual feedback for invalid regex
        if regex_error:
            self.filter_edit.setStyleSheet("QLineEdit{border:1px solid #d66;}")
        else:
            self.filter_edit.setStyleSheet("")

        total = self.list_widget.count()
        visible_count = 0
        for i in range(total):
            item = self.list_widget.item(i)
            if item is None:
                continue
            widget = self.list_widget.itemWidget(item)
            # Group-based hiding first
            mod_name = item.data(ROLE_IMPORT)
            mod_file = item.data(ROLE_FILE)
            mod_no_file = item.data(ROLE_NO_FILE)

            # Pyright-friendly type narrowing
            name_str = mod_name if isinstance(mod_name, str) else ""
            file_str = mod_file if isinstance(mod_file, str) else ""
            no_file = (
                bool(mod_no_file) if isinstance(mod_no_file, bool) else False
            )

            if hide_qgis and (
                name_str.startswith("qgis.") or _is_qgis_core_file(file_str)
            ):
                item.setHidden(True)
                continue

            if hide_qgis_user and _is_qgis_user_plugin_file(file_str):
                item.setHidden(True)
                continue

            if hide_pyqt5 and (
                name_str.startswith("PyQt5") or ("PyQt5" in file_str)
            ):
                item.setHidden(True)
                continue

            if hide_qt_bindings and (
                name_str.startswith("PySide2")
                or name_str.startswith("PySide6")
                or "PySide" in file_str
            ):
                item.setHidden(True)
                continue

            # Built-in/frozen markers used by importlib
            is_builtin_mark = file_str in ("built-in", "frozen")

            if hide_system and (
                no_file or _is_stdlib_file(file_str) or is_builtin_mark
            ):
                item.setHidden(True)
                continue

            if hide_builtins and is_builtin_mark:
                item.setHidden(True)
                continue

            if hide_third_party and _is_site_file(file_str):
                item.setHidden(True)
                continue

            if hide_project and any(
                name_str.startswith(pfx) for pfx in self._project_prefixes
            ):
                item.setHidden(True)
                continue

            if hide_dev and (
                any(
                    name_str == pfx or name_str.startswith(pfx + ".")
                    for pfx in _DEV_TOOL_PREFIXES
                )
                or name_str.startswith("_pydevd_")
                or name_str.startswith("_pydev_")
                or name_str == "debugpy"
                or name_str.startswith("debugpy.")
                or name_str.startswith("pydev_")
            ):
                item.setHidden(True)
                continue

            if hide_c_ext and _is_c_extension_file(file_str):
                item.setHidden(True)
                continue

            if not isinstance(widget, _ModuleItemWidget):
                item.setHidden(False)
                visible_count += 1
                continue

            if not text or regex_error:
                hide_now = bool(regex_error)
                item.setHidden(hide_now)
                if not hide_now:
                    visible_count += 1
                continue

            key_text = widget.title.text()
            import_text = widget.import_path.text()
            file_text = widget.file_path.text()

            haystacks: List[str] = []
            if use_key:
                haystacks.append(key_text)
            if use_import:
                haystacks.append(import_text)
            if use_file:
                haystacks.append(file_text)

            matched = False
            if use_regex and pattern is not None:
                for h in haystacks:
                    if pattern.search(h):
                        matched = True
                        break
            else:
                low_q = text.lower()
                for h in haystacks:
                    if low_q in h.lower():
                        matched = True
                        break

            item.setHidden(not matched)
            if matched:
                visible_count += 1

        # Update status label
        self.status_label.setText(
            self.ctx.t(
                "utils.reload_modules.status",
                "Showing {param} modules",
                param=f"{visible_count}/{total}",
            )
        )
