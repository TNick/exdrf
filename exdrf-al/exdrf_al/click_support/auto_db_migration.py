from typing import TYPE_CHECKING, Optional

import click

from exdrf_al.click_support.get_base import GetBase
from exdrf_al.click_support.get_conn import GetConn
from exdrf_al.connection import DbConn
from exdrf_al.db_ver.db_ver import DbVer

if TYPE_CHECKING:
    from exdrf_al.base import Base


@click.command()
@click.argument(
    "conn",
    metavar="CONN",
    type=GetConn(),
    envvar="EXDRF_DB_CONN_STRING",
)
@click.argument(
    "base",
    metavar="BASE",
    type=GetBase(),
    envvar="EXDRF_DB_BASE",
)
@click.option(
    "--schema",
    type=str,
    default="public",
    help="The schema to use for the database.",
    envvar="EXDRF_DB_SCHEMA",
)
@click.option(
    "--m-dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    default="migrations",
    help="The directory to store the migration files.",
    envvar="EXDRF_DB_MIGRATIONS_DIR",
)
@click.option(
    "--message",
    type=str,
    default=None,
    help="The message to be used in the migration.",
)
def auto_db_migration(
    conn: DbConn,
    base: "Base",
    schema: str,
    m_dir: str,
    message: Optional[str],
):
    """Create migration file from the database.

    Arguments:
        CONN: The database connection string.
        BASE: The base class for the models. It should be an importable
            python path to the base class: module.name:Base
    """
    engine = conn.connect()
    assert engine is not None
    result = (
        DbVer(engine=engine, migrations=m_dir)
        .autogenerate(
            metadata=base.metadata,
            message=message,
        )
        .strip()
    )
    if len(result) > 0:
        click.echo(result)


if __name__ == "__main__":
    auto_db_migration()
