import logging
import os
from typing import TYPE_CHECKING, Any, List, Optional, Tuple, Union
from uuid import uuid4

from PyQt5.QtCore import QModelIndex, Qt
from PyQt5.QtWidgets import (
    QAction,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QMessageBox,
    QPushButton,
)

from exdrf_qt.context_use import QtUseContext
from exdrf_qt.controls.seldb.db_version_worker import DbVersionCheckerWorker
from exdrf_qt.controls.seldb.manage_model import (
    COL_NAME,
    DatabaseConfigModel,
    DbVersionInfo,
)
from exdrf_qt.controls.seldb.sel_db_ui import Ui_SelectDatabase
from exdrf_qt.controls.seldb.utils import (
    CON_TYPE_LOCAL,
    CON_TYPE_REMOTE,
)
from exdrf_qt.utils.tlh import top_level_handler

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401


logger = logging.getLogger(__name__)


class SelectDatabaseDlg(QDialog, Ui_SelectDatabase, QtUseContext):
    """A dialog that allows the user to select a database."""

    ac_load: QAction
    ac_rename: QAction
    ac_remove: QAction
    save_btn: QPushButton
    ok_btn: QPushButton
    _config_model: DatabaseConfigModel

    def __init__(self, ctx: "QtContext", **kwargs):
        """Initialize the editor widget."""
        super().__init__(**kwargs)
        self.ctx = ctx
        self.setup_ui(self)
        self._setup_backend_combo()
        self._setup_manager()

        ok_btn = self.bbox.button(QDialogButtonBox.StandardButton.Ok)
        assert ok_btn is not None
        self.ok_btn = ok_btn
        self.ok_btn.setEnabled(False)

        begin = os.environ.get("EXDRF_DB_CONN_STRING", None)
        if begin:
            self.set_con_str(begin)
        else:
            self.main_tab.setCurrentWidget(self.tab_local)
        s_string = os.environ.get("EXDRF_DB_SCHEMA", "public")
        self.c_schema.setText(s_string)

        self.c_browse_file.clicked.connect(self.on_browse_file)

        self.btn_bootstrap = self.bbox.addButton(
            self.ctx.t("cmn.bootstrap", "Bootstrap"),
            QDialogButtonBox.ButtonRole.ActionRole,
        )
        assert self.btn_bootstrap is not None
        self.btn_bootstrap.setIcon(self.get_icon("sitemap_application_blue"))
        self.btn_bootstrap.clicked.connect(self.on_bootstrap)  # type: ignore

        # Notice changes by the user.
        self.c_db_name.textChanged.connect(self.on_content_changed)
        self.c_file_path.textChanged.connect(self.on_content_changed)
        self.c_host.textChanged.connect(self.on_content_changed)
        self.c_pass.textChanged.connect(self.on_content_changed)
        self.c_port.textChanged.connect(self.on_content_changed)
        self.c_schema.textChanged.connect(self.on_content_changed)
        self.c_username.textChanged.connect(self.on_content_changed)
        self.main_tab.currentChanged.connect(self.on_content_changed)
        self.c_backend.currentIndexChanged.connect(self.on_content_changed)
        self.c_list.selectionModel().selectionChanged.connect(
            self.on_content_changed
        )

    def _setup_backend_combo(self):
        self.c_backend.addItem(
            self.t("cmn.db.postgresql", "PostgreSQL"), "postgresql"
        )
        self.c_backend.addItem(self.t("cmn.db.mysql", "MySQL"), "mysql")
        self.c_backend.addItem(self.t("cmn.db.oracle", "Oracle"), "oracle")
        self.c_backend.addItem(
            self.t("cmn.db.sqlserver", "SQL Server"), "mssql"
        )

    def _setup_manager(self):
        # Create and set the model
        self._config_model = DatabaseConfigModel(self.ctx, self)
        self.c_list.setModel(self._config_model)

        self.ac_load = QAction(
            self.get_icon("folder"),
            self.t("cmn.load", "Load"),
            self.c_list,
        )
        self.ac_load.triggered.connect(self.on_mng_load)

        self.ac_rename = QAction(
            self.get_icon("edit_button"),
            self.t("cmn.rename", "Rename"),
            self.c_list,
        )
        self.ac_rename.triggered.connect(self.on_mng_rename)

        self.ac_remove = QAction(
            self.get_icon("cross"),
            self.t("cmn.remove", "Remove"),
            self.c_list,
        )
        self.ac_remove.triggered.connect(self.on_mng_remove)

        self.c_list.addAction(self.ac_load)
        self.c_list.addAction(self.ac_rename)
        self.c_list.addAction(self.ac_remove)
        self.c_list.setContextMenuPolicy(
            Qt.ContextMenuPolicy.ActionsContextMenu
        )

        self.save_btn = QPushButton(self.t("cmn.save", "Save"))
        self.bbox.addButton(
            self.save_btn, QDialogButtonBox.ButtonRole.ActionRole
        )
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self.on_save_crt)
        self.save_btn.setIcon(self.get_icon("file_save_as"))

        # Connect selection model signals
        self.c_list.selectionModel().selectionChanged.connect(
            self.on_mng_current_changed
        )
        # Connect model dataChanged signal
        self._config_model.dataChanged.connect(self.on_mng_item_changed)

        # Start version checker
        self._start_version_checker()

    def _start_version_checker(self):
        """Start the background thread to check database versions."""
        migrations_dir = os.environ.get("EXDRF_DB_MIGRATIONS_DIR", None)
        if not migrations_dir:
            # If migrations dir is not set, we can't check versions
            return

        # Get all configs from the model
        configs = []
        for i in range(self._config_model.rowCount()):
            index = self._config_model.index(i, 0)
            config = self._config_model.get_config(index)
            if config:
                configs.append(config)

        # Create and start the worker thread
        self._version_worker = DbVersionCheckerWorker(
            configs=configs,
            migrations_dir=migrations_dir,
            parent=self,
        )
        self._version_worker.version_checked.connect(self._on_version_checked)
        self._version_worker.start()

    def _on_version_checked(
        self, config_id: str, version_info: "DbVersionInfo"
    ):
        """Handle version check result from worker thread.

        Args:
            config_id: The configuration ID.
            version_info: Dictionary with version information.
        """
        self._config_model.update_db_version_info(config_id, version_info)

    @top_level_handler
    def on_mng_item_changed(
        self,
        top_left: QModelIndex,
        bottom_right: QModelIndex,
        roles: Optional[List[int]] = None,
    ):
        """Handle the item changed event.

        Args:
            top_left: Top-left index of changed items.
            bottom_right: Bottom-right index of changed items.
            roles: List of data roles that changed.
        """
        # The model already updates the settings in setData, so we don't
        # need to do anything here. This method is kept for potential
        # future use or side effects.

    @top_level_handler
    def on_mng_current_changed(self):
        """Handle the current item changed event.

        We disable the actions when there is no current item.
        """
        index = self._get_current_index()
        has_selection = index.isValid()
        self.ac_load.setEnabled(has_selection)
        self.ac_rename.setEnabled(has_selection)
        self.ac_remove.setEnabled(has_selection)

    @top_level_handler
    def on_mng_load(self):
        """Load the connection from the settings manager."""
        index = self._get_current_index()
        if not index.isValid():
            return
        config = self._config_model.get_config(index)
        if config:
            self.set_con_str(config["c_string"])
            self.c_schema.setText(config.get("schema", ""))

    @top_level_handler
    def on_mng_rename(self):
        """Rename the current connection."""
        index = self._get_current_index()
        if not index.isValid():
            return

        # Start editing the first column
        name_index = self._config_model.index(index.row(), COL_NAME)
        self.c_list.edit(name_index)

    @top_level_handler
    def on_mng_remove(self):
        """Remove the current connection."""
        index = self._get_current_index()
        if not index.isValid():
            return

        config = self._config_model.get_config(index)
        if not config:
            return

        # Get the current name
        old_name = config.get("name", "")

        # Ask for confirmation
        reply = QMessageBox.question(
            self,
            self.t("cmn.remove", "Remove"),
            self.t(
                "cmn.db.remove-confirm",
                "Are you sure you want to remove {name}?",
                name=old_name,
            ),
        )
        if reply == QMessageBox.StandardButton.Yes:
            # Remove the item from the model (which also updates settings)
            self._config_model.remove_config(index)

    @top_level_handler
    def on_save_crt(self):
        """Save the current connection to the settings."""
        if self.is_local:
            self._save_crt(local=True, c_string=self.local_con_str)
        elif self.is_remote:
            self._save_crt(local=False, c_string=self.remote_con_str)

    def _save_crt(self, local: bool, c_string: str):
        """Save the current connection to the settings.

        Args:
            local: Whether the connection is local.
            c_string: The connection string.
        """
        name = self.t("cmn.db.new_name", "New Connection")
        kind = CON_TYPE_LOCAL if local else CON_TYPE_REMOTE
        schema = self.c_schema.text().strip()
        config_id = str(uuid4())

        # Add the configuration to the model (which also updates settings)
        new_index = self._config_model.add_config(
            config_id=config_id,
            name=name,
            kind=kind,
            c_string=c_string,
            schema=schema,
        )

        # Make the management tab the current tab.
        self.main_tab.setCurrentWidget(self.tab_manage)

        # Select the new item and begin editing
        self.c_list.setCurrentIndex(new_index)
        self.c_list.edit(new_index)

    @top_level_handler
    def on_content_changed(self):
        """Handle the content changed event from all controls."""
        if self.is_local:
            valid = len(self.c_file_path.text().strip()) > 0
            self.btn_bootstrap.setEnabled(valid)
            self.save_btn.setEnabled(valid)
            self.ok_btn.setEnabled(valid)
        elif self.is_remote:
            valid = (
                len(self.c_db_name.text().strip()) > 0
                and len(self.c_host.text().strip()) > 0
                and len(self.c_port.text().strip()) > 0
                and len(self.c_username.text().strip()) > 0
            )
            self.btn_bootstrap.setEnabled(valid)
            self.save_btn.setEnabled(valid)
            self.ok_btn.setEnabled(valid)
        elif self.is_manager:
            valid = self.selected_config is not None
            self.btn_bootstrap.setEnabled(valid)
            self.save_btn.setEnabled(valid)
            self.ok_btn.setEnabled(valid)
        else:
            raise ValueError("Invalid tab")

    @property
    def is_local(self):
        return bool(self.main_tab.currentWidget() is self.tab_local)

    @property
    def is_remote(self):
        return bool(self.main_tab.currentWidget() is self.tab_remote)

    @property
    def is_manager(self):
        return bool(self.main_tab.currentWidget() is self.tab_manage)

    @property
    def local_con_str(self) -> str:
        return f'sqlite:///{self.c_file_path.text().replace("\\", "/")}'

    @property
    def selected_id(self) -> str:
        if self.is_manager:
            index = self._get_current_index()
            if index.isValid():
                item_id = self._config_model.data(
                    index, Qt.ItemDataRole.UserRole
                )
                if item_id:
                    return str(item_id)
        return ""

    @property
    def selected_config(self) -> Union[None, dict[str, Any]]:
        if self.is_manager:
            index = self._get_current_index()
            if index.isValid():
                return self._config_model.get_config(index)
        return None

    @property
    def remote_con_str(self) -> str:
        backend = self.c_backend.currentData()
        host = self.c_host.text().strip()
        port = self.c_port.text().strip()
        user = self.c_username.text().strip()
        password = self.c_pass.text().strip()
        db_name = self.c_db_name.text().strip()
        return f"{backend}://{user}:{password}@{host}:{port}/{db_name}"

    @property
    def saved_con_str(self) -> str:
        config = self.selected_config
        if config:
            return config["c_string"]
        else:
            return ""

    @property
    def con_str(self) -> str:
        """Return the connection string."""
        if self.is_local:
            return self.local_con_str
        elif self.is_remote:
            return self.remote_con_str
        elif self.is_manager:
            return self.saved_con_str
        else:
            raise ValueError("Invalid tab")

    @con_str.setter
    def con_str(self, con_str: str):
        """Set the connection string."""
        self.set_con_str(con_str)

    @property
    def schema(self) -> str:
        """Return the schema name."""
        if self.is_manager:
            config = self.selected_config
            if config:
                return config["schema"]
            else:
                return "public"
        else:
            schema = self.c_schema.text().strip()
            if schema:
                return schema
            else:
                return "public"

    @schema.setter
    def schema(self, schema: str):
        """Set the schema name."""
        if schema:
            self.c_schema.setText(schema)
        else:
            self.c_schema.clear()

    def _get_current_index(self) -> QModelIndex:
        """Get the current selected index from the tree view.

        Returns:
            The current model index, or an invalid index if nothing is
            selected.
        """
        selection_model = self.c_list.selectionModel()
        if not selection_model:
            return QModelIndex()
        indexes = selection_model.selectedIndexes()
        if indexes:
            # Return the first selected index (row, column 0)
            return self._config_model.index(indexes[0].row(), 0)
        return QModelIndex()

    def set_con_str(self, con_str: str):
        """Set the connection string."""
        from exdrf_qt.controls.seldb.utils import parse_sqlalchemy_conn_str

        try:
            if con_str.startswith("sqlite:///"):
                self.main_tab.setCurrentWidget(self.tab_local)
                self.c_file_path.setText(con_str[10:])
            else:
                self.main_tab.setCurrentWidget(self.tab_remote)

                result = parse_sqlalchemy_conn_str(con_str)
                self.c_backend.setCurrentText(result["host"])
                self.c_username.setText(result["username"])
                self.c_pass.setText(result["password"])
                self.c_host.setText(result["host"])
                self.c_port.setText(result["port"])
                self.c_db_name.setText(result["database"])
        except Exception as e:
            logger.error("Failed to set connection string", exc_info=True)
            self.ctx.show_error(
                title=self.ctx.t("cmn.error", "Error"),
                message=self.ctx.t(
                    "cmn.db.err-set-con-str",
                    "Failed to set connection string: {err}",
                    err=str(e),
                ),
            )

    @top_level_handler
    def on_browse_file(self):
        """Browse for a file."""

        crt_dir = self.c_file_path.text().strip()
        if len(crt_dir) > 0:
            crt_dir = os.path.dirname(crt_dir)
            if not os.path.isdir(crt_dir):
                crt_dir = ""

        if not crt_dir:
            crt_dir = os.getcwd()

        filename, _ = QFileDialog.getSaveFileName(
            self,
            self.t("cmn.db.select-db-file", "Select Database File"),
            crt_dir,
            self.t(
                "cmn.db.select-db-filter",
                "SQL & Database Files (*.sqlite3 *.sqlite *.db);;All Files (*)",
            ),
        )
        if filename:
            self.c_file_path.setText(filename)

    @top_level_handler
    def on_bootstrap(self, suppress_success_message: bool = False) -> bool:
        """Bootstrap the database."""
        local_ctx = self.ctx.__class__(  # type: ignore
            c_string=self.con_str,
            schema=self.schema,
            top_widget=self.ctx.top_widget,
            work_relay=None,
            asset_sources=self.ctx.asset_sources,
            auto_migrate=False,
        )
        try:
            local_ctx.connect()
        except Exception as e:
            self.ctx.show_error(
                title=self.ctx.t("cmn.error", "Error"),
                message=self.ctx.t(
                    "cmn.db.err-connect",
                    "Failed to connect to the database using {cons}: {err}",
                    cons=local_ctx.c_string,
                    err=str(e),
                ),
            )
            logger.error(
                "Failed to connect to the database: %s", str(e), exc_info=True
            )
            return False

        try:
            if not local_ctx.bootstrap():
                return False
        except Exception as e:
            self.ctx.show_error(
                title=self.ctx.t("cmn.error", "Error"),
                message=self.ctx.t(
                    "cmn.db.err-bootstrap",
                    "Failed to bootstrap the database: {err}",
                    err=str(e),
                ),
            )
            logger.error(
                "Failed to bootstrap the database: %s", str(e), exc_info=True
            )
            return False

        if not suppress_success_message:
            QMessageBox.information(
                self,
                self.ctx.t("cmn.info", "Info"),
                self.ctx.t("cmn.db.bootstrap-success", "Bootstrap successful!"),
            )
        return True

    @classmethod
    def change_connection_str(cls, ctx: "QtContext") -> Tuple[str, str]:
        """Ask the user for the connection string."""
        dlg = cls(parent=ctx.top_widget, ctx=ctx)
        if ctx.c_string:
            dlg.set_con_str(ctx.c_string)
        if ctx.schema:
            dlg.schema = ctx.schema
        if dlg.exec_() == dlg.Accepted:
            ctx.set_db_string(dlg.con_str, dlg.schema)
        return ctx.c_string, ctx.schema
