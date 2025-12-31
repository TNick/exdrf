from exdrf_xl.schema import XlSchema


def xl_sumifs(
    *,
    schema: XlSchema,
    this_table: str,
    this_row_key_column: str,
    other_table: str,
    other_sum_column: str,
    other_criteria_column: str,
) -> str:
    """Build an Excel formula that sums related values from another table.

    `IFERROR(SINGLE(SUMIFS(sum_range, criteria_range, this_row_key)), "")`

    Args:
        schema: Schema that contains the structured tables.
        this_table: Structured table name where the formula is placed.
        this_row_key_column: Column in `this_table` used as key (This Row
            reference).
        other_table: Structured table name that provides the rows to sum.
        other_sum_column: Column in `other_table` to sum.
        other_criteria_column: Column in `other_table` used to filter rows (must
            match the current row key).

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
    sum_range_ref = "%s[%s]" % (other_table, other_sum_column)
    criteria_range_ref = "%s[%s]" % (other_table, other_criteria_column)

    return "\n".join(
        [
            "=IFERROR(",
            "  _xlfn.SINGLE(",
            "    SUMIFS(",
            "     %s, " % sum_range_ref,
            "     %s, " % criteria_range_ref,
            "      %s" % this_key_ref,
            "    )",
            "  ),",
            '  ""',
            ")",
        ]
    )
