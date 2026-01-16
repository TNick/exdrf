from typing import TYPE_CHECKING, Any, Generator, List, Literal, Optional, Tuple

if TYPE_CHECKING:
    from pathlib import Path

    from exdrf_al.connection import DbConn


FormatType = Literal["json", "yaml", "csv", "plain", "pickle", "dict"]


def get_format_extension(file_format: FormatType) -> str:
    """Get the file extension for a given format.

    Args:
        format: Format name (json, yaml, csv, plain, pickle, dict).

    Returns:
        File extension with leading dot (e.g., '.json').
    """
    format_lower = file_format.lower()
    if format_lower == "json":
        return ".json"
    elif format_lower == "yaml":
        return ".yaml"
    elif format_lower == "csv":
        return ".csv"
    elif format_lower == "plain":
        return ".txt"
    elif format_lower == "pickle":
        return ".pkl"
    elif format_lower == "dict":
        return ".json"
    else:
        return ".dat"


def dump_database(
    cn: "DbConn", file_format: FormatType = "pickle"
) -> Generator[Tuple[str, List[str], List[Any], Any], None, None]:
    """Export the content of the database as raw data."""
    from io import StringIO

    from sqlalchemy import inspect, text

    assert cn.engine is not None, "Engine is not connected."

    file_format_lower = file_format.lower()

    with cn.engine.connect() as conn:
        inspector = inspect(cn.engine)
        tables_list = inspector.get_table_names()
        for table in tables_list:
            query = text(f"SELECT * FROM {table}")
            result = conn.execute(query)

            columns = list(result.keys())
            rows = list(result)
            has_rows = False

            if file_format_lower == "csv":
                import csv

                sio = StringIO()
                writer = csv.writer(sio)
                writer.writerow(columns)
                for row in rows:
                    writer.writerow(row)
                    has_rows = True
                if not has_rows:
                    continue

                yield table, columns, rows, sio.getvalue()
            elif file_format_lower == "plain":
                yield table, columns, rows, None
            elif file_format_lower == "json":
                import json

                yield table, columns, rows, json.dumps(rows)
            elif file_format_lower == "yaml":
                import yaml

                yield table, columns, rows, yaml.dump(
                    rows, default_flow_style=False
                )
            elif file_format_lower == "pickle":
                import pickle

                yield table, columns, rows, pickle.dumps(rows)

            elif file_format_lower == "dict":
                list_of_rows = [dict(zip(columns, list(row))) for row in rows]

                yield table, columns, rows, list_of_rows
            else:
                raise ValueError(f"Invalid file format: {file_format}")


def write_db_to_file(
    cn: "DbConn",
    output_path: "Path | str",
    file_format: FormatType = "pickle",
    archive_format: Optional[
        Literal["zip", "tar", "tar.gz", "tar.bz2"]
    ] = "zip",
    date_in_name: bool = False,
    time_in_name: bool = False,
    encoding: str = "utf-8",
):
    """Write the content of the database to a file."""
    import csv
    import json
    import pickle
    import tarfile
    import zipfile
    from datetime import datetime
    from io import BytesIO, StringIO
    from pathlib import Path

    import yaml

    output_path = Path(output_path)
    file_format_lower = file_format.lower()

    # Get base name without any extensions for archive filename
    base_name = output_path.name
    if "." in base_name:
        base_name = base_name.split(".", 1)[0]

    # Add date/time suffix if requested
    if date_in_name or time_in_name:
        parts = []
        if date_in_name:
            parts.append(datetime.now().strftime("%Y-%m-%d"))
        if time_in_name:
            parts.append(datetime.now().strftime("%H-%M-%S"))
        suffix_str = "_" + "_".join(parts)
        base_name = base_name + suffix_str

    # Determine archive extension based on archive_format
    if archive_format == "zip":
        archive_ext = ".zip"
    elif archive_format == "tar":
        archive_ext = ".tar"
    elif archive_format == "tar.gz":
        archive_ext = ".tar.gz"
    elif archive_format == "tar.bz2":
        archive_ext = ".tar.bz2"
    else:
        archive_ext = ""

    # Ensure output_path has the correct archive extension
    original_output_path = output_path
    if archive_ext:
        # Reconstruct path with archive extension
        output_path = output_path.parent / (base_name + archive_ext)

    # Handle dict format specifically
    if file_format_lower == "dict":
        # Collect all tables into a dictionary
        db_dict = {}
        for table, _, _, list_of_rows in dump_database(cn, file_format="dict"):
            db_dict[table] = list_of_rows

        # Serialize as JSON (dict format is typically JSON-serializable)
        if file_format == "pickle":
            content_bytes = pickle.dumps(db_dict)
        elif file_format == "json":
            content_str = json.dumps(db_dict, indent=2)
            content_bytes = content_str.encode(encoding)
        elif file_format == "yaml":
            content_str = yaml.dump(db_dict, default_flow_style=False)
            content_bytes = content_str.encode(encoding)
        elif file_format == "csv":
            for t_name, t_data in db_dict.items():
                if not archive_format:
                    with open(
                        original_output_path / f"{t_name}.csv",
                        "w",
                        encoding=encoding,
                    ) as f:
                        writer = csv.writer(f)
                        columns = list(t_data[0].keys())
                        writer.writerow(columns)
                        for row in t_data:
                            writer.writerow([row[col] for col in columns])
                    return
                else:
                    # Collect a mapping of table name -> CSV bytes
                    table_csv_bytes = {}
                    for t_name, t_data in db_dict.items():
                        if not t_data:
                            # If table data is empty, skip writing
                            continue

                        # Prepare a CSV string using StringIO
                        csv_buffer = StringIO()
                        writer = csv.writer(csv_buffer)
                        columns = list(t_data[0].keys())
                        writer.writerow(columns)
                        for row in t_data:
                            writer.writerow([row[col] for col in columns])
                        csv_str = csv_buffer.getvalue()
                        csv_bytes = csv_str.encode(encoding)
                        table_csv_bytes[t_name] = csv_bytes

        # At this point table_csv_bytes acts as {table_name: csv_bytes}
        # These should be written to the archive in the surrounding code
        else:
            content_str = json.dumps(db_dict, indent=2)
            content_bytes = content_str.encode(encoding)

        # Get format extension for file inside archive
        format_ext = get_format_extension(file_format)
        archive_filename = base_name + format_ext

        # Write to archive or file
        if archive_format == "zip":
            if file_format == "csv":
                pass
            else:
                with zipfile.ZipFile(
                    output_path, "w", zipfile.ZIP_DEFLATED
                ) as zf:
                    zf.writestr(archive_filename, content_bytes)
        elif archive_format == "tar":
            with tarfile.open(output_path, "w") as tf:
                info = tarfile.TarInfo(name=archive_filename)
                info.size = len(content_bytes)
                tf.addfile(info, BytesIO(content_bytes))
        elif archive_format == "tar.gz":
            with tarfile.open(output_path, "w:gz") as tf:
                info = tarfile.TarInfo(name=archive_filename)
                info.size = len(content_bytes)
                tf.addfile(info, BytesIO(content_bytes))
        elif archive_format == "tar.bz2":
            with tarfile.open(output_path, "w:bz2") as tf:
                info = tarfile.TarInfo(name=archive_filename)
                info.size = len(content_bytes)
                tf.addfile(info, BytesIO(content_bytes))
        elif file_format == "pickle":
            with open(output_path, "wb") as f:
                f.write(content_bytes)
        else:
            # Write directly to file if no archive format
            with open(output_path, "w", encoding=encoding) as f:
                f.write(content_str)
    else:
        # Handle other formats (existing implementation would go here)
        raise NotImplementedError(
            f"Format {file_format} not yet implemented in write_db_to_file"
        )
