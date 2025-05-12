import os
from importlib import resources
from typing import TYPE_CHECKING, Any, Callable, List, Optional, cast

from attrs import define, field
from exdrf_al.connection import DbConn
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QMessageBox

from exdrf_qt.controls.seldb.sel_db import SelectDatabaseDlg
from exdrf_qt.worker import Relay, Work

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QWidget  # noqa: F401
    from sqlalchemy import Select  # noqa: F401


@define
class QtContext(DbConn):
    """Provides a context for Qt application classes.

    It is used to manage the database and the application state.
    """

    top_widget: "QWidget" = cast("QWidget", None)
    work_relay: Optional[Relay] = None
    asset_sources: List[str] = field(factory=lambda: ["exdrf_qt.assets"])

    def create_window(self, w: "QWidget"):
        """Creates a stand-alone window.

        The default implementation assumes that the `top_widget` has a
        `mdi_area` attribute that is an instance of `QMdiArea`. Reimplement
        this method if you want to use a different type of window manager.

        Args:
            w: The widget to create a window for.
        """
        if not w:
            return
        result = self.top_widget.mdi_area.addSubWindow(w)
        w.show()
        return result

    def close_window(self, w: "QWidget"):
        """Closes a stand-alone window.

        The default implementation assumes that the `top_widget` has a
        `mdi_area` attribute that is an instance of `QMdiArea`. Reimplement
        this method if you want to use a different type of window manager.

        Args:
            w: The widget to close.
        """
        if not w:
            return
        self.top_widget.mdi_area.removeSubWindow(w.parent())
        w.close()
        w.deleteLater

    def set_db_string(self, c_string: str, schema: str = "public") -> None:
        """Sets the database connection string.

        All current connections will be closed. The worker thread will be
        asked to stop and a new relay will be created.

        Args:
            c_string: The database connection string.
        """
        self.close()
        if self.work_relay:
            self.work_relay.stop()
            self.work_relay.deleteLater()
            self.work_relay = None

        if c_string:
            self.work_relay = Relay(
                cn=DbConn(c_string=c_string, schema=schema),
                parent=self.top_widget,
            )

        self.c_string = c_string
        self.schema = schema

    def push_work(
        self,
        statement: "Select",
        callback: Callable[["Work"], None],
        req_id: Optional[Any] = None,
    ) -> "Work":
        """Pushes work to the worker thread.

        The function makes sure that a connection string is set and that the
        worker thread is running. If the connection string is not set, it will
        prompt the user for one.

        Args:
            statement: The SQLAlchemy select statement to execute.
            callback: The callback function to call with the result.
            req_id: An optional request ID to identify the work. If one is not
                provided, a new one will be generated.
        """
        if self.work_relay is None:
            if self.ensure_db_conn():
                self.work_relay = Relay(
                    cn=DbConn(self.c_string), parent=self.top_widget
                )
            else:
                raise RuntimeError(
                    "Attempted to push work but no database connection "
                    "string was provided"
                )
        return self.work_relay.push_work(
            statement=statement, callback=callback, req_id=req_id
        )

    def show_error(
        self,
        message: str,
        title: str = "Error",
    ):
        """Shows an error message.

        Args:
            title: The title of the error message.
            message: The error message.
        """
        QMessageBox.critical(
            self.top_widget,
            title,
            message,
        )

    def ensure_db_conn(self):
        """Ensures that the database connection is set.

        If the connection string is not set, the function looks into the
        `EXDRF_DB_CONN_STRING` variable. It will prompt the user for the
        connection string if it is not set in the environment variable.

        Returns:
            True if the connection string is set, False otherwise.
        """
        if not self.c_string:
            # Attempt to use the environment variable first.
            env_string = os.environ.get("EXDRF_DB_CONN_STRING", None)
            if env_string:
                s_string = os.environ.get("EXDRF_DB_SCHEMA", "public")
                self.set_db_string(env_string, s_string)
                return True

            # Ask the user for the connection string.
            SelectDatabaseDlg.change_connection_str(self)

        return bool(self.c_string)

    def get_icon(self, name: str) -> "QIcon":
        """Get an icon by name.

        The function look in the packages listed in `asset_sources` for the
        icon file. If the icon is not found, it will look for the icon in the
        current working directory.

        Args:
            name: The name of the icon file (without the .png extension)
                or the full path to the icon file.

        Throws:
            FileNotFoundError: If the icon file is not found in any of the
                asset sources or in the current working directory.
        """

        for asset in self.asset_sources:
            # Locate the resource.
            icon_path = resources.files(asset).joinpath(f"{name}.png")

            # Use as_file to ensure compatibility with zipped/wheel packages
            if icon_path.is_file():
                with resources.as_file(icon_path) as icon_file:
                    if not icon_file.exists():
                        raise FileNotFoundError(
                            f"Icon file `{name}.png` not found in {asset}"
                        )
                    return QIcon(str(icon_file))

        if os.path.isfile(name):
            # If the name is a file path, return the icon directly.
            return QIcon(name)

        raise FileNotFoundError(
            f"Icon file `{name}.png` not found in any asset source"
        )

    def t(self, key: str, d: str, **kwargs: Any) -> str:
        """Translates a string using the context.

        The default implementation does not perform any translation. It simply
        formats the default string with the given arguments.

        Args:
            key: The translation key.
            d: The default string if translation is not found.
            **kwargs: Additional arguments for translation string.

        Returns:
            The translated string.
        """
        return d.format(**kwargs)

    def bootstrap(self):
        """Prepare the database for use."""
        from exdrf_al.base import Base

        self.create_all_tables(Base)
