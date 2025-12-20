from exdrf_xl.schema import XlSchema


def xl_lookup_value(
    *,
    schema: XlSchema,
    this_table: str,
    this_row_key_column: str,
    other_table: str,
    other_key_column: str,
    other_value_column: str,
    has_xlookup: bool,
) -> str:
    """Build an Excel formula that looks up a related value in another table.

    The returned string is an Excel formula using structured table references:

    - If `has_xlookup` is True, we generate:
      `IFERROR(SINGLE(XLOOKUP(...)), "")`
    - Otherwise, we generate:
      `IFERROR(VLOOKUP(...), "")`

    The function also validates that `other_table` exists in `schema` and that
    `other_value_column` is present among the included columns in that table.

    Args:
        schema: Schema that contains the structured tables.
        this_table: Structured table name where the formula is placed.
        this_row_key_column: Column in `this_table` used as lookup key (This
            Row reference).
        other_table: Structured table name that provides the lookup data.
        other_key_column: Key column in `other_table` to match against.
        other_value_column: Value column in `other_table` to return.
        has_xlookup: Whether Excel supports XLOOKUP in the target environment.

    Returns:
        Excel formula string.

    Raises:
        ValueError: If `other_table` does not exist in schema or if
            `other_value_column` is not present in the other table.
    """
    other_tbl = schema.get_table(other_table)
    if other_tbl is None:
        raise ValueError("Table '%s' not found in schema" % other_table)

    this_key_ref = "%s[[#This Row],[%s]]" % (this_table, this_row_key_column)
    other_key_ref = "%s[%s]" % (other_table, other_key_column)
    other_value_ref = "%s[%s]" % (other_table, other_value_column)

    if has_xlookup:
        return "\n".join(
            [
                "=IFERROR(",
                "  _xlfn.SINGLE(",
                "    _xlfn.XLOOKUP(",
                "      %s," % this_key_ref,
                "      %s," % other_key_ref,
                "      %s" % other_value_ref,
                "    )",
                "  ),",
                '  ""',
                ")",
            ]
        )

    value_col_idx0 = other_tbl.get_column_index(other_value_column)
    if value_col_idx0 == -1:
        raise ValueError(
            "Column '%s' not found in table '%s'"
            % (other_value_column, other_table)
        )

    # Excel VLOOKUP expects a 1-based column index within the provided table
    # range; `get_column_index()` returns a 0-based index among included cols.
    value_col_idx1 = value_col_idx0 + 1

    return (
        "=IFERROR(\n"
        "    _xlfn.VLOOKUP(\n"
        "        %s,\n"
        "        %s,\n"
        "        %d,\n"
        "        FALSE\n"
        "    ),\n"
        '    ""\n'
        ")" % (this_key_ref, other_table, value_col_idx1)
    )
