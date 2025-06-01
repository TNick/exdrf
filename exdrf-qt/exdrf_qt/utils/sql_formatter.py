import logging
import logging.config
from typing import TYPE_CHECKING, Any

import sqlparse  # type: ignore

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QWidget  # noqa: F401
    from sqlalchemy import Select  # noqa: F401


def is_dict_arg(record: logging.LogRecord) -> bool:
    if not record.args:
        return False
    if len(record.args) != 2:
        return False

    first_rec: str = record.args[0]  # type: ignore
    if not isinstance(first_rec, str):
        return False

    if not first_rec.startswith("generated in ") and not first_rec.startswith(
        "cached since"
    ):
        return False

    if record.args[1].__class__.__name__ != "_repr_params":  # type: ignore
        return False
    return True


def pformat(obj: Any) -> str:
    """Pretty-print a _repr_params object."""
    result = []
    for k, v in obj.params.items():
        if isinstance(v, str):
            result.append(f'  {k}: "{v}",')
        else:
            result.append(f"  {k}: {v},")
    if len(result) == 0:
        return "{}"
    return "{\n" + "\n".join(result) + "\n}"


class SQLPrettyFormatter(logging.Formatter):
    """Custom formatter that pretty-prints SQL statements from SQLAlchemy."""

    def format(self, record):
        msg = record.getMessage()

        if record.name == "sqlalchemy.engine.Engine" and isinstance(
            record.msg, str
        ):
            try:
                if is_dict_arg(record):
                    record.msg = "[%s]\n%s"
                    record.args = (
                        record.args[0],  # type: ignore
                        pformat(record.args[1]),  # type: ignore
                    )
                    return super().format(record)

                if "[cached since" in msg or "[generated in" in msg:
                    return super().format(record)

                pretty_sql = sqlparse.format(
                    record.getMessage(), reindent=True, keyword_case="upper"
                ).replace(" ON ", "\n    ON ")
                record.msg = "\n" + pretty_sql
                record.args = ()
            except Exception as e:
                # fallback to default formatting if sqlparse fails
                print(f"Error formatting SQL: {record.msg}: {e}")
        return super().format(record)
