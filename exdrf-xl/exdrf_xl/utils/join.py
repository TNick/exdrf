from exdrf_xl.schema import XlSchema


def xl_join_values(
    *,
    schema: XlSchema,
    this_table: str,
    this_row_key_column: str,
    other_table: str,
    other_filter_column: str,
    other_value_expression: str,
    delimiter: str = "CHAR(10)",
    ignore_empty: bool = True,
) -> str:
    """Build an Excel formula that joins related values from another table.

    This mirrors the pattern used in resi_xl for "join related rows" columns:

    `IFERROR(SINGLE(TEXTJOIN(delimiter, ignore_empty, FILTER(values, cond))),
    "")`

    Args:
        schema: Schema that contains the structured tables.
        this_table: Structured table name where the formula is placed.
        this_row_key_column: Column in `this_table` used as key (This Row
            reference).
        other_table: Structured table name that provides the values.
        other_filter_column: Column in `other_table` used to filter rows (must
            match the current row key).
        other_value_expression: Excel expression that yields the value to join
            for each filtered row (should reference `other_table[...]`).
        delimiter: Excel expression used as join separator (default:
            `"CHAR(10)"`).
        ignore_empty: Whether TEXTJOIN should ignore empty values.

    Returns:
        Excel formula string.

    Raises:
        ValueError: If `other_table` does not exist in schema.
    """
    other_tbl = schema.get_table(other_table)
    if other_tbl is None:
        raise ValueError("Table '%s' not found in schema" % other_table)

    # Build structured references.
    this_key_ref = "%s[[#This Row],[%s]]" % (this_table, this_row_key_column)
    other_filter_ref = "%s[%s]" % (other_table, other_filter_column)

    # Keep the formula structure identical to existing templates.
    ignore_empty_token = "TRUE" if ignore_empty else "FALSE"
    return "\n".join(
        [
            "=IFERROR(",
            "  _xlfn.SINGLE(",
            "    _xlfn.TEXTJOIN(",
            "      %s, %s," % (delimiter, ignore_empty_token),
            "      _xlfn.FILTER(",
            "        %s," % other_value_expression,
            "        %s = %s" % (other_filter_ref, this_key_ref),
            "      )",
            "    )",
            "  ),",
            '  ""',
            ")",
        ]
    )
