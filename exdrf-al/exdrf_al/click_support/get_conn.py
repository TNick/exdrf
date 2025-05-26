import os

import click
from dotenv import load_dotenv

from exdrf_al.connection import DbConn


class GetConn(click.ParamType):
    """A custom Click parameter type for database connection.

    The user enters a string and this class returns a connection to the
    database.
    """

    name = "conn"

    def convert(self, value, param, ctx):
        try:
            if not value or value == "-":
                value = os.environ.get("EXDRF_DB_CONN_STRING", None)
                if value is None:
                    load_dotenv()
                    value = os.environ.get("EXDRF_DB_CONN_STRING", None)

            if not value:
                raise ValueError("No connection string provided")
            assert ctx, "Context is required"
            schema = ctx.params.get(
                "schema", os.environ.get("EXDRF_DB_SCHEMA", "public")
            )
            return DbConn(
                c_string=value,
                schema=schema,
            )
        except Exception as e:
            self.fail(
                f"Could not create the connection '{value}': {e}",
                param,
                ctx,
            )
