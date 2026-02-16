import logging
import os
import re
import tempfile
import traceback
from contextlib import contextmanager
from datetime import datetime, timedelta
from enum import IntEnum
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)

import yaml  # type: ignore
from attrs import define
from exdrf.constants import FIELD_TYPE_INTEGER, RecIdType
from exdrf.field import ExField
from exdrf.var_bag import VarBag
from exdrf_al.tools import count_relationship
from exdrf_gen.jinja_support import jinja_env, recreate_global_env
from jinja2 import Environment, Template
from PyQt5.QtCore import QPoint, Qt, QThread, QTimer, QUrl, pyqtSignal
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWebEngineWidgets import QWebEnginePage
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QDialog,
    QFileDialog,
    QMenu,
    QMessageBox,
    QWidget,
)
from sqlalchemy.orm.collections import InstrumentedList, InstrumentedSet

from exdrf_qt.context_use import QtUseContext
from exdrf_qt.controls.crud_actions import (
    AcBase,
    OpenCreatePac,
    OpenDeletePac,
    OpenEditPac,
    RouteProvider,
)
from exdrf_qt.controls.templ_viewer.add_var_dlg import NewVariableDialog
from exdrf_qt.controls.templ_viewer.delegate import VarItemDelegate
from exdrf_qt.controls.templ_viewer.header import VarHeader
from exdrf_qt.controls.templ_viewer.html_to_docx.main import HtmlToDocxConverter
from exdrf_qt.controls.templ_viewer.model import VarModel
from exdrf_qt.controls.templ_viewer.templ_viewer_ui import Ui_TemplViewer
from exdrf_qt.controls.templ_viewer.view_page import (  # noqa: F401
    WebEnginePage,
)
from exdrf_qt.utils.tlh import top_level_handler

if TYPE_CHECKING:
    from sqlalchemy import Select  # noqa: F401
    from sqlalchemy.orm import Session  # noqa: F401

    from exdrf_qt.context import QtContext  # noqa: F401
    from exdrf_qt.controls import ExdrfEditor  # noqa: F401


logger = logging.getLogger(__name__)
VERBOSE = 1
LOADING_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {
            margin: 0;
            padding: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            background-color: #ffffff;
            font-family: Arial, sans-serif;
        }
        .spinner {
            width: 50px;
            height: 50px;
            border: 4px solid #f3f3f3;
            border-top: 4px solid #3498db;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="spinner"></div>
</body>
</html>
"""


@define
class CountField(ExField):
    """A field that contains the count of a relationship."""

    type_name: str = FIELD_TYPE_INTEGER


class TemplateRenderWorker(QThread):
    """Worker thread for rendering templates.

    Attributes:
        job_id: Identifier for the render job. Used to ignore stale results.
        render_func: The function to call for rendering.
        render_kwargs: Keyword arguments to pass to the render function.
        ctx: The Qt context for creating sessions in the worker thread.
    """

    job_id: int
    render_func: Callable[..., str]
    render_kwargs: Dict[str, Any]
    ctx: Optional["QtContext"]
    data: Dict[str, Any]

    rendered = pyqtSignal(int, str)
    error = pyqtSignal(int, Exception, str)

    def __init__(
        self,
        job_id: int,
        render_func: Callable[..., str],
        render_kwargs: Dict[str, Any],
        ctx: Optional["QtContext"] = None,
        parent=None,
        data: Optional[Dict[str, Any]] = None,
    ):
        """Initialize the template render worker.

        Args:
            job_id: Identifier for the render job.
            render_func: The function to call for rendering the template.
            render_kwargs: Keyword arguments to pass to the render function.
            ctx: The Qt context for creating sessions in the worker thread.
            parent: The parent QObject.
        """
        super().__init__(parent)
        self.setObjectName("TemplateRenderWorker-%s" % job_id)
        self.job_id = job_id
        self.render_func = render_func
        self.render_kwargs = render_kwargs
        self.ctx = ctx
        self.data = data if data else {}

    def run(self):
        """Execute the template rendering in the worker thread."""
        try:
            # If the caller already moved on, skip the work.
            if self.isInterruptionRequested():
                return

            html = self.render_func(**self.render_kwargs)

            # If a newer render superseded this one, do not emit.
            if self.isInterruptionRequested():
                return

            self.rendered.emit(self.job_id, html)
        except Exception as e:
            if self.isInterruptionRequested():
                return

            self.error.emit(self.job_id, e, traceback.format_exc())


snippets = {
    "templ.snp.var_name": ("Insert variable", "{{ $(name) }}"),
    "templ.snp.for_loop": (
        "Insert for loop",
        "{% for $(itr) in $(src) %}\n" "$(body)\n" "{% endfor %}",
    ),
    "templ.snp.if_stmt": (
        "Insert if statement",
        "{% if $(cond) %}\n" "$(body)\n" "{% endif %}",
    ),
    "templ.snp.if_stmt_else": (
        "Insert if-else",
        "{% if $(cond) %}\n"
        "$(body)\n"
        "{% else %}\n"
        "$(body)\n"
        "{% endif %}",
    ),
    "templ.snp.if_stmt_else_if": (
        "Insert if-else-if",
        "{% if $(cond) %}\n"
        "$(body)\n"
        "{% elif $(cond) %}\n"
        "$(body)\n"
        "{% endif %}",
    ),
    "templ.snp.namespaced_name": (
        "Insert namespaced name",
        "{% set ns = namespace($(ns_name)=False) %}\n"
        "{% for $(itr) in $(src) %}\n"
        "{%- if not ns.$(ns_name) %}\n"
        "$(body)\n"
        "{%- set ns.$(ns_name) = True %}\n"
        "{%- endif %}\n"
        "{% endfor %}",
    ),
}


class ViewMode(IntEnum):
    """The mode of the template viewer.

    Attributes:
        SOURCE: The editor presents the user with the source code of the
            template and the user can edit it.
        RENDERED: The editor presents the user with the rendered HTML of the
            template.
    """

    SOURCE = 0
    RENDERED = 1


class TemplViewer(QWidget, Ui_TemplViewer, QtUseContext, RouteProvider):
    """Widget for rendering templates.

    Attributes:
        _current_template: The current compiled template.
        _current_template_file: The file name of the current template.
        _use_edited_text: Whether the text has been edited. If the text is
            edited, the template will be replaced with one created from the
            edited text.
        _auto_save_to: The file name of the auto-save file.
        _auto_save_timer: The auto-save timer.
        jinja_env: The Jinja environment.
        header: The header of the variable editor.
        model: The model of the variable editor.
        view_mode: The mode of the template viewer: source or rendered.
    """

    _active_render_job_id: int
    _auto_save_timer: "QTimer"
    _auto_save_to: Optional[str]
    _backup_file: Optional[str]
    _current_template_file: Optional[str]
    _current_template: Optional["Template"]
    _fallback_triggered_for_seq: int
    _last_render_html: Optional[str]
    _last_render_len: int
    _last_render_seq: int
    _pending_html: Optional[str]
    _render_job_seq: int
    _render_seq: int
    _set_html_timer: "QTimer"
    _use_edited_text: bool
    extra_context: Dict[str, Any]
    header: "VarHeader"
    jinja_env: "Environment"
    model: "VarModel"
    view_mode: "ViewMode"

    ac_add: "QAction"
    ac_clear: "QAction"
    ac_copy_all: "QAction"
    ac_copy_key: "QAction"
    ac_copy_keys: "QAction"
    ac_copy_value: "QAction"
    ac_copy_values: "QAction"
    ac_others: List[Union["AcBase", QAction, None]]
    ac_refresh: "QAction"
    ac_save_as_docx: "QAction"
    ac_save_as_html: "QAction"
    ac_save_as_pdf: "QAction"
    ac_save_as_templ: "QAction"
    ac_switch_mode: "QAction"

    mnu_snippets: "QMenu"
    _prevent_render: bool
    _prevent_save: bool

    _override_content: Optional[str]
    _render_worker: Optional["TemplateRenderWorker"]
    _render_later_timer: "QTimer"
    _render_later_kwargs: Dict[str, Any]

    def __init__(
        self,
        ctx: "QtContext",
        var_bag: Optional["VarBag"] = None,
        parent=None,
        extra_context: Optional[Dict[str, Any]] = None,
        template_src: Optional[str] = None,
        page_class: Type[WebEnginePage] = WebEnginePage,
        other_actions: Optional[
            List[Union[Tuple[str, str, str], "AcBase", QAction, None]]
        ] = None,
        prevent_render: bool = False,
        var_model: Optional["VarModel"] = None,
        highlight_code: bool = True,
        override_content: Optional[str] = None,
        prevent_var_list: bool = False,
    ):
        """Initialize the template viewer.

        Args:
            ctx: The context of the template viewer.
            var_bag: The variable bag of the template viewer. Will only be used
                to construct a new model if no model is provided.
            var_model: The model of the template viewer. If not provided, a new
                model will be constructed using the var_bag.
            parent: The parent of the template viewer.
            extra_context: Extra variables to be provided to the template.
                These will not show up in the variable list.
            template_src: The source of the template.
            page_class: The class of the page used to render the template.
            other_actions: The other actions of the template viewer.
            prevent_render: Whether to prevent the template from being rendered.
        """
        self._prevent_save = False
        self._prevent_render = prevent_render
        self.ctx = ctx
        self._current_template_file = None
        self._backup_file = None
        self.extra_context = extra_context or {}
        self._current_template = None
        self.jinja_env = jinja_env
        self._auto_save_to = None
        self.view_mode = ViewMode.RENDERED
        self._use_edited_text = False
        self._override_content = override_content
        self._render_worker = None
        super().__init__(parent)

        # Prepare the model.
        if var_bag is None:
            var_bag = VarBag()
        self.model = var_model or VarModel(
            ctx=ctx, var_bag=var_bag, parent=self
        )

        # Prepare the UI.
        self.setup_ui(self)

        # Prepare the viewer.
        self.prepare_viewer(page_class)

        # Browse for the template file.
        self.c_sel_templ.clicked.connect(self.on_browse_templ_file)
        self.c_templ.textChanged.connect(self.set_template_source)

        # Context menu for template editor.
        self.c_editor.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.c_editor.customContextMenuRequested.connect(
            self.on_editor_context_menu
        )
        self.c_editor.highlight_code = highlight_code

        # Set a flag when the text is edited.
        self.c_editor.textChanged.connect(self.on_editor_text_changed)

        # Prepare the variables list.
        if prevent_var_list:
            self.c_vars.deleteLater()
            self.c_vars = None
        else:
            self.prepare_vars_list()

        # Initialize the auto-save timer
        self._auto_save_timer = QTimer(self)
        self._auto_save_timer.setSingleShot(True)
        self._auto_save_timer.setInterval(2000)  # 2 seconds delay
        self._auto_save_timer.timeout.connect(self._perform_auto_save)

        # Initialize render sequence counter for traceability of loads.
        self._render_seq = 0
        self._render_job_seq = 0
        self._active_render_job_id = -1

        # Coalesce rapid setHtml calls to avoid aborting loads.
        self._pending_html = None
        self._set_html_timer = QTimer(self)
        self._set_html_timer.setSingleShot(True)
        self._set_html_timer.timeout.connect(self._flush_pending_html)

        # Debounce render_template_later calls when responding to a
        # controlChanged.
        self._render_later_timer = QTimer(self)
        self._render_later_timer.setSingleShot(True)
        self._render_later_timer.setInterval(1500)  # 1.5 seconds
        self._render_later_timer.timeout.connect(self._on_render_later_timeout)
        self._render_later_kwargs: Dict[str, Any] = {}

        # Track last render to enable fallback loading on failures.
        self._last_render_html = None
        self._last_render_len = 0
        self._last_render_seq = 0
        self._fallback_triggered_for_seq = -1

        if template_src:
            self.c_templ.setText(template_src)
        self.model.varDataChanged.connect(self.render_template)

        # Create the actions.
        self.create_actions(other_actions)

        # By default hide the list of variables.
        self.on_toggle_vars(self.ac_toggle_vars.isChecked())

    def prepare_viewer(
        self,
        page_class: Type[WebEnginePage] = WebEnginePage,
    ):
        """Prepare the viewer."""
        logger.debug(
            "Preparing viewer %s with ID %s",
            self.c_viewer,
            id(self.c_viewer),
        )
        self.c_viewer.show()

        # Set the page for the viewer.
        page = page_class(parent=self, ctx=self.ctx)
        self.c_viewer.setPage(page)

        # Hook page/view load lifecycle signals for better diagnostics.
        try:
            page.loadStarted.connect(self._on_page_load_started)
            page.loadProgress.connect(self._on_page_load_progress)
            page.loadFinished.connect(self._on_page_load_finished)
            page.urlChanged.connect(self._on_page_url_changed)
            # Render process crashes can result in blank pages.
            page.renderProcessTerminated.connect(
                self._on_page_render_terminated
            )
        except Exception as e:
            logger.debug("Failed connecting web signals: %s", e)

        # Context menu for the template renderer.
        self.c_viewer.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.c_viewer.customContextMenuRequested.connect(
            self.on_viewer_context_menu
        )

        # React to refresh requests.
        self.c_viewer.simpleRefresh.connect(self.render_template)
        self.c_viewer.fullRefresh.connect(self.full_refresh)
        self.c_viewer.printRequested.connect(self.on_save_as_pdf)

        # React to print requests.
        page.printRequested.connect(self.on_save_as_pdf)
        page.pdfPrintingFinished.connect(self.on_saved_as_pdf)

        self.c_viewer.raise_()
        self.c_viewer.setMinimumSize(400, 400)
        self.c_viewer.show()
        self.c_viewer.update()

    def prepare_vars_list(self):
        """Prepare the variables list."""
        logger.debug(
            "Preparing variables list %s with ID %s",
            self.c_vars,
            id(self.c_vars),
        )

        # Install the model inside the tree view.
        self.c_vars.setModel(self.model)

        # Set-up the tree view.
        self.c_vars.setRootIsDecorated(False)
        self.c_vars.setUniformRowHeights(True)

        # Set alternating row colors
        self.c_vars.setAlternatingRowColors(False)
        self.c_vars.setStyleSheet(
            """
            QTreeView {
                font-size: 12px;
            }
            """
        )
        # print(QApplication.instance().styleSheet())

        # Use custom header
        self.header = VarHeader(parent=self.c_vars, ctx=self.ctx, viewer=self)
        self.c_vars.setHeader(self.header)
        self.header.setStretchLastSection(True)

        # Install custom delegate for editing values by type.
        try:
            self._var_delegate = VarItemDelegate(
                parent=self.c_vars, ctx=self.ctx
            )
            self.c_vars.setItemDelegate(self._var_delegate)
        except Exception as e:
            logger.error(
                "Failed to install VarItemDelegate: %s", e, exc_info=True
            )

        # Context menu for the list of variables.
        self.c_vars.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.c_vars.customContextMenuRequested.connect(
            self.on_vars_context_menu
        )

        # Selection change in the list of variables.
        sel_model = self.c_vars.selectionModel()
        assert sel_model is not None
        sel_model.currentRowChanged.connect(self.on_vars_selection_changed)

        # When an item is double-clicked, we may want to insert it into the
        # template editor.
        self.c_vars.doubleClicked.connect(self.on_vars_double_clicked)

    @contextmanager
    def prevent_render(self):
        """Prevent the template from being rendered."""
        self._prevent_render = True
        try:
            yield
        finally:
            self._prevent_render = False
        self.render_template()

    @contextmanager
    def prevent_save(self, rerender: bool = True):
        """Prevent the template from being rendered."""
        self._prevent_save = True
        try:
            yield
        finally:
            self._prevent_save = False

        if rerender:
            self.render_template()

    @property
    def highlight_code(self) -> bool:
        """Whether the template code should be highlighted."""
        return self.c_editor.highlight_code

    @highlight_code.setter
    def highlight_code(self, value: bool):
        """Set whether the template code should be highlighted."""
        self.c_editor.highlight_code = value

    @property
    def page(self) -> "WebEnginePage":
        """The page of the template viewer."""
        page = self.c_viewer.page()
        assert page is not None
        return cast("WebEnginePage", page)

    @property
    def var_bag(self) -> "VarBag":
        """The variable bag of the template viewer."""
        return self.model.var_bag

    @var_bag.setter
    def var_bag(self, value: "VarBag"):
        """Set the variable bag of the template viewer."""
        self.model.var_bag = value

    @property
    def current_template(self) -> Optional["Template"]:
        """The current compiled template."""
        return self._current_template

    @current_template.setter
    def current_template(self, value: "Template"):
        """Set the current compiled template.

        Changing the template will trigger a re-render.

        Args:
            value: The new template.
        """
        self._auto_save_to = None
        self._auto_save_timer.stop()
        self._current_template = value
        self.render_template()

    @property
    def current_field(self) -> Optional["ExField"]:
        """The currently selected field in the variable list."""
        crt_item = self.c_vars.currentIndex()
        if crt_item.isValid():
            return self.model.var_bag.fields[crt_item.row()]
        return None

    @property
    def override_content(self) -> Optional[str]:
        """The override content of the template viewer."""
        return self._override_content

    @override_content.setter
    def override_content(self, value: Optional[str]):
        """Set the override content of the template viewer."""
        self._override_content = value
        self.render_template()

    @top_level_handler
    def on_copy_key(self):
        """Copy the key of the currently selected variable to the clipboard."""
        if not self.current_field:
            return

        clipboard = QApplication.clipboard()
        if clipboard is None:
            return
        clipboard.setText(self.current_field.name)

    @top_level_handler
    def on_copy_value(self):
        """Copy the value of the currently selected variable to the clipboard.

        The value is converted to a string using the `str` function.
        """
        if not self.current_field:
            return

        clipboard = QApplication.clipboard()
        if clipboard is None:
            return
        clipboard.setText(str(self.model.var_bag[self.current_field.name]))

    @top_level_handler
    def on_copy_keys(self):
        """Copy all keys to the clipboard.

        The keys are joined by a newline character.
        """
        clipboard = QApplication.clipboard()
        if clipboard is None:
            return
        clipboard.setText("\n".join(self.model.var_bag.var_names))

    @top_level_handler
    def on_copy_values(self):
        """Copy all values to the clipboard.

        The values are converted to strings using the `str` function and joined
        by a newline character.
        """
        clipboard = QApplication.clipboard()
        if clipboard is None:
            return
        clipboard.setText(
            "\n".join(str(v) for v in self.model.var_bag.var_values)
        )

    @top_level_handler
    def on_copy_all(self):
        """Copy all variables to the clipboard.

        The variables are converted to a YAML dictionary and then to a string.
        """
        clipboard = QApplication.clipboard()
        if clipboard is None:
            return
        dct = self.model.var_bag.as_dict
        clipboard.setText(yaml.dump(dct, default_flow_style=False))

    @top_level_handler
    def on_add(self):
        """Add a new variable.

        The user is prompted to enter the name and value of the new variable.
        """
        dialog = NewVariableDialog(
            ctx=self.ctx,
            invalid_names=set(self.model.var_bag.var_names),
        )
        if dialog.exec_() == QDialog.Accepted:
            fld, value = dialog.get_field()
            if fld:
                self.model.add_field(fld, value)

    @top_level_handler
    def on_clear(self):
        """Clear the currently selected variable.

        The currently selected variable is removed from the model.
        """
        if not self.c_vars:
            return

        crt_item = self.c_vars.currentIndex()
        if crt_item.isValid():
            crt_field = self.model.var_bag.fields[crt_item.row()]
            self.model.var_bag[crt_field.name] = None
            self.model.varDataChanged.emit()

    def create_actions(
        self,
        other_actions: Optional[
            List[Union[Tuple[str, str, str], "AcBase", QAction, None]]
        ] = None,
    ):
        """Create the actions for the template viewer."""
        # The action that refreshes the generated content from the current
        # template and variable bag.
        self.ac_refresh = QAction(
            self.get_icon("arrow_refresh"),
            self.t("templ.vars.refresh", "Refresh"),
        )
        self.ac_refresh.triggered.connect(self.render_template)

        # The action for copying the key of the currently selected variable.
        self.ac_copy_key = QAction(
            self.t("templ.vars.copy-key", "Copy Current Key")
        )
        self.ac_copy_key.triggered.connect(self.on_copy_key)

        # The action for copying the value of the currently selected variable.
        self.ac_copy_value = QAction(
            self.t("templ.vars.copy-value", "Copy Current Value")
        )
        self.ac_copy_value.triggered.connect(self.on_copy_value)

        # The action for copying all keys.
        self.ac_copy_keys = QAction(
            self.t("templ.vars.copy-keys", "Copy All Keys")
        )
        self.ac_copy_keys.triggered.connect(self.on_copy_keys)

        # The action for copying all values.
        self.ac_copy_values = QAction(
            self.t("templ.vars.copy-values", "Copy All Values")
        )
        self.ac_copy_values.triggered.connect(self.on_copy_values)

        # The action for copying all keys and values.
        self.ac_copy_all = QAction(
            self.get_icon("page_copy"),
            self.t("templ.vars.copy-all", "Copy All"),
        )
        self.ac_copy_all.triggered.connect(self.on_copy_all)

        # The action for adding a new variable.
        self.ac_add = QAction(
            self.get_icon("plus"), self.t("templ.vars.add", "Add...")
        )
        self.ac_add.triggered.connect(self.on_add)

        # The action for clearing current variable.
        self.ac_clear = QAction(
            self.get_icon("cross"), self.t("templ.vars.clear", "Clear")
        )
        self.ac_clear.triggered.connect(self.on_clear)

        # The action for switching between source and rendered mode.
        self.ac_switch_mode = QAction()
        self.ac_switch_mode.setCheckable(True)
        self.ac_switch_mode.toggled.connect(self.on_switch_mode)
        self.ac_switch_mode.setChecked(self.view_mode == ViewMode.SOURCE)
        self.on_switch_mode(False)

        # Toggle the visibility of the variable panel.
        self.ac_toggle_vars = QAction(
            self.get_icon("eye"),
            self.t("templ.vars.toggle", "Toggle Variables"),
        )
        self.ac_toggle_vars.setCheckable(True)
        right_widget = self.c_splitter.widget(1)
        assert right_widget is not None
        self.ac_toggle_vars.setChecked(right_widget.isVisible())
        self.ac_toggle_vars.toggled.connect(self.on_toggle_vars)

        # Save the (edited) template.
        self.ac_save_as_templ = QAction(
            self.get_icon("file_save_as"),
            self.t("templ.vars.save", "Save..."),
        )
        self.ac_save_as_templ.triggered.connect(self.on_save_as_templ)

        # Auto-save the template.
        self.ac_auto_save_templ = QAction(
            self.get_icon("script_save"),
            self.t("templ.vars.auto-save", "Auto-save to ..."),
        )
        self.ac_auto_save_templ.triggered.connect(self.on_auto_save_templ)

        # Save the generated HTML.
        self.ac_save_as_html = QAction(
            self.get_icon("file_save_as"),
            self.t("templ.vars.save", "Save..."),
        )
        self.ac_save_as_html.triggered.connect(self.on_save_as_html)

        # Save the rendered content as a .pdf file.
        self.ac_save_as_pdf = QAction(
            self.get_icon("file_extension_pdf"),
            self.t("templ.vars.export.pdf", "Export as PDF"),
        )
        self.ac_save_as_pdf.triggered.connect(self.on_save_as_pdf)

        # Save the rendered content as a .docx file.
        self.ac_save_as_docx = QAction(
            self.get_icon("file_extension_doc"),
            self.t("templ.vars.export.docx", "Export as MS Word"),
        )
        self.ac_save_as_docx.triggered.connect(self.on_save_as_docx)

        # Show snippets menu.
        self.mnu_snippets = QMenu(self.t("templ.snp.t", "Snippets"))
        for name, (default_tr, snippet) in snippets.items():
            ac = QAction(self.t(name, default_tr), self.mnu_snippets)
            self.mnu_snippets.addAction(ac)
            ac.setToolTip(snippet)
            ac.setData(snippet)
            ac.triggered.connect(self.on_insert_snippet)

        # Create custom actions.
        self.ac_others = []
        if other_actions is not None:
            other_ac: Union["AcBase", QAction, None]
            for ac_src in other_actions:
                if isinstance(ac_src, tuple):
                    label, icon, route = ac_src
                    other_ac = AcBase(
                        label=label,
                        ctx=self.ctx,
                        route=route,
                        icon=self.get_icon(icon),
                        menu_or_parent=self,
                    )
                elif isinstance(ac_src, AcBase):
                    other_ac = ac_src
                elif ac_src is None:
                    other_ac = None
                elif callable(ac_src):
                    other_ac = ac_src(
                        ctx=self.ctx,
                        menu_or_parent=self,
                        provider=self,
                    )
                else:
                    raise ValueError(f"Invalid action: {ac_src}")
                self.ac_others.append(other_ac)

        # Create the actions for the template viewer.
        return [
            self.ac_copy_key,
            self.ac_copy_value,
            self.ac_copy_keys,
            self.ac_copy_values,
            self.ac_copy_all,
            self.ac_add,
            self.ac_clear,
            self.ac_switch_mode,
            self.ac_save_as_templ,
            self.ac_save_as_html,
        ]

    @top_level_handler
    def on_insert_snippet(self) -> None:
        """Insert a snippet into the editor."""
        ac = cast(QAction, self.sender())
        assert ac is not None
        if ac.data() is None:
            src = ac.text()
        else:
            src = ac.data()
        self.c_editor.insert_snippet(src)

    def update_switch_mode_action(self):
        """Change the appearance of the switch mode action based on the view
        mode.
        """
        if self.view_mode == ViewMode.SOURCE:
            self.ac_switch_mode.setText(
                self.t("templ.vars.switch-mode-rendered", "Switch to Rendered")
            )
            self.ac_switch_mode.setIcon(self.get_icon("book"))
        else:
            self.ac_switch_mode.setText(
                self.t("templ.vars.switch-mode-source", "Switch to Source")
            )
            self.ac_switch_mode.setIcon(self.get_icon("blueprint"))

    @top_level_handler
    def on_toggle_vars(self, checked: bool):
        """Toggle the visibility of the variable panel.

        Args:
            checked: Whether the variable panel is visible.
        """
        w = self.c_splitter.widget(1)
        if w is None:
            return
        w.setVisible(checked)
        self.side_panel_visibility_changed(checked)

    def side_panel_visibility_changed(self, visible: bool):
        """Called when the side panel is visible or hidden."""

    @top_level_handler
    def on_vars_selection_changed(self):
        """Update the actions based on the selection of the variable list."""
        crt_item = self.c_vars.currentIndex()
        valid = crt_item.isValid()
        self.ac_copy_key.setEnabled(valid)
        self.ac_copy_value.setEnabled(valid)

    @top_level_handler
    def on_vars_double_clicked(self):
        """Insert the currently selected variable into the template editor."""
        crt_item = self.c_vars.currentIndex()
        if crt_item.isValid() and self.view_mode == ViewMode.SOURCE:
            self.c_editor.insertPlainText(
                "{{ " + self.model.var_bag.fields[crt_item.row()].name + " }}"
            )

    @top_level_handler
    def on_vars_context_menu(self, pos: QPoint):
        """Context menu for the variable list."""
        menu = QMenu()

        menu.addAction(self.ac_copy_key)
        menu.addAction(self.ac_copy_value)
        menu.addAction(self.ac_copy_keys)
        menu.addAction(self.ac_copy_values)
        menu.addAction(self.ac_copy_all)
        menu.addSeparator()
        menu.addAction(self.ac_add)
        menu.addAction(self.ac_clear)
        menu.addSeparator()
        menu.addAction(self.ac_toggle_vars)

        menu.exec_(self.c_vars.mapToGlobal(pos))

    def add_other_view_actions(self, menu: QMenu):
        """Add the other actions to the context menu."""
        actual_actions = 0
        for ac in self.ac_others:
            if ac is not None:
                menu.addAction(ac)
                actual_actions += 1
            else:
                menu.addSeparator()
        if actual_actions:
            menu.addSeparator()

    def construct_menu(
        self,
        ac_copy: QAction,
        ac_copy_link: QAction,
        ac_cut: QAction,
        ac_paste: QAction,
        ac_inspect: QAction,
    ):
        """Construct the context menu for the template viewer."""
        menu = QMenu()

        menu.addAction(ac_copy)
        menu.addAction(ac_copy_link)
        menu.addAction(ac_cut)
        menu.addAction(ac_paste)
        menu.addSeparator()
        self.add_other_view_actions(menu)
        menu.addAction(self.ac_switch_mode)
        menu.addAction(self.ac_toggle_vars)
        menu.addSeparator()
        menu.addAction(self.ac_save_as_html)
        menu.addAction(self.ac_save_as_pdf)
        menu.addAction(self.ac_save_as_docx)
        menu.addSeparator()
        menu.addAction(self.ac_refresh)
        menu.addAction(ac_inspect)

        return menu

    @top_level_handler
    def on_viewer_context_menu(self, pos: QPoint):
        """Context menu for the template renderer."""
        try:
            ac_copy_link = self.c_viewer.pageAction(
                QWebEnginePage.WebAction.CopyLinkToClipboard
            )
            assert ac_copy_link is not None
            ac_copy = self.c_viewer.pageAction(QWebEnginePage.WebAction.Copy)
            assert ac_copy is not None
            ac_cut = self.c_viewer.pageAction(QWebEnginePage.WebAction.Cut)
            assert ac_cut is not None
            ac_paste = self.c_viewer.pageAction(QWebEnginePage.WebAction.Paste)
            assert ac_paste is not None
            ac_inspect = self.c_viewer.pageAction(
                QWebEnginePage.WebAction.InspectElement
            )
            assert ac_inspect is not None

            menu = self.construct_menu(
                ac_copy,
                ac_copy_link,
                ac_cut,
                ac_paste,
                ac_inspect,
            )

            result_ac = menu.exec_(self.c_viewer.mapToGlobal(pos))
            if result_ac == ac_inspect:
                # Show devtools view when inspect is triggered
                self.c_viewer.show_devtools()
        except Exception as e:
            logger.error("Error showing context menu: %s", e, exc_info=True)

    @top_level_handler
    def on_editor_context_menu(self, pos: QPoint):
        """Context menu for the template editor."""
        menu = self.c_editor.createStandardContextMenu()
        if menu is None:
            menu = QMenu()
        menu.addMenu(self.mnu_snippets)
        menu.addSeparator()
        menu.addAction(self.ac_switch_mode)
        menu.addAction(self.ac_toggle_vars)
        menu.addSeparator()
        menu.addAction(self.ac_save_as_templ)
        menu.addAction(self.ac_auto_save_templ)

        menu.exec_(self.c_editor.mapToGlobal(pos))

    @top_level_handler
    def on_browse_templ_file(self):
        """Browse for the template file."""
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            self.t("templ.open-dlg.t", "Open Template File"),
            "",
            self.t("templ.open-dlg.filter", "Jinja2 Template Files (*.j2)"),
        )
        if file_name:
            self.c_templ.setText(file_name)

    def set_template_source(
        self, text: Optional[str], var_bag: Optional[VarBag] = None
    ):
        """React to change in the text of the template file line edit.

        The template is compiled and the source code is displayed in the
        editor.

        Args:
            text: The file system path or module path to the template file.
        """

        with self.prevent_save(rerender=False):
            if var_bag is not None:
                self.model.var_bag = var_bag

            if not text:
                self.c_templ.setStyleSheet("QLineEdit { color: black; }")
                self.c_templ.setToolTip(
                    self.t("templ.open-dlg.none", "No template file selected")
                )
                self._current_template = None
                self._current_template_file = None
                self._use_edited_text = False
                self.c_editor.setPlainText("")
                self.render_template()
                return

            try:
                self._current_template = self.jinja_env.get_template(text)
                self.c_templ.setStyleSheet("QLineEdit { color: black; }")
                self.c_templ.setToolTip("")

                loader = self.jinja_env.loader
                assert loader is not None
                source, filename, _ = loader.get_source(self.jinja_env, text)
                # self.c_editor.blockSignals(True)
                # self.c_editor.setPlainText(source)
                # self.c_editor.blockSignals(False)
                self._current_template_file = filename
                self._use_edited_text = False
                self.render_template()
                if self.c_editor.toPlainText() != source:
                    self.c_editor.blockSignals(True)
                    self.c_editor.setPlainText(source)
                    self.c_editor.blockSignals(False)

            except Exception as e:
                logger.error("Error loading template: %s", e, exc_info=True)
                self.c_templ.setStyleSheet("QLineEdit { color: red; }")
                self.c_templ.setToolTip(str(e))
                self.show_exception(e, traceback.format_exc())

    @top_level_handler
    def on_switch_mode(self, checked: bool):
        """Switch between source and rendered mode.

        Args:
            checked: Whether the source mode is selected.
        """
        try:
            self.view_mode = ViewMode.SOURCE if checked else ViewMode.RENDERED
            self.update_switch_mode_action()
            if self.view_mode == ViewMode.RENDERED:
                self.c_stacked.setCurrentWidget(self.page_viewer)
                if self._use_edited_text:
                    self._current_template = self.jinja_env.from_string(
                        self.c_editor.toPlainText()
                    )
                self.render_template()
            else:
                self.c_stacked.setCurrentWidget(self.page_editor)
        except Exception as e:
            logger.error("Error switching mode: %s", e, exc_info=True)
            self.show_exception(e, traceback.format_exc())

    def _ensure_fresh_template(self):
        if not self._use_edited_text and self._current_template:
            # Check if the template file has been modified
            try:
                if not self._current_template.is_up_to_date:
                    logger.debug("Template file has changed, reload it")
                    assert self._current_template.filename is not None
                    self._current_template = self.jinja_env.get_template(
                        self._current_template.filename
                    )
                    loader = self.jinja_env.loader
                    assert self._current_template is not None
                    assert loader is not None
                    assert self._current_template.filename is not None
                    source, filename, _ = loader.get_source(
                        self.jinja_env, self._current_template.filename
                    )
                    self.c_editor.blockSignals(True)
                    self.c_editor.setPlainText(source)
                    self.c_editor.blockSignals(False)
                    logger.debug("Template file has been reloaded")
            except Exception as e:
                logger.warning("Error checking template file: %s", e)

    def _render_template(self, **kwargs):
        """The actual rendering of the template."""
        assert self._current_template is not None
        self._ensure_fresh_template()
        return self._current_template.render(
            # Merge all dicts, with later dicts overriding earlier ones in case
            # of duplicate keys
            **{
                **self.model.var_bag.as_dict,
                **self.extra_context,
                "api_point": self.ctx.data,
                **kwargs,
            },
        )

    def full_refresh(self):
        """Full refresh of the template."""
        self.jinja_env = recreate_global_env()

        profile = self.c_viewer.page().profile()
        profile.clearHttpCache()
        profile.clearAllVisitedLinks()
        profile.cookieStore().deleteAllCookies()

        self.model = VarModel(self.ctx, self.var_bag)
        if self.c_vars:
            self.c_vars.setModel(self.model)

        if self._use_edited_text:
            self._current_template = self.jinja_env.from_string(
                self.c_editor.toPlainText()
            )
        elif self._current_template_file is not None:
            self._current_template = self.jinja_env.get_template(
                self._current_template_file
            )

        self.render_template()

    def _is_webview_valid(self) -> bool:
        """Check if the WebView is still valid and not deleted.

        Returns:
            True if the WebView is valid and can be used, False otherwise.
        """
        try:
            # Try to access a simple property to check if the object is valid
            _ = self.c_viewer.objectName()
            return True
        except RuntimeError as e:
            if "wrapped C/C++ object" in str(e) and "deleted" in str(e):
                return False
            # Re-raise other RuntimeErrors
            raise
        except Exception:
            # For any other exception, assume the object is invalid
            return False

    # -- WebEngine diagnostics -------------------------------------------------

    @top_level_handler
    def _on_page_load_started(self) -> None:
        try:
            url = self.c_viewer.url().toString()  # type: ignore[attr-defined]
        except Exception:
            url = "<unknown>"
        logger.log(VERBOSE, "WebEngine loadStarted url=%s", url)

    def _on_page_load_progress(self, p: int) -> None:
        logger.log(VERBOSE, "WebEngine loadProgress=%d", p)

    @top_level_handler
    def _on_page_load_finished(self, ok: bool) -> None:
        try:
            url = self.c_viewer.url().toString()  # type: ignore[attr-defined]
        except Exception:
            url = "<unknown>"
        logger.log(VERBOSE, "WebEngine loadFinished ok=%s url=%s", ok, url)
        # Fallback: if load failed after setHtml, try loading via temp file.
        if not ok and self._last_render_html and self._last_render_len > 0:
            if self._fallback_triggered_for_seq != self._last_render_seq:
                self._fallback_triggered_for_seq = self._last_render_seq
                self._fallback_load_via_file(
                    self._last_render_html, self._last_render_seq
                )

    @top_level_handler
    def _on_page_url_changed(self, url: QUrl) -> None:
        try:
            s = url.toString()
        except Exception:
            s = "<unavailable>"
        logger.log(VERBOSE, "WebEngine urlChanged=%s", s)

    def _on_page_render_terminated(self, status, exit_code: int) -> None:
        # Status is an enum; print it as-is to avoid import churn.
        logger.error(
            "WebEngine render process terminated status=%s exit_code=%s",
            status,
            exit_code,
        )

    def render_template_later(self, **kwargs):
        """Schedule a delayed render of the template.

        This method debounces rapid calls to render_template by restarting
        a timer. The actual render will happen 1.5 seconds after the last
        call to this method.

        Args:
            **kwargs: Additional keyword arguments to pass to render_template.
        """
        # Store kwargs for later use
        self._render_later_kwargs = kwargs
        # Stop any existing timer
        if self._render_later_timer.isActive():
            self._render_later_timer.stop()
        # Start the timer (will trigger render_template after 1.5 seconds)
        self._render_later_timer.start()

    def _on_render_later_timeout(self):
        """Handle the timeout of the render_later timer."""
        kwargs = self._render_later_kwargs.copy()
        self._render_later_kwargs.clear()
        self.render_template(**kwargs)

    def render_template(self, **kwargs):
        """Render the template.

        If the current view mode is source, the template is not rendered.
        """
        if self.view_mode == ViewMode.SOURCE:
            logger.log(VERBOSE, "Skipping render of template in source mode")
            return
        if self._prevent_render:
            logger.log(
                VERBOSE, "Skipping render of template in prevent_render mode"
            )
            return

        # Check if the WebView is still valid before attempting to render
        if not self._is_webview_valid():
            logger.warning(
                "WebView is no longer valid, skipping template render"
            )
            return

        # Cancel any existing render worker
        if self._render_worker is not None and self._render_worker.isRunning():
            # Never use terminate(): it is unsafe and can crash the process
            # (notably on Windows). Instead, request interruption and ignore
            # stale results via job_id.
            logger.log(
                VERBOSE, "Cancelling previous render worker (soft cancel)"
            )
            try:
                self._render_worker.requestInterruption()
            except Exception as e:
                logger.debug(
                    "Failed to request interruption for render worker: %s",
                    e,
                    exc_info=True,
                )

        try:
            if self._override_content:
                logger.log(VERBOSE, "Rendering override content...")
                html = self._override_content
                # For override content, render immediately (no threading needed)
                if not self._is_webview_valid():
                    logger.warning(
                        "WebView became invalid during template rendering, "
                        "skipping setHtml"
                    )
                    return
                self._queue_set_html(html)
            elif self._current_template is not None:
                logger.log(
                    1, "Rendering template %s...", self._current_template
                )
                # Render in a separate thread
                self._render_template_async(**kwargs)
            else:
                html = self.t(
                    "templ.render.none",
                    "<p style='color: grey; font-style: italic;'>"
                    "No template loaded"
                    "</p>",
                )
                logger.debug("No template loaded, using default message")
                if not self._is_webview_valid():
                    logger.warning(
                        "WebView became invalid during template rendering, "
                        "skipping setHtml"
                    )
                    return
                self._queue_set_html(html)
        except RuntimeError as e:
            if "wrapped C/C++ object" in str(e) and "deleted" in str(e):
                logger.warning(
                    "WebView was deleted during template rendering: %s", e
                )
                return
            else:
                logger.error("Error rendering template: %s", e, exc_info=True)
                self.show_exception(e, traceback.format_exc())
        except Exception as e:
            logger.error("Error rendering template: %s", e, exc_info=True)
            self.show_exception(e, traceback.format_exc())

    def _get_loading_html(self) -> str:
        """Get HTML with a circular progress indicator.

        Returns:
            HTML string with a centered circular spinner.
        """
        return LOADING_HTML

    def _render_template_async(self, **kwargs):
        """Render the template asynchronously in a worker thread."""
        # Show loading indicator in web view
        if self._is_webview_valid():
            loading_html = self._get_loading_html()
            self._queue_set_html(loading_html)

        # Create worker thread. Use job ids to avoid out-of-order updates.
        self._render_job_seq += 1
        job_id = self._render_job_seq
        self._active_render_job_id = job_id

        worker = TemplateRenderWorker(
            job_id=job_id,
            render_func=self._render_template,
            render_kwargs=kwargs,
            ctx=self.ctx,
            parent=self,
        )
        self._render_worker = worker

        # Allow the subclasses to adjust the thread.
        self._adjust_render_thread()

        # Connect signals
        worker.rendered.connect(self._on_template_rendered)
        worker.error.connect(self._on_template_render_error)
        worker.finished.connect(lambda: self._on_render_worker_finished(worker))

        # Start the worker
        worker.start()

    def _adjust_render_thread(self):
        """Adjust the render thread."""

    @top_level_handler
    def _on_template_rendered(self, job_id: int, html: str):
        """Handle successful template rendering."""
        if job_id != self._active_render_job_id:
            logger.log(
                1,
                "Ignoring rendered HTML for stale job_id=%d (active=%d)",
                job_id,
                self._active_render_job_id,
            )
            return

        html_len = len(html) if isinstance(html, str) else 0
        if html_len == 0 or (isinstance(html, str) and not html.strip()):
            logger.warning("Rendered HTML is empty/blank")
        else:
            logger.log(VERBOSE, "Rendered HTML length=%d", html_len)
        logger.log(VERBOSE, "The template has been rendered")

        # Double-check WebView validity before setting HTML
        if not self._is_webview_valid():
            logger.warning(
                "WebView became invalid during template rendering, "
                "skipping setHtml"
            )
            return

        # Coalesce setHtml invocations; schedule a single update shortly.
        self._queue_set_html(html)

    @top_level_handler
    def _on_template_render_error(
        self, job_id: int, e: Exception, formatted: str
    ) -> None:
        """Handle template rendering error."""
        if job_id != self._active_render_job_id:
            logger.log(
                1,
                "Ignoring render error for stale job_id=%d (active=%d): %s",
                job_id,
                self._active_render_job_id,
                e,
            )
            return

        logger.error("Error rendering template: %s", e, exc_info=True)

        # Show exception in viewer
        self.show_exception(e, formatted)

    @top_level_handler
    def _on_render_worker_finished(self, worker: TemplateRenderWorker) -> None:
        """Handle worker thread completion.

        Args:
            worker: The worker that finished.
        """
        try:
            worker.deleteLater()
        except Exception as e:
            logger.debug("Failed to delete render worker: %s", e, exc_info=True)

        if self._render_worker is worker:
            self._render_worker = None

    def _snapshot_page_html(self, seq: int) -> None:
        """Log a small snapshot/length of the current page HTML for seq.

        This helps diagnose cases where setHtml succeeds but nothing is shown.
        """
        try:
            page = self.c_viewer.page()
        except Exception:
            page = None
        if page is None:
            logger.debug("snapshot(seq=%d): page unavailable", seq)
            return

        # try:
        #     page.toHtml(
        #         lambda html: logger.debug(
        #             "snapshot(seq=%d): html_len=%s head=%s",
        #             seq,
        #             (len(html) if isinstance(html, str) else "<none>"),
        #             (
        #                 (html[:120] + "...")
        #                 if isinstance(html, str) and len(html) > 120
        #                 else html
        #             ),
        #         )
        #     )
        # except Exception as e:
        #     logger.debug("snapshot(seq=%d) failed: %s", seq, e)

    def _queue_set_html(self, html: str) -> None:
        """Queue a setHtml call; collapse bursts into a single update."""
        self._pending_html = html
        # Use a short delay to batch multiple renders in the same loop turn.
        if not self._set_html_timer.isActive():
            self._set_html_timer.start(10)

    def _flush_pending_html(self) -> None:
        html = self._pending_html
        self._pending_html = None
        if html is None:
            return
        # Track the setHtml invocations to correlate with load signals.
        self._render_seq += 1
        seq = self._render_seq
        self._last_render_seq = seq
        self._last_render_html = html
        self._last_render_len = len(html) if isinstance(html, str) else 0
        # Reset fallback guard for this sequence.
        self._fallback_triggered_for_seq = -1
        logger.debug("setHtml(seq=%d) start", seq)
        try:
            # Provide a baseUrl to avoid data: origin restrictions.
            self.c_viewer.setHtml(html, QUrl("exdrf://assets/index.html"))
        except Exception as e:
            logger.error("setHtml(seq=%d) failed: %s", seq, e, exc_info=True)
            return
        try:
            # Snapshot the page HTML shortly after scheduling setHtml.
            QTimer.singleShot(200, lambda: self._snapshot_page_html(seq))
        except Exception as e:
            logger.debug(
                "Failed to schedule HTML snapshot seq=%d: %s",
                seq,
                e,
                exc_info=True,
            )
        logger.debug("setHtml(seq=%d) scheduled", seq)

    def _fallback_load_via_file(self, html: str, seq: int) -> None:
        """Write HTML to a temp file and load it via setUrl as a fallback."""
        try:
            import tempfile as _tf

            fd, path = _tf.mkstemp(suffix=".html", prefix="templ-")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(html)
            except Exception:
                # Ensure the file descriptor is closed on error as well
                try:
                    os.close(fd)
                except Exception:
                    pass
                raise
            q_url = QUrl.fromLocalFile(path)
            logger.debug("fallback setUrl(seq=%d) path=%s", seq, path)
            self.c_viewer.setUrl(q_url)
            try:
                QTimer.singleShot(300, lambda: self._snapshot_page_html(seq))
            except Exception as e:
                logger.debug(
                    "Failed to schedule fallback snapshot seq=%d: %s",
                    seq,
                    e,
                    exc_info=True,
                )
        except Exception as e:
            logger.error(
                "Fallback load via file failed seq=%d: %s",
                seq,
                e,
                exc_info=True,
            )

    def show_exception(self, e: Exception, formatted: str):
        """Show an exception in the viewer.

        Args:
            e: The exception to show.
            formatted: The formatted exception.
        """
        # Check if the WebView is still valid before showing exception
        if not self._is_webview_valid():
            logger.warning("WebView is no longer valid, cannot show exception")
            return

        try:
            html = self.t(
                "templ.render.error",
                "<p style='color: red;'>Error rendering template: {e}</p>",
                e=e,
            )
            html += f"<pre style='color: grey;'>{formatted}</pre>"
            self.c_viewer.setHtml(html)
        except RuntimeError as e:
            if "wrapped C/C++ object" in str(e) and "deleted" in str(e):
                logger.warning(
                    "WebView was deleted while showing exception: %s", e
                )
                return
            else:
                raise

    def on_editor_text_changed(self):
        """Handle the change of the editor text."""
        if self._prevent_save:
            logger.log(VERBOSE, "Skipping auto-save in prevent_save mode")
            return
        self._use_edited_text = True
        if self._auto_save_timer.isActive():
            self._auto_save_timer.stop()
        # if self._auto_save_to is not None:
        self._auto_save_timer.start()

    def _perform_auto_save(self):
        """Perform the actual auto-save operation."""
        if self._prevent_save:
            logger.log(VERBOSE, "Skipping auto-save in prevent_save mode")
            return

        if self._auto_save_to is not None:
            try:
                with open(self._auto_save_to, "w", encoding="utf-8") as f:
                    f.write(self.get_template_content_for_save())
            except Exception as e:
                logger.error("Error auto-saving template: %s", e, exc_info=True)
        else:
            # Compute a backup file name.
            if self._backup_file is None:
                now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                self._backup_file = tempfile.mktemp(
                    suffix=f"-exdrf-template-backup-{now_str}.j2"
                )
                logger.info("Created backup file: %s", self._backup_file)

            # Save the backup file.
            with open(self._backup_file, "w", encoding="utf-8") as f:
                f.write(self.get_template_content_for_save())

            # Delete old backups.
            self.delete_old_backups()

    def delete_old_backups(self):
        """Iterate existing file and delete those that are older than two
        days.
        """
        assert self._backup_file is not None
        tmp_dir = os.path.dirname(self._backup_file)
        pattern = re.compile(
            r"^.*-exdrf-template-backup-"
            r"(\d{4})(\d{2})(\d{2})_"
            r"(\d{2})(\d{2})(\d{2})\.j2$"
        )
        now = datetime.now()
        limit = now - timedelta(days=2)
        for file in os.listdir(tmp_dir):
            match = pattern.match(file)
            if match:
                file_path = os.path.join(tmp_dir, file)
                created = datetime(
                    int(match.group(1)),
                    int(match.group(2)),
                    int(match.group(3)),
                    int(match.group(4)),
                    int(match.group(5)),
                    int(match.group(6)),
                )
                if created < limit:
                    os.remove(file_path)
                    logger.info("Deleted old backup file: %s", file_path)

    def get_template_content_for_save(self) -> str:
        """Get the template content for saving."""
        return self.c_editor.toPlainText()

    @top_level_handler
    def on_save_as_templ(self):
        """Save the template."""
        try:
            filter_str = self.t(
                "templ.save-templ.filter", "Jinja2 Template Files (*.j2)"
            )
            file_name, _ = QFileDialog.getSaveFileName(
                self,
                self.t("templ.save-templ.t", "Save Template"),
                "",
                filter_str,
            )
            if file_name:
                with open(file_name, "w", encoding="utf-8") as f:
                    f.write(self.get_template_content_for_save())
                self._auto_save_to = None
                self._auto_save_timer.stop()
        except Exception as e:
            logger.error("Error saving template: %s", e, exc_info=True)

    @top_level_handler
    def on_auto_save_templ(self):
        """Save the template."""
        try:
            filter_str = self.t(
                "templ.save-templ.filter", "Jinja2 Template Files (*.j2)"
            )
            file_name, _ = QFileDialog.getSaveFileName(
                self,
                self.t("templ.save-templ.t-auto", "Auto-save template"),
                "",
                filter_str,
            )
            if file_name:
                self._auto_save_to = file_name
                self._perform_auto_save()
        except Exception as e:
            logger.error("Error auto-saving template: %s", e, exc_info=True)

    @top_level_handler
    def on_save_as_html(self) -> None:
        """Save the HTML."""
        page: "WebEnginePage" = cast("WebEnginePage", self.c_viewer.page())
        assert page is not None

        def do_save_html(html: str, output_file_name: str):
            try:
                with open(output_file_name, "w", encoding="utf-8") as f:
                    f.write(html)
                parent_dir = os.path.dirname(output_file_name)
                if parent_dir:
                    QDesktopServices.openUrl(QUrl.fromLocalFile(parent_dir))
            except Exception as e:
                logger.error("Error saving HTML: %s", e, exc_info=True)
                QMessageBox.critical(
                    self,
                    self.t("templ.save-html.error", "Error"),
                    str(e),
                )

        file_name, _ = QFileDialog.getSaveFileName(
            self,
            self.t("templ.save-html.t", "Save HTML"),
            "",
            self.t("templ.save-html.filter", "HTML Files (*.html)"),
        )
        if file_name:
            page.toHtml(
                lambda html: (
                    do_save_html(html, file_name) if html is not None else None
                )
            )

    @top_level_handler
    def on_saved_as_pdf(self, file_path: str, result: bool):
        """Handle the result of the PDF saving operation."""
        if not result:
            self.show_error(
                self.t("templ.save-pdf.error", "Error"),
                self.t("templ.save-pdf.error-msg", "Error saving PDF"),
            )
            logger.error("Error saving PDF")
            return

        if file_path is None:
            self.show_error(
                self.t("templ.save-pdf.error", "Error"),
                self.t("templ.save-pdf.error-msg", "Error saving PDF"),
            )
            logger.error("Error saving PDF: file path is None")
            return

        QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))

    @top_level_handler
    def on_save_as_pdf(self) -> None:
        """Save the rendered content as a .pdf file."""
        page: "WebEnginePage" = cast("WebEnginePage", self.c_viewer.page())
        assert page is not None
        from exdrf_qt.controls.templ_viewer.save_pdf_dlg import SavePdfDialog

        dialog = SavePdfDialog(self.ctx, self)
        dialog.setFileMode(QFileDialog.AnyFile)
        dialog.setViewMode(QFileDialog.Detail)
        if dialog.exec_() == QFileDialog.Accepted:
            file_name = dialog.selectedFiles()[0]
            if file_name:
                # Ensure the file name ends with .pdf.
                _, ext = os.path.splitext(file_name)
                if ext != ".pdf":
                    file_name += ".pdf"

                # Attempt to save the PDF.
                try:
                    page_layout = dialog.get_page_layout()
                    page.printToPdf(file_name, page_layout)
                except Exception as e:
                    logger.error("Error saving PDF: %s", e, exc_info=True)
                    self.show_error(
                        self.t("templ.save-pdf.error", "Error"),
                        str(e),
                    )

    @top_level_handler
    def on_save_as_docx(self) -> None:
        """Save the rendered content as a .docx file."""
        # from html4docx import HtmlToDocx  # type: ignore

        page: "WebEnginePage" = cast("WebEnginePage", self.c_viewer.page())
        assert page is not None

        file_name, _ = QFileDialog.getSaveFileName(
            self,
            self.t("templ.save-docx.t", "Save DOCX"),
            "",
            self.t("templ.save-docx.filter", "DOCX Files (*.docx)"),
        )
        if file_name:
            converter = HtmlToDocxConverter(self.c_viewer)
            converter.export_to_docx(file_name)

    def show_variables_widget(self, visible: bool = True):
        """Show or hide the variables widget."""
        self.ac_toggle_vars.setChecked(visible)


DBM = TypeVar("DBM")


class RecordTemplViewer(TemplViewer, Generic[DBM]):
    """A template viewer that displays a database record."""

    record_id: Optional[RecIdType]
    db_model: Type[DBM]
    editor: Optional["ExdrfEditor"]
    editor_ctor: Optional[Type["ExdrfEditor"]]

    ac_new: Union[OpenCreatePac, None]
    ac_rem: Union[OpenDeletePac, None]
    ac_edit: Union[OpenEditPac, None]

    def __init__(
        self,
        db_model: Type[DBM],
        record_id: Optional[RecIdType] = None,
        has_new_action: bool = True,
        has_delete_action: bool = True,
        has_edit_action: bool = True,
        editor_ctor: Optional[Type["ExdrfEditor"]] = None,
        **kwargs,
    ):
        self.record_id = None
        self.db_model = db_model
        self.editor_ctor = editor_ctor
        self.editor = None
        super().__init__(
            var_bag=VarBag(),
            prevent_render=True,
            prevent_var_list=editor_ctor is not None,
            **kwargs,
        )
        self.create_crud_actions(
            has_new_action=has_new_action,
            has_delete_action=has_delete_action,
            has_edit_action=has_edit_action,
        )
        self.change_record(record_id)

        if editor_ctor is not None:
            self.ac_toggle_vars.setText(
                self.t("templ.editor.toggle", "Toggle Editor")
            )

    def change_record(self, record_id: Optional[RecIdType]) -> bool:
        """Change the record."""
        with self.prevent_render():
            self.record_id = record_id
            has_record = record_id is not None

            if has_record:
                result = self.populate()
            else:
                self.on_no_record()
                result = False

            self.ctx.set_window_title(self, self.windowTitle())
        # The rendering happens automatically in the prevent_render exit.
        return result

    def on_no_record(self):
        if self.ac_edit is not None:
            self.ac_edit.setEnabled(False)
        if self.ac_rem is not None:
            self.ac_rem.setEnabled(False)

    def on_with_record(self):
        if self.ac_edit is not None:
            self.ac_edit.setEnabled(True)
        if self.ac_rem is not None:
            self.ac_rem.setEnabled(True)

    def populate(self) -> bool:
        """Populate the variable bag with the fields of the database record."""
        with self.ctx.same_session() as session:
            record = self.read_record(session)
            if record is None:
                self.on_no_record()
                return False

            self.on_with_record()

            # Populate the variable bag.
            self.model.beginResetModel()
            try:
                self._populate_from_record(record)
                result = True
            except Exception as e:
                logger.error(
                    "Error populating variable bag: %s",
                    e,
                    exc_info=True,
                )
                self.show_exception(e, traceback.format_exc())
                result = False
            self.model.endResetModel()
            return result

    def _populate_from_record(self, record: DBM):
        """Populate the variable bag with the fields of the database record."""
        raise NotImplementedError("Not implemented")

    def _render_template(self, **kwargs) -> str:
        """The actual rendering of the template."""
        assert self._current_template is not None
        self._ensure_fresh_template()

        def do_field(fld, template_vars, record, session):
            try:
                # Access the attribute within the session context
                # This will trigger lazy loading if needed
                attr_value = getattr(record, fld.name)
                # Convert relationships to lists to detach from
                # session
                if isinstance(attr_value, (InstrumentedList, InstrumentedSet)):
                    # Convert to list to ensure it's loaded and
                    # detached from session. This will trigger
                    # lazy loading if not already loaded.
                    attr_value = list(attr_value)
                    try:
                        count = count_relationship(session, record, fld.name)
                    except Exception as e:
                        logger.error(
                            "Error counting relation %s in model " "%s: %s",
                            fld.name,
                            record.__class__.__name__,
                            e,
                            exc_info=True,
                        )
                        count = 0
                    count_name = f"{fld.name}_count"
                    template_vars[count_name] = count
                template_vars[fld.name] = attr_value
                logger.debug(
                    "fld.name: %s, type: %s",
                    fld.name,
                    type(attr_value),
                )
            except Exception as e:
                logger.error(
                    "Error accessing field %s: %s",
                    fld.name,
                    e,
                    exc_info=True,
                )
                # Set to None if we can't access it
                template_vars[fld.name] = None

        # Create a wrapper function that handles the session
        # This ensures the session is created in the worker thread
        def render_with_session():
            data = (
                self._render_worker.data
                if self._render_worker is not None
                else {}
            )
            existing = data.get("record", None)

            # Use new_session instead of same_session to ensure we get a
            # fresh session in the worker thread
            with self.ctx.new_session(add_to_stack=False) as session:
                with session.no_autoflush:
                    if existing is None:
                        record = (
                            None
                            if self.record_id is None
                            else self.read_record(session)
                        )
                        if record is None:
                            return self.t(
                                "templ.render.no-record",
                                "<p style='color: grey; font-style: italic;'>"
                                "No record found"
                                "</p>",
                            )
                    else:
                        # make_transient_to_detached(existing)
                        # session.add(existing)
                        # record = existing
                        record = session.merge(existing, load=True)

                    # Build a dictionary of values to pass to the template.
                    # We need to access all relationship attributes within the
                    # session context to ensure they're loaded.
                    template_vars = {}
                    template_vars.update(self.model.var_bag.as_dict)

                    # Refresh the variable bag with the fields of the database
                    # record. Access all attributes within the session context.
                    # Ensure the record is bound to this session.
                    for fld in self.model.var_bag.fields:
                        if fld.name == "record":
                            template_vars[fld.name] = record
                        elif isinstance(fld, CountField):
                            continue
                        else:
                            do_field(fld, template_vars, record, session)

                    # Render the template with all variables loaded.
                    assert self._current_template is not None
                    return self._current_template.render(
                        **template_vars,
                        **self.extra_context,
                        record=record,
                        api_point=self.ctx.data,  # type: ignore
                        list_route=self.get_list_route(),
                        create_route=self.get_create_route(),
                        edit_route=self.get_edit_route(),
                        view_route=self.get_view_route(),
                        delete_route=self.get_delete_route(),
                        **kwargs,
                    )

        return render_with_session()

    def read_record(self, session: "Session") -> Union[None, DBM]:
        """Read the database record indicated by the record ID.

        Args:
            session: The SQLAlchemy session.

        Returns:
            The database record.
        """
        raise NotImplementedError("Not implemented")

    def get_db_item_id(self, record: DBM) -> RecIdType:
        """Get the ID of the database item."""
        raise NotImplementedError("Not implemented")

    def construct_menu(
        self,
        ac_copy: QAction,
        ac_copy_link: QAction,
        ac_cut: QAction,
        ac_paste: QAction,
        ac_inspect: QAction,
    ):
        """Construct the context menu for the template viewer."""
        menu = QMenu()

        menu.addAction(ac_copy)
        menu.addAction(ac_copy_link)
        menu.addAction(ac_cut)
        menu.addAction(ac_paste)
        menu.addSeparator()
        self.add_other_view_actions(menu)
        menu.addAction(self.ac_switch_mode)
        menu.addAction(self.ac_toggle_vars)
        if None not in (self.ac_new, self.ac_rem, self.ac_edit):
            menu.addSeparator()
            if self.ac_new is not None:
                menu.addAction(self.ac_new)
            if self.ac_rem is not None:
                menu.addAction(self.ac_rem)
            if self.ac_edit is not None:
                menu.addAction(self.ac_edit)
        menu.addSeparator()
        menu.addAction(self.ac_save_as_html)
        menu.addAction(self.ac_save_as_pdf)
        menu.addAction(self.ac_save_as_docx)
        menu.addSeparator()
        menu.addAction(self.ac_refresh)
        menu.addAction(ac_inspect)

        return menu

    @property
    def base_route(self) -> str:
        """The base route for the list."""
        try:
            m_name = self.db_model.__name__
        except Exception:
            m_name = "unknown"
        return f"exdrf://navigation/resource/{m_name}"

    def create_crud_actions(
        self,
        has_new_action: bool = True,
        has_delete_action: bool = True,
        has_edit_action: bool = True,
    ):
        """Create the CRUD actions."""
        try:
            self.get_deletion_function()
            self.get_current_record_selector()
            has_delete = True
        except NotImplementedError:
            has_delete = False
        except Exception:
            has_delete = True

        self.ac_new = (
            OpenCreatePac(
                label=self.t("sq.common.new", "New"),
                ctx=self.ctx,
                provider=self,
                menu_or_parent=self,
            )
            if has_new_action
            else None
        )
        if has_delete and has_delete_action:
            self.ac_rem = OpenDeletePac(
                label=self.t("sq.common.del", "Remove"),
                ctx=self.ctx,
                provider=self,
                menu_or_parent=self,
            )
        else:
            self.ac_rem = None

        self.ac_edit = (
            OpenEditPac(
                label=self.t("sq.common.edit", "Edit"),
                ctx=self.ctx,
                provider=self,
                menu_or_parent=self,
            )
            if has_edit_action
            else None
        )

    def get_list_route(self) -> Union[None, str]:
        return f"{self.base_route}"

    def get_create_route(self) -> Union[None, str]:
        return f"{self.base_route}/create"

    def get_edit_route(self) -> Union[None, str]:
        if self.record_id is None:
            return None
        return f"{self.base_route}/{self.record_id}/edit"

    def get_view_route(self) -> Union[None, str]:
        if self.record_id is None:
            return None
        return f"{self.base_route}/{self.record_id}"

    def get_delete_route(self) -> Union[None, str]:
        if self.record_id is None:
            return None
        return f"{self.base_route}/{self.record_id}/delete"

    def get_current_record_selector(self) -> Union[None, "Select"]:
        raise NotImplementedError(
            "exdrf_qt.controls.crud_actions.RouteProvider requires an "
            "implementation of this function in order to be able to delete "
            "records"
        )

    def get_deletion_function(
        self,
    ) -> Union[None, Callable[[Any, "Session"], bool]]:
        raise NotImplementedError(
            "exdrf_qt.controls.crud_actions.RouteProvider requires an "
            "implementation of this function in order to be able to delete "
            "records"
        )

    def side_panel_visibility_changed(self, visible: bool):
        if not visible:
            return

        if self.editor_ctor is not None and self.editor is None:
            editor = self.editor_ctor(
                ctx=self.ctx,
                db_model=self.db_model,
                record_id=self.record_id,
                parent=self,
            )
            self.editor = editor
            self.lay_side_panel.insertWidget(0, self.editor)
            editor.destroyed.connect(self.on_editor_destroyed)
            editor.controlChanged.connect(self.render_template_later)

    def on_editor_destroyed(self):
        w = self.c_splitter.widget(1)
        if w is not None:
            w.setVisible(False)
            return
        self.editor = None

    def _adjust_render_thread(self):
        """Adjust the render thread."""
        if self.editor is not None and self._render_worker is not None:
            self._render_worker.data["record"] = self.editor.db_record(
                save=False
            )
