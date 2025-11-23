import logging
import logging.config
import os
from contextlib import contextmanager
from importlib import resources
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Union,
    cast,
    overload,
)

from attrs import define, field
from exdrf_al.connection import DbConn
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QMessageBox
from pyrsistent import thaw

from exdrf_qt.controls.seldb.sel_db import SelectDatabaseDlg
from exdrf_qt.local_settings import LocalSettings
from exdrf_qt.plugins import exdrf_qt_pm
from exdrf_qt.utils.attr_dict import AttrDict
from exdrf_qt.utils.plugins import safe_hook_call
from exdrf_qt.utils.router import ExdrfRouter
from exdrf_qt.utils.sql_formatter import SQLPrettyFormatter  # noqa: F401
from exdrf_qt.worker import Relay, Work

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QWidget  # noqa: F401
    from sqlalchemy import Select  # noqa: F401
    from sqlalchemy.orm import Session

# Default logging configuration
DEFAULT_LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "sql-pretty": {
            "()": "exdrf_qt.context.SQLPrettyFormatter",
            "format": (
                "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d: "
                "%(message)s"
            ),
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "sql-pretty",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": "sql-pretty",
            "filename": "exdrf.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "encoding": "utf8",
        },
    },
    "loggers": {
        "": {  # Root logger
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": True,
        },
    },
}


@define
class QtContext(DbConn):
    """Provides a context for Qt application classes.

    It is used to manage the database and the application state.

    Attributes:
        top_widget: The main widget of the application. This will be the default
            parent for widgets.
        work_relay: The relay for the worker thread. Provides the ability for
            the application to retrieve data from the database asynchronously.
        asset_sources: The list of asset sources to search for icons.
        stg: The local read-write settings.
        overrides: A dictionary of general-purpose overrides. You add values
            through the `set_ovr` method and retrieve them through the
            `get_ovr` method.
        data: A dictionary of general-purpose data. Passes into the
            api_point variable to the templates.
        router: The router for the application. Provides the ability for
            the application to open widgets using only a string url.
    """

    top_widget: "QWidget" = cast("QWidget", None)
    work_relay: Optional[Relay] = None
    asset_sources: List[str] = field(factory=lambda: ["exdrf_qt.assets"])
    stg: LocalSettings = field(factory=LocalSettings)
    _overrides: Dict[str, Any] = field(factory=dict)
    data: AttrDict = field(factory=AttrDict)
    router: "ExdrfRouter" = field(default=None)

    def __attrs_post_init__(self):
        if self.router is None:
            self.router = ExdrfRouter(
                ctx=self,
                base_path="exdrf://navigation/resource",
            )

        self.setup_logging()

        # Attempt to load the last used connection from settings before
        # notifying plugins, so they can find an initialized DB context.
        if not self.c_string:
            try:
                self._load_last_used_db_config()
            except Exception as e:
                logging.getLogger(__name__).error(
                    "Failed to load last used DB config: %s", e, exc_info=True
                )

        # Inform plugins that the context has been created.
        safe_hook_call(exdrf_qt_pm.hook.context_created, context=self)

    def create_window(self, w: "QWidget", title: str):
        """Creates a stand-alone window.

        The default implementation assumes that the `top_widget` has a
        `mdi_area` attribute that is an instance of `QMdiArea`. Reimplement
        this method if you want to use a different type of window manager.

        Args:
            w: The widget to create a window for.
            title: The title of the window.
        """
        if not w:
            return
        result = self.top_widget.mdi_area.addSubWindow(w)
        w.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        w.show()
        w.setWindowTitle(title)
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

    def set_window_title(self, w: "QWidget", title: str):
        """Sets the window title.

        Args:
            w: The widget to set the title for.
            title: The title to set.
        """
        w.setWindowTitle(title)
        for subwindow in self.top_widget.mdi_area.subWindowList():
            s_widget = subwindow.widget()
            if s_widget == w:
                subwindow.setWindowTitle(title)
                self.top_widget.mdi_area.setActiveSubWindow(subwindow)
                break

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

        self.c_string = c_string  # type: ignore
        self.schema = schema  # type: ignore
        logging.getLogger(__name__).debug(
            "Database connection string set to %s with schema %s",
            self.c_string,
            self.schema,
        )

        # Persist the current connection id for next startup.
        try:
            current_id = self.current_db_setting_id()
            if current_id:
                self.stg.set_setting("exdrf.db.crt_connection", current_id)
        except Exception as e:
            logging.getLogger(__name__).error(
                "Failed to persist current DB config id: %s", e, exc_info=True
            )

    def db_config_id(self) -> str:
        """Get the ID of the current database configuration."""
        return self.stg.get_db_configs()[0]["id"]

    @overload
    def push_work(self, work: "Work") -> "Work": ...

    @overload
    def push_work(  # type: ignore[misc, assignment]
        self,
        statement: "Select",
        callback: Callable[["Work"], None],
        req_id: Optional[Any] = None,
        use_unique: bool = False,
    ) -> "Work": ...

    def push_work(  # type: ignore[misc, assignment]
        self,
        statement_or_work: Any,
        callback: Any = None,
        req_id: Optional[Any] = None,
        use_unique: bool = False,
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
        if isinstance(statement_or_work, Work):
            return self.work_relay.push_work(statement_or_work)
        else:
            assert callback is not None and req_id is not None
            return self.work_relay.push_work(
                statement=cast("Select", statement_or_work),
                callback=cast(Callable[["Work"], None], callback),
                req_id=req_id,
                use_unique=use_unique,
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

    def bootstrap(self) -> bool:
        """Prepare the database for use."""
        from exdrf_al.base import Base

        self.create_all_tables(Base)
        return True

    def setup_logging(self):
        """Setup logging."""
        log_stg = self.stg.get_setting("logging")
        if log_stg is None:
            log_stg = DEFAULT_LOGGING.copy()
            log_stg["handlers"]["file"]["filename"] = os.path.join(
                os.path.dirname(self.stg.settings_file()), "exdrf.log"
            )
            self.stg.set_setting("logging", log_stg)

        # Apply the configuration
        logging.config.dictConfig(thaw(log_stg))

        logger = logging.getLogger(__name__)
        logger.debug("Logging has been setup")

    def get_ovr(
        self,
        key: str,
        default: Any = None,
        exception_if_missing: bool = False,
    ) -> Any:
        """Get an override value.

        Args:
            key: The key to get the override for.
            default: The default value if the key is not found.
            exception_if_missing: If True, an exception will be raised if the
                key is not found.
        """
        ovr = self._overrides.get(key, None)
        if ovr is None:
            if exception_if_missing:
                raise ValueError(f"Override {key} not found")
            ovr = default
        return ovr

    def get_c_ovr(self, key: str, default, *args, **kwargs) -> Any:
        """Get then evaluate a function.

        Args:
            key: The key to get the override for.
            default: The function to call to get the default value.
            *args: Additional arguments for the default function.
            **kwargs: Additional keyword arguments for the default function.
        """
        ovr = self._overrides.get(key, None)
        if ovr is None:
            ovr = default(*args, **kwargs)
        else:
            ovr = ovr(*args, **kwargs)
        return ovr

    def set_ovr(self, key: str, value: Any, exception_if_exists: bool = False):
        """Set an override value.

        Args:
            key: The key to set the override for.
            value: The value to set.
            exception_if_exists: If True, an exception will be raised if the
                key already exists.
        """
        # if exception_if_exists and key in self._overrides:
        #     raise ValueError(f"Override {key} already exists")
        self._overrides[key] = value

    def current_db_setting_id(self) -> Union[str, None]:
        """Get the ID of the current database configuration.

        The function locates the connection string and schema and returns
        the ID of the configuration. If the configuration is not found,
        a new one is created and its ID is returned.

        Returns:
            The ID of the current database configuration or None if no
            connection string is set in the context.
        """
        if not self.c_string:
            logging.getLogger(__name__).error(
                "No database connection string set"
            )
            return None

        return self.stg.locate_db_config(
            c_string=self.c_string,
            schema=self.schema,
            create=True,
        )

    # Internal helpers
    def _load_last_used_db_config(self) -> None:
        """Load last used DB connection from settings into the context.

        Looks up the id saved under `exdrf.db.crt_connection`, finds the
        matching entry in `exdrf.db.c_strings`, and if present applies its
        connection string and schema.
        """
        # Read the last used connection id
        last_id = self.stg.get_setting("exdrf.db.crt_connection")
        if not last_id:
            return

        # Search the configured connections
        try:
            for item in self.stg.get_db_configs():
                if item.get("id") == last_id:
                    c_string = item.get("c_string", "")
                    schema = item.get("schema", "public")
                    if c_string:
                        self.set_db_string(c_string=c_string, schema=schema)
                    return
        except Exception as e:
            logging.getLogger(__name__).error(
                "Error while loading saved DB config: %s", e, exc_info=True
            )


@contextmanager
def same_session(session_or_ctx: "Session | QtContext"):
    if isinstance(session_or_ctx, QtContext):
        with session_or_ctx.same_session() as session:
            yield session
    else:
        yield session_or_ctx
