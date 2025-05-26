import click

from exdrf_al.click_support.get_conn import GetConn
from exdrf_al.connection import DbConn
from exdrf_al.db_ver.db_ver import DbVer


@click.command()
@click.argument(
    "conn",
    metavar="CONN",
    type=GetConn(),
)
@click.option(
    "--schema",
    type=str,
    default="public",
    help="The schema to use for the database.",
)
@click.option(
    "--target",
    type=str,
    default="heads",
    help=(
        "The target version to upgrade to. By default, it upgrades to "
        "the latest version."
    ),
)
@click.option(
    "--m-dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    default="migrations",
    help="The directory to store the migration files.",
    envvar="EXDRF_DB_MIGRATIONS_DIR",
)
def upgrade_db(conn: DbConn, schema: str, target: str, m_dir: str):
    """Upgrade the database.

    The database is upgraded to the target version. If the target version
    is not specified, it will be upgraded to the latest version.

    Arguments:
        CONN: The database connection string.
    """
    engine = conn.connect()
    assert engine is not None
    DbVer(engine=engine, migrations=m_dir).upgrade(
        target=target,
    )


if __name__ == "__main__":
    upgrade_db()
