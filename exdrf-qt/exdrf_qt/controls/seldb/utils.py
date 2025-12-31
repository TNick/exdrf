import re

# Connection type constants
CON_TYPE_LOCAL = "Local"
CON_TYPE_REMOTE = "Remote"
CON_TYPE_CURRENT = "Current"

CONN_PATTERN = re.compile(
    r"^(?P<scheme>[\w\+]+)://"
    r"(?:(?P<username>[^:/]+)(?::(?P<password>[^@]+))?@)?"
    r"(?P<host>[^:/]+)?"
    r"(?:\:(?P<port>\d+))?"
    r"(?:/(?P<database>[^\?]+))?"
    r"(?:\?(?P<params>.*))?$"
)


def parse_sqlalchemy_conn_str(conn_str: str):
    """
    Parse a SQLAlchemy-style connection string into its components.
    Returns a dictionary with keys: scheme, username, password,
    host, port, database, and params.
    """
    match = CONN_PATTERN.match(conn_str)
    if match:
        return match.groupdict()
    return {}
