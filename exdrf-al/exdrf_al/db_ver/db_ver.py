import importlib.util
import io
import logging
import subprocess
import sys
from contextlib import contextmanager
from typing import Generator, List, Optional, Tuple

from alembic import autogenerate, command
from alembic.config import Config
from alembic.runtime.environment import EnvironmentContext, IncludeNameFn
from alembic.script import ScriptDirectory
from attrs import define, field
from sqlalchemy import Engine, MetaData, text


def default_pretty_script(script):
    pass


try:
    # Try to prettify the generated script using black if available
    if importlib.util.find_spec("black"):

        def pretty_script(script):
            try:
                # Format the script content using black
                result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "black",
                        "-q",
                        script.path,
                    ],
                    # input=script.render().encode(),
                    capture_output=True,
                    check=True,
                )
                # Update the script with formatted content
                # script.script_content = result.stdout.decode()
                print(result.stdout.decode())
            except subprocess.CalledProcessError:
                # If black fails, keep the original content
                pass

    else:
        pretty_script = default_pretty_script
except ImportError:
    # If black is not available, keep the original content
    pretty_script = default_pretty_script


@define
class DbVer:
    """Utilities for working with database versions."""

    engine: Engine
    migrations: str
    schema: Optional[str] = None
    main_options: List[Tuple[str, str]] = field(factory=list)
    section_options: List[Tuple[str, str, str]] = field(factory=list)
    script_dir: str = field(default="exdrf_al:db_ver:alembic")

    @contextmanager
    def alembic_config(self) -> Generator[Config, None, None]:
        """Get the alembic config.

        Yields:
            The alembic config.
        """

        # Create the instance.
        alembic_cfg = Config()

        # Set the main options.
        alembic_cfg.set_main_option("script_location", self.script_dir)
        alembic_cfg.set_main_option("version_path_separator", "os")
        alembic_cfg.set_main_option("version_locations", self.migrations)
        for key, value in self.main_options:
            alembic_cfg.set_main_option(key, value)

        # Default options in sections.
        alembic_cfg.set_section_option(
            "loggers", "keys", "root,sqlalchemy,alembic"
        )
        alembic_cfg.set_section_option("handlers", "keys", "console")
        alembic_cfg.set_section_option("formatters", "keys", "generic")

        alembic_cfg.set_section_option("logger_root", "level", "WARN")
        alembic_cfg.set_section_option("logger_root", "handlers", "console")
        alembic_cfg.set_section_option("logger_root", "qualname", "")

        alembic_cfg.set_section_option("logger_sqlalchemy", "level", "WARN")
        alembic_cfg.set_section_option("logger_sqlalchemy", "handlers", "")
        alembic_cfg.set_section_option(
            "logger_sqlalchemy", "qualname", "sqlalchemy.engine"
        )

        alembic_cfg.set_section_option("logger_alembic", "level", "INFO")
        alembic_cfg.set_section_option("logger_alembic", "handlers", "")
        alembic_cfg.set_section_option("logger_alembic", "qualname", "alembic")

        alembic_cfg.set_section_option(
            "handler_console", "class", "StreamHandler"
        )
        alembic_cfg.set_section_option(
            "handler_console", "args", "(sys.stderr,)"
        )
        alembic_cfg.set_section_option("handler_console", "level", "NOTSET")
        alembic_cfg.set_section_option(
            "handler_console", "formatter", "generic"
        )

        alembic_cfg.set_section_option(
            "formatter_generic",
            "format",
            r"%%(levelname)-5.5s [%%(name)s] %%(message)s",
        )
        alembic_cfg.set_section_option(
            "formatter_generic", "datefmt", r"%%H:%%M:%%S"
        )

        # Set the section options.
        for section, key, value in self.section_options:
            alembic_cfg.set_section_option(section, key, value)

        # Set the schema in attributes so env.py can use it.
        alembic_cfg.attributes["schema"] = self.schema

        # Set the connection.
        if self.engine is not None:
            with self.engine.begin() as connection:
                # Inform alembic to use the connection.
                alembic_cfg.attributes["connection"] = connection
                yield alembic_cfg
        else:
            yield alembic_cfg

    def set_version(self, version: str = "heads"):
        """Set the version inside the database as the latest version.

        Args:
            version: The version to set.
        """
        with self.alembic_config() as alembic_cfg:
            command.stamp(alembic_cfg, version)

    def create_tables(self, metadata: MetaData):
        """Create all tables in the database.

        Args:
            metadata: The metadata to create the tables from.
        """
        # Create all tables.
        with self.engine.begin() as conn:
            metadata.create_all(conn)

            # Load the Alembic configuration and generate the
            # version table, "stamping" it with the most recent rev:
            self.set_version()

    def upgrade(self, target: str = "heads"):
        """Run migrations on the database.

        Args:
            engine: The database engine.
            migrations: The migrations module (`myapp:migrations`).
        """
        from exdrf_qt.utils.sql_formatter import disable_sql_formatter

        with disable_sql_formatter():
            with self.alembic_config() as alembic_cfg:
                command.upgrade(alembic_cfg, target)

    def initial(self, metadata, message: str = "Initial schema"):
        """Create the initial migration that creates the tables.

        Args:
            message: The message to be used in the migration.
        """
        with self.alembic_config() as alembic_cfg:
            alembic_cfg.attributes["metadata"] = metadata
            alembic_cfg.attributes["schema"] = None
            command.revision(alembic_cfg, message=message, autogenerate=True)

    def downgrade(self, target: str = "-1"):
        """Restore previous version.

        Args:
            target: The target version.
        """
        with self.alembic_config() as alembic_cfg:
            command.downgrade(alembic_cfg, target)

    def autogenerate(
        self,
        metadata: MetaData,
        message: Optional[str] = None,
        include_filter: Optional[IncludeNameFn] = None,
        use_sql: bool = False,
    ) -> str:
        """Generate migrations.

        Args:
            metadata: The metadata to create the tables from.
            message: The message to be used in the migration.
            include_filter: The filter to be used in the migration.
            use_sql: Whether to use SQL or not.
        """
        with self.alembic_config() as alembic_cfg:
            output_buffer = io.StringIO()
            alembic_cfg.stdout = output_buffer
            alembic_cfg.attributes["metadata"] = metadata
            if include_filter:
                alembic_cfg.attributes["include_name"] = include_filter

            # Following code was borrowed from command.revision.
            script_directory = ScriptDirectory.from_config(alembic_cfg)
            command_args = dict(
                message=message,
                autogenerate=autogenerate,
                sql=False,
                head="head",
                splice=False,
                branch_label=None,
                version_path=None,
                rev_id=None,
                depends_on=None,
            )

            revision_context = autogenerate.RevisionContext(
                alembic_cfg,
                script_directory,
                command_args,
                process_revision_directives=None,
            )

            def retrieve_migrations(rev, context):
                revision_context.run_autogenerate(rev, context)
                return []

            with EnvironmentContext(
                alembic_cfg,
                script_directory,
                fn=retrieve_migrations,
                as_sql=use_sql,
                template_args=revision_context.template_args,
                revision_context=revision_context,
                include_name=include_filter,
            ):
                script_directory.run_env()

            # Go through the generated scripts and format them.
            scripts = []
            for script in revision_context.generate_scripts():
                pretty_script(script)
                scripts.append(script)
            assert len(scripts) > 0

        return output_buffer.getvalue()

    def get_history(self):
        """Get the history of the migrations.

        Returns:
            A list of tuples, where each tuple contains (revision_key, message).
            The message is the migration message or an empty string if not
            available. Revisions are returned in chronological order from
            base to head.
        """
        with self.alembic_config() as alembic_cfg:
            script_directory = ScriptDirectory.from_config(alembic_cfg)
            # Get all revisions by walking the revision graph
            # walk_revisions() returns scripts in topological order
            # (base to heads)
            revisions = []
            for script in script_directory.walk_revisions():
                message = script.doc if script.doc else ""
                revisions.append((script.revision, message))

        return revisions

    def get_current_version(self) -> Optional[str]:
        """Get the current version of the database."""
        try:
            with self.engine.connect() as conn:
                with self.alembic_config() as alembic_cfg:
                    alembic_version_table = (
                        alembic_cfg.get_main_option("version_table")
                        or "alembic_version"
                    )
                # Use schema-qualified table name if schema is set.
                if self.schema:
                    # Quote schema name to handle identifiers starting
                    # with digits or special characters
                    quoted_schema = f'"{self.schema}"'
                    table_name = f"{quoted_schema}.{alembic_version_table}"
                else:
                    table_name = alembic_version_table
                result = conn.execute(
                    text(f"SELECT version_num FROM {table_name}")
                )
                row = result.fetchone()
                if row is not None and len(row) > 0:
                    return row[0]
                else:
                    return None
        except Exception as e:
            if "psycopg2.errors.UndefinedTable" not in str(e):
                logging.getLogger(__name__).error(
                    "Error getting current version of the database.",
                    exc_info=True,
                )
            return None

    def get_latest_version(self) -> Optional[str]:
        """Get the latest version of the migrations."""
        result = self.get_history()
        return result[0][0]
