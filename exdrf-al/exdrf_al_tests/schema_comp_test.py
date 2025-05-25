from sqlalchemy import Column, Integer, MetaData, String, Table, text

from exdrf_al.connection import DbConn
from exdrf_al.schema_comp import (
    COL_DIFFS_COUNT,
    IDENTICAL_COUNT,
    RAW_DATA,
    TABLE_DIFFS_COUNT,
    compare_db_schema_to_code,
    metadata_to_dict,
    print_db_schema_diff,
    read_db_schema,
)


def make_metadata():
    metadata = MetaData()
    Table(
        "table1",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("name", String),
    )
    Table(
        "table2",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("value", String),
    )
    return metadata


def test_metadata_to_dict():
    metadata = make_metadata()
    d = metadata_to_dict(metadata)
    assert set(d.keys()) == {"table1", "table2"}
    assert d["table1"] == {"id": "INTEGER", "name": "VARCHAR"}
    assert d["table2"] == {"id": "INTEGER", "value": "VARCHAR"}


def test_read_db_schema(tmp_path):
    db_conn = DbConn(c_string="sqlite:///:memory:")
    metadata = make_metadata()
    metadata.create_all(db_conn.connect())
    assert db_conn.engine is not None
    d = read_db_schema(db_conn.engine)
    assert set(d.keys()) == {"table1", "table2"}
    # Test dump to file
    out_file = tmp_path / "schema.json"
    d2 = read_db_schema(db_conn.engine, dump_to_file=str(out_file))
    assert out_file.exists()
    import json

    with open(out_file, "r", encoding="utf+8") as f:
        loaded = json.load(f)
    assert loaded == d2


def test_compare_db_schema_to_code_identical():
    db_conn = DbConn(c_string="sqlite:///:memory:")
    metadata = make_metadata()
    metadata.create_all(db_conn.connect())
    assert db_conn.engine is not None
    result = compare_db_schema_to_code(db_conn.engine, metadata)
    assert set(result.keys()) == {"table1", "table2"}
    for v in result.values():
        # Both code and db dicts should be present
        assert isinstance(v, tuple)
        assert isinstance(v[0], dict)
        assert isinstance(v[1], dict)


def test_compare_db_schema_to_code_missing_table():
    db_conn = DbConn(c_string="sqlite:///:memory:")
    metadata = make_metadata()
    # Only create table1 in DB
    t1 = metadata.tables["table1"]
    MetaData().create_all(db_conn.connect(), tables=[t1])
    assert db_conn.engine is not None
    result = compare_db_schema_to_code(db_conn.engine, metadata)
    assert result["table2"][1] is None  # table2 missing in DB
    assert "table1" in result


def test_compare_db_schema_to_code_extra_table():
    db_conn = DbConn(c_string="sqlite:///:memory:")
    metadata = make_metadata()
    # Create table1 and an extra table in DB
    t1 = metadata.tables["table1"]
    engine = db_conn.connect()
    MetaData().create_all(engine, tables=[t1])
    # Add extra table directly
    with engine.connect() as conn:
        conn.execute(text("CREATE TABLE extra (id INTEGER PRIMARY KEY)"))
    result = compare_db_schema_to_code(engine, metadata)
    assert result["extra"][0] is None  # extra only in DB
    assert "table1" in result


def test_compare_db_schema_to_code_column_diff():
    db_conn = DbConn(c_string="sqlite:///:memory:")
    metadata = MetaData()
    Table(
        "table1",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("name", String),
    )
    metadata.create_all(db_conn.connect())
    assert db_conn.engine is not None
    # Now alter DB to add a column
    with db_conn.engine.connect() as conn:
        conn.execute(text("ALTER TABLE table1 ADD COLUMN extra_col INTEGER"))
    result = compare_db_schema_to_code(db_conn.engine, metadata)
    # extra_col should be in DB but not in code
    assert result["table1"][0]["extra_col"] == (None, "INTEGER")


def test_print_db_schema_diff_identical(LocalBase2Tables):
    db_conn, MockModelA, MockModelB = LocalBase2Tables
    messages = []

    def push_info(msg):
        messages.append(msg)

    out = print_db_schema_diff(db_conn, push_info)
    assert any("identical" in m for m in messages)
    assert out[IDENTICAL_COUNT] >= 1
    assert RAW_DATA in out


def test_print_db_schema_diff_table_and_col_diff(LocalBase):
    db_conn = DbConn(c_string="sqlite:///:memory:")

    class ModelA(LocalBase):
        __tablename__ = "table1"
        id = Column(Integer, primary_key=True)
        name = Column(String)

    LocalBase.metadata.create_all(db_conn.connect())
    # Add extra table in DB
    assert db_conn.engine is not None
    with db_conn.engine.connect() as conn:
        conn.execute(text("CREATE TABLE extra (id INTEGER PRIMARY KEY)"))
    messages = []

    def push_info(msg):
        messages.append(msg)

    out = print_db_schema_diff(db_conn, push_info, base=LocalBase)
    assert any(
        "only in code or database" in m or "differences in columns" in m
        for m in messages
    )
    assert TABLE_DIFFS_COUNT in out
    assert COL_DIFFS_COUNT in out
