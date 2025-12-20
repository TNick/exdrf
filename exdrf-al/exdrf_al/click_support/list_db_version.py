import click

from exdrf_al.connection import DbConn
from exdrf_al.db_ver.db_ver import DbVer


@click.command()
@click.option(
    "--m-dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    default="migrations",
    help="The directory to store the migration files.",
    envvar="EXDRF_DB_MIGRATIONS_DIR",
)
def list_db_versions(conn: DbConn, schema: str, m_dir: str):
    """List the database version.

    Arguments:
        CONN: The database connection string.
    """
    result = DbVer(engine=None, migrations=m_dir).get_history()  # type: ignore
    for rev_key, message in result:
        if message:
            click.echo(f"{rev_key}: {message}")
        else:
            click.echo(rev_key)


if __name__ == "__main__":
    list_db_versions()
