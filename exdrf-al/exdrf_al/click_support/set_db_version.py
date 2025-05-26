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
@click.argument("target", type=click.STRING)
@click.option(
    "--schema",
    type=str,
    default="public",
    help="The schema to use for the database.",
)
@click.option(
    "--m-dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    default="migrations",
    help="The directory to store the migration files.",
    envvar="EXDRF_DB_MIGRATIONS_DIR",
)
def set_version(target: str, conn: DbConn, schema: str, m_dir: str):
    """Set the version of the database.

    The version is simply saved in the `alembic_version` table without
    performing any migrations.
    """
    engine = conn.connect()
    assert engine is not None
    DbVer(engine=engine, migrations=m_dir).set_version(
        version=target,
    )


if __name__ == "__main__":
    set_version()
