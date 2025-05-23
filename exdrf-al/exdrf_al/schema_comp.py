import json
import os
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional, Type

from sqlalchemy import Engine, MetaData

from exdrf_al.base import Base

if TYPE_CHECKING:
    from exdrf_al.connection import DbConn

IDENTICAL_COUNT = "IDENTICAL_COUNT"
TABLE_DIFFS_COUNT = "TABLE_DIFFS_COUNT"
COL_DIFFS_COUNT = "COL_DIFFS_COUNT"
RAW_DATA = "RAW_DATA"

aliases = {
    "DATETIME": {
        "TIMESTAMP",
    },
    "TEXT": {
        "JSON",
    },
    "CHAR": {
        "VARCHAR",
        "TEXT",
        "JSON",
        "UUID",
        "XML",
    },
    "VARCHAR": {
        "CHAR",
        "TEXT",
        "JSON",
        "UUID",
        "XML",
    },
    "FLOAT": {
        "DOUBLE PRECISION",
    },
    "BLOB": {
        "BYTEA",
    },
    "BIGINT": {
        "INTEGER",
    },
}


def metadata_to_dict(metadata: MetaData):
    dict_exists = {}
    for table_name, table in metadata.tables.items():
        out_t = {}
        for column in table.columns:
            out_t[column.name] = str(column.type)
        dict_exists[table_name] = out_t
    return dict_exists


def read_db_schema(db: Engine, dump_to_file=None):
    """
    Reads the structure of a database and creates a simple representation
    of the table it consists of and of the columns composing the tables.

    The result can be optionally dumped to a file as json.
    """
    metadata_read = MetaData()
    metadata_read.reflect(bind=db)
    dict_exists = metadata_to_dict(metadata_read)

    if not dump_to_file:
        return dict_exists

    with open(dump_to_file, "w", encoding="utf+8") as f_out:
        json.dump(dict_exists, f_out, indent=4)
    return dict_exists


def compare_db_schema_to_code(db: Engine, metadata: MetaData) -> Dict[str, Any]:
    """Creates a comparison of the database schema to the code schema.

    The result is a dictionary where the keys are table names and the values
    are tuples of two dictionaries. The first dictionary contains the
    structure of the table as it is defined in the code. The second dictionary
    contains the structure of the table as it is present in the database.

    The structure of the table is a dictionary where the keys are column names
    and the values are the types of the columns.

    Args:
        db: The database to compare to the code.
        metadata: The metadata of the code.

    Returns:
        A dictionary with the comparison of the database schema to the code
        schema.
    """
    # Retrieve the structure of the actual database.
    old_save = os.environ.get("ALCHEPY_SAVE_SCHEMA", None)
    if old_save is not None:
        del os.environ["ALCHEPY_SAVE_SCHEMA"]
    db_schema = read_db_schema(db)
    if old_save is not None:
        os.environ["ALCHEPY_SAVE_SCHEMA"] = old_save

    # Retrieve the structure of the code.
    code_schema = metadata_to_dict(metadata)

    # This is where we join the two structures.
    result: Dict[str, Any] = {}

    # Go through the code schema and compare it to the database schema.
    for table_name, table in code_schema.items():
        if table_name not in db_schema:
            # Table is missing from the database.
            result[table_name] = (table, None)
            continue

        # Table is present in both the code and the database.
        columns = {}
        for column_name, column in table.items():
            if column_name not in db_schema[table_name]:
                # Column is missing from the database.
                columns[column_name] = (column, None)
                continue

            # Column is present in both the code and the database.
            columns[column_name] = (column, db_schema[table_name][column_name])

        for column_name, column in db_schema[table_name].items():
            if column_name not in table:
                # Column is missing from the code.
                columns[column_name] = (None, column)

        result[table_name] = (columns, columns)

    # Go through the database schema and compare it to the code schema.
    for table_name, table in db_schema.items():
        if table_name not in code_schema:
            # Table is missing from the code.
            result[table_name] = (None, table)
            continue

    return result


def print_db_schema_diff(
    conn: "DbConn",
    push_info: Callable[[str], None],
    exact_match: bool = False,
    check_data_type: bool = False,
    base: Optional[Type[Base]] = None,
):
    """Prints the differences between the database schema and the code schema.

    Args:
        conn: The database connection.
        push_info: The function to push information.
        exact_match: Whether to use exact match.
        check_data_type: Whether to check data type.
        base: The base class to use that retrieves the.
    """
    if base is None:
        base = Base
    with conn.same_session():
        assert conn.engine is not None
        compare = compare_db_schema_to_code(conn.engine, Base.metadata)

    # Top level in this dictionaries is the name of the table
    # and the content.
    identical = 0
    table_diffs = 0
    col_diffs = 0
    for table_name, (code_table, db_table) in compare.items():
        # If there is no such table in code
        if code_table is None:
            push_info(
                f"Table {table_name} is in the database but not in " "the code."
            )
            table_diffs += 1
            continue

        # If there is no such table in the database
        if db_table is None:
            push_info(
                f"Table {table_name} is in the code but not in " "the database."
            )
            table_diffs += 1
            continue

        # If the table exists in both code and database
        columns = code_table

        # Collect the differences in columns
        differences = []

        for column_name, (code_column, db_columns) in columns.items():
            if code_column is None:
                differences.append(
                    f"column {column_name} is in the database but "
                    "not in the code."
                )
                continue

            if db_columns is None:
                differences.append(
                    f"column {column_name} is in the code but not in "
                    "the database."
                )
                continue

            # If the column exists in both code and database
            # Collect the differences in the column
            if check_data_type and code_column != db_columns:
                if not exact_match:
                    if db_columns in aliases.get(code_column, set()):
                        continue
                    if code_column.replace("VARCHAR", "CHAR") == db_columns:
                        continue
                differences.append(
                    f"column {column_name} is {code_column} in code "
                    f"but {db_columns} in the database."
                )

        if differences:
            str_diff = "\n - ".join(differences)
            push_info(
                f"Table {table_name} has differences in columns:\n - "
                f"{str_diff}"
            )
            col_diffs += 1
        else:
            identical += 1

    push_info(f"{identical} tables are identical in code and database.")
    if table_diffs:
        push_info(f"{table_diffs} tables exist only in code or database.")
    if col_diffs:
        push_info(
            f"{col_diffs} columns are different between code and database."
        )

    return {
        IDENTICAL_COUNT: identical,
        TABLE_DIFFS_COUNT: table_diffs,
        COL_DIFFS_COUNT: col_diffs,
        RAW_DATA: compare,
    }
