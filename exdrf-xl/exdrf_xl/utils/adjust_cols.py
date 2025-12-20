from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from exdrf_xl.column import Change, XlColumn


def adjust_columns(columns: list["XlColumn"], hints: list["Change"], **kwargs):
    """Adjust the columns of the table based on the hints."""

    to_apply = list(hints)

    c = 0
    while c < len(columns):
        column = columns[c]

        while True:
            found = -1
            for h, hint in enumerate(to_apply):
                if isinstance(hint.ref_type, str):
                    if hint.ref_type == column.xl_name:
                        found = h
                        break
                elif isinstance(column, hint.ref_type):
                    found = h
                    break
            if found != -1:
                change = to_apply.pop(found)
                new_column = change.constructor(**kwargs)
                if change.kind == "before":
                    columns.insert(c, new_column)
                    c += 1
                elif change.kind == "after":
                    columns.insert(c + 1, new_column)
                    c += 1
                elif change.kind == "replace":
                    columns[c] = new_column
                else:
                    raise ValueError(f"Invalid change kind: {change.kind}")
            else:
                # Nothing found for this column, step to the next one.
                c += 1
                break
    return columns
