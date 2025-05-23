from typing import TYPE_CHECKING, Callable, Dict, Optional, Set

from sqlalchemy import MetaData

if TYPE_CHECKING:
    from exdrf_al.connection import DbConn


def table_records_counts(
    conn: "DbConn",
    metadata: MetaData,
    excluded_tables: Optional[Set[str]] = None,
    included_tables: Optional[Set[str]] = None,
) -> Dict[str, int]:
    """
    Goes through each table and retrieves the number of records.
    """
    result = {}
    if excluded_tables is None:
        excluded_tables = set()
    with conn.same_session() as session:
        for table_name, table in metadata.tables.items():
            if included_tables and table_name not in included_tables:
                continue

            if table_name in excluded_tables:
                continue

            result[table_name] = session.query(table).count()

    return result


def print_table_records_counts(
    conn: "DbConn",
    metadata: MetaData,
    excluded_tables: Optional[Set[str]] = None,
    included_tables: Optional[Set[str]] = None,
    header: Optional[str] = None,
    push_info: Callable[[str], None] = print,
    show_zero: bool = False,
):
    """Print number of records in each table.

    Goes through each table, prints and returns the number of records for each
    table.

    Args:
        conn: The database connection.
        excluded_tables: The tables to exclude.
        included_tables: The tables to include.
        header: The header to print.
        push_info: The function to push information.
    """
    td = table_records_counts(
        conn,
        metadata=metadata,
        excluded_tables=excluded_tables,
        included_tables=included_tables,
    )

    push_info(header if header else "Non-empty database tables:")
    for t_name in sorted(td.keys()):
        count = td[t_name]
        if count or show_zero:
            push_info(f" * {t_name}: {td[t_name]}")

    return td
