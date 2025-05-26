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
    envvar="EXDRF_DB_SCHEMA",
)
@click.option(
    "--target",
    type=str,
    default="-1",
    help=(
        "The target version to downgrade to. By default, it downgrades to "
        "the previous version."
    ),
)
@click.option(
    "--m-dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    default="migrations",
    help="The directory to store the migration files.",
    envvar="EXDRF_DB_MIGRATIONS_DIR",
)
def downgrade_db(conn: DbConn, schema: str, target: str, m_dir: str):
    """Downgrade the database."""
    engine = conn.connect()
    assert engine is not None
    DbVer(engine=engine, migrations=m_dir).downgrade(
        target=target,
    )


if __name__ == "__main__":
    downgrade_db()
