import logging
import os
from typing import TYPE_CHECKING, Tuple

from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QFileDialog, QMessageBox

from exdrf_qt.context_use import QtUseContext
from exdrf_qt.controls.seldb.sel_db_ui import Ui_SelectDatabase

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401


logger = logging.getLogger(__name__)


class SelectDatabaseDlg(QDialog, Ui_SelectDatabase, QtUseContext):
    """A dialog that allows the user to select a database."""

    def __init__(self, ctx: "QtContext", **kwargs):
        """Initialize the editor widget."""
        super().__init__(**kwargs)
        self.ctx = ctx
        self.setup_ui(self)
        self.c_backend.addItem("PostgreSQL", "postgresql")
        self.c_backend.addItem("MySQL", "mysql")
        self.c_backend.addItem("Oracle", "oracle")
        self.c_backend.addItem("SQL Server", "mssql")

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
        self.btn_bootstrap.clicked.connect(self.bootstrap)

        # Notice changes by the user.
        self.c_backend.currentIndexChanged.connect(self.content_changed)
        self.c_db_name.textChanged.connect(self.content_changed)
        self.c_file_path.textChanged.connect(self.content_changed)
        self.c_host.textChanged.connect(self.content_changed)
        self.c_pass.textChanged.connect(self.content_changed)
        self.c_port.textChanged.connect(self.content_changed)
        self.c_schema.textChanged.connect(self.content_changed)
        self.c_username.textChanged.connect(self.content_changed)
        self.main_tab.currentChanged.connect(self.content_changed)

    def content_changed(self):
        if self.is_local:
            self.btn_bootstrap.setEnabled(
                len(self.c_file_path.text().strip()) > 0
            )
        else:
            self.btn_bootstrap.setEnabled(
                len(self.c_db_name.text().strip()) > 0
                and len(self.c_host.text().strip()) > 0
                and len(self.c_port.text().strip()) > 0
                and len(self.c_username.text().strip()) > 0
            )

    @property
    def is_local(self):
        return bool(self.main_tab.currentWidget() is self.tab_local)

    @property
    def con_str(self) -> str:
        """Return the connection string."""
        if self.is_local:
            return f'sqlite:///{self.c_file_path.text().replace("\\", "/")}'
        else:
            backend = self.c_backend.currentData()
            host = self.c_host.text().strip()
            port = self.c_port.text().strip()
            user = self.c_user.text().strip()
            password = self.c_password.text().strip()
            db_name = self.c_db_name.text().strip()
            return f"{backend}://{user}:{password}@{host}:{port}/{db_name}"

    @con_str.setter
    def con_str(self, con_str: str):
        """Set the connection string."""
        self.set_con_str(con_str)

    @property
    def schema(self) -> str:
        """Return the schema name."""
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

    def set_con_str(self, con_str: str):
        """Set the connection string."""
        if con_str.startswith("sqlite:///"):
            self.main_tab.setCurrentWidget(self.tab_local)
            self.c_file_path.setText(con_str[10:])
        else:
            self.main_tab.setCurrentWidget(self.tab_remote)
            backend, rest = con_str.split("://", maxsplit=1)
            user, rest = rest.split("@", maxsplit=1)
            password, rest = user.split(":", maxsplit=1)
            host, rest = rest.split(":", maxsplit=1)
            port, db_name = rest.split("/", maxsplit=1)
            self.c_backend.setCurrentText(backend)
            self.c_user.setText(user)
            self.c_password.setText(password)
            self.c_host.setText(host)
            self.c_port.setText(port)
            self.c_db_name.setText(db_name)

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

    @classmethod
    def change_connection_str(cls, ctx: "QtContext") -> Tuple[str, str]:
        """Ask the user for the connection string.."""
        dlg = cls(parent=ctx.top_widget, ctx=ctx)
        if ctx.c_string:
            dlg.set_con_str(ctx.c_string)
        if ctx.schema:
            dlg.schema = ctx.schema
        if dlg.exec_() == dlg.Accepted:
            ctx.set_db_string(dlg.con_str, dlg.schema)
        return ctx.c_string, ctx.schema

    def bootstrap(self):
        """Bootstrap the database."""
        local_ctx = self.ctx.__class__(
            c_string=self.con_str,
            schema=self.schema,
            top_widget=self.ctx.top_widget,
            work_relay=None,
            asset_sources=self.ctx.asset_sources,
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
            return

        try:
            local_ctx.bootstrap()
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
            return

        QMessageBox.information(
            self,
            self.ctx.t("cmn.info", "Info"),
            self.ctx.t("cmn.db.bootstrap-success", "Bootstrap successful!"),
        )
