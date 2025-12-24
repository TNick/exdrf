"""Standalone function to apply an import plan to the database."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from sqlalchemy.exc import IntegrityError

from exdrf_xl.ingest.apply_result import ApplyResult
from exdrf_xl.ingest.import_plan import ImportPlan
from exdrf_xl.ingest.pending_update import PendingUpdate
from exdrf_xl.ingest.row_diff import RowDiff, XlRecord
from exdrf_xl.ingest.tools import (
    build_import_table_ref_map,
    default_is_db_pk,
)
from exdrf_xl.utils.toposort import toposort_tables

if TYPE_CHECKING:
    from exdrf_xl.table import XlTable

    XlTableAny = XlTable[Any]
else:
    XlTableAny = Any


def apply_import_plan(
    db: Any,
    plan: ImportPlan,
    *,
    accept_new: bool,
    accept_modified: bool,
    is_db_pk: Callable[[Any], bool] | None = None,
) -> ApplyResult:
    """Apply a previously computed `ImportPlan` to the database.

    Placeholder handling:
    - New records can use string placeholders in the primary key column
      `id`. After insertion, the allocated integer id is recorded and any
      occurrences of that placeholder in other `*_id` columns can be
      replaced.
    - For unresolved placeholders in `*_id` columns, updates may be deferred
      until all inserts complete.

    This is designed to be flexible enough for future row-level selection
    UIs: callers can filter `plan.tables[*].new_rows/modified_rows` before
    passing them here.

    Args:
        db: Database connection used to create a session for import.
        plan: Import plan previously created by `plan_import_from_file()`.
        accept_new: Whether to insert new rows.
        accept_modified: Whether to apply modifications to existing rows.
        is_db_pk: Predicate used to determine DB IDs. Defaults to
            `default_is_db_pk`.

    Returns:
        An `ApplyResult` with counts.
    """
    is_db_pk = is_db_pk or default_is_db_pk

    # Build worklists.
    to_insert: list[tuple[XlTableAny, RowDiff]] = []
    to_update: list[tuple[XlTableAny, RowDiff]] = []
    for table_plan in plan.tables:
        if accept_new:
            to_insert.extend((table_plan.table, r) for r in table_plan.new_rows)
        if accept_modified:
            to_update.extend(
                (table_plan.table, r) for r in table_plan.modified_rows
            )

    # Fast exit.
    if not to_insert and not to_update:
        return ApplyResult()

    # Determine best-effort table insertion order based on FK dependencies
    # between tables that are included in this import.
    import_tables = [table_plan.table for table_plan in plan.tables]
    ref_to_xl_name = build_import_table_ref_map(import_tables)

    deps: dict[str, set[str]] = {tbl.xl_name: set() for tbl in import_tables}
    table_fk_cols: dict[str, set[str]] = {
        tbl.xl_name: set() for tbl in import_tables
    }
    for tbl in import_tables:
        for c in tbl.columns:
            fk_ref = c.fk_table
            if not fk_ref:
                continue

            # Only consider FK relations to tables that are part of this
            # import set; otherwise the column should behave like a normal
            # data column (no placeholder mapping / deferral).
            dep = ref_to_xl_name.get(str(fk_ref))
            if not dep:
                continue
            if dep == tbl.xl_name:
                continue

            deps[tbl.xl_name].add(dep)
            table_fk_cols[tbl.xl_name].add(c.xl_name)

    table_names_in_plan_order = [tbl.xl_name for tbl in import_tables]
    insertion_order = toposort_tables(table_names_in_plan_order, deps)
    order_idx = {name: i for i, name in enumerate(insertion_order)}

    # Reorder insert worklist by table insertion order; keep row order
    # within each table stable.
    to_insert.sort(key=lambda x: order_idx.get(x[0].xl_name, 10**9))

    result = ApplyResult()

    # Placeholder -> db id mapping, scoped by table name.
    # Key is (table_name, placeholder_string), value is the integer id.
    placeholder_to_id: dict[tuple[str, str], int] = {}

    # Deferred placeholder updates for unresolved foreign keys.
    pending_updates: list[PendingUpdate] = []

    def _primary_cols(table: XlTableAny) -> list[str]:
        return [c.xl_name for c in table.columns if c.primary]

    def _is_generated_id_pk(table: XlTableAny) -> bool:
        pk = _primary_cols(table)
        return pk == ["id"]

    def _fk_cols_in_import_set(table: XlTableAny) -> set[str]:
        return table_fk_cols.get(table.xl_name, set())

    def _transform_xl_rec_for_apply(
        table: XlTableAny,
        xl_rec: XlRecord,
        *,
        allow_defer_fk: bool,
    ) -> tuple[XlRecord, str | None, list[str], list[PendingUpdate]]:
        """Prepare an Excel record dict for applying to a db record.

        Returns:
            (transformed_record, id_placeholder, unresolved_pk_columns,
            pending_updates)
        """
        transformed = dict(xl_rec)
        pk_cols = _primary_cols(table)
        unresolved_pk: list[str] = []
        row_pending: list[PendingUpdate] = []
        fk_cols_in_plan = _fk_cols_in_import_set(table)

        # Handle placeholder primary key for auto-generated id.
        id_placeholder: str | None = None
        if _is_generated_id_pk(table):
            raw_id = transformed.get("id", None)
            if raw_id is not None and not is_db_pk(raw_id):
                if isinstance(raw_id, str):
                    id_placeholder = raw_id.strip()
                transformed["id"] = None

        # Resolve placeholders in likely FK columns.
        # Find column objects to access fk_table information.
        col_by_name: dict[str, Any] = {}
        for c in table.get_included_columns():
            col_by_name[c.xl_name] = c

        for key, value in list(transformed.items()):
            if value is None:
                continue

            # Normalize empty strings to None only for FK columns that point
            # to tables included in this import run. For other tables (not
            # part of the import set), treat the value as normal user data.
            if (
                key in fk_cols_in_plan
                and key.endswith("_id")
                and isinstance(value, str)
            ):
                v = value.strip()
                if v == "":
                    transformed[key] = None
                    continue
                value = v
                transformed[key] = v

            if not isinstance(value, str):
                continue

            placeholder = value.strip()
            if placeholder == "":
                continue

            # Only treat placeholders specially for FK columns that point to
            # tables included in this import run.
            if key not in fk_cols_in_plan:
                continue

            # Get the foreign key table name for this column.
            col = col_by_name.get(key)
            fk_table_name = None
            if col is not None:
                fk_table_name = getattr(col, "fk_table", None)
            if fk_table_name is None:
                # Fallback: if we can't determine the FK table, skip
                # placeholder resolution for this column.
                continue

            # Look up placeholder scoped to the target table.
            placeholder_key = (fk_table_name, placeholder)
            mapped = placeholder_to_id.get(placeholder_key)
            if mapped is not None:
                transformed[key] = mapped
                continue

            # Unresolved placeholder in PK -> row can't be inserted yet.
            if key in pk_cols and key in fk_cols_in_plan:
                unresolved_pk.append(key)
                continue

            # Unresolved placeholder in fk-like column -> defer update.
            if (
                allow_defer_fk
                and key.endswith("_id")
                and key in fk_cols_in_plan
            ):
                transformed[key] = None
                row_pending.append(
                    PendingUpdate(
                        db_rec=None,
                        column_name=key,
                        placeholder=placeholder,
                        fk_table_name=fk_table_name,
                    )
                )

        return transformed, id_placeholder, unresolved_pk, row_pending

    with db.same_session() as session:
        # Insert pass: iterate until no progress to handle association rows
        # that depend on previously inserted ids.
        insert_queue = list(to_insert)
        inserted_this_round = True
        while insert_queue and inserted_this_round:
            inserted_this_round = False
            remaining: list[tuple[XlTableAny, RowDiff]] = []

            for table, row in insert_queue:
                xl_rec_in = row.xl_row
                transformed, id_placeholder, unresolved_pk, row_pending = (
                    _transform_xl_rec_for_apply(
                        table,
                        xl_rec_in,
                        allow_defer_fk=True,
                    )
                )

                if unresolved_pk:
                    remaining.append((table, row))
                    continue

                db_rec = table.create_new_db_record(session, transformed)

                # Bind deferred updates to this newly created record.
                for pu in row_pending:
                    pu.db_rec = db_rec
                pending_updates.extend(row_pending)

                try:
                    # Use a savepoint so one failing row doesn't roll back
                    # prior successful inserts.
                    with session.begin_nested():
                        table.apply_xl_to_db(session, db_rec, transformed)
                        session.add(db_rec)
                        session.flush()
                except IntegrityError:
                    remaining.append((table, row))
                    continue

                if id_placeholder is not None:
                    new_id = db_rec.id
                    assert new_id is not None
                    # Store placeholder scoped to this table.
                    placeholder_key = (table.xl_name, id_placeholder)
                    placeholder_to_id[placeholder_key] = new_id

                result.inserted += 1
                inserted_this_round = True

            insert_queue = remaining

        if insert_queue:
            # Still unresolved: most likely due to unresolvable placeholders
            # in composite PK association tables.
            unresolved = [(t.xl_name, r.pk) for (t, r) in insert_queue]
            raise ValueError(
                "Unresolved placeholders prevent inserting %d rows: %r"
                % (len(unresolved), unresolved)
            )

        # Update pass.
        for table, row in to_update:
            assert row.db_rec is not None
            transformed, _, _, row_pending = _transform_xl_rec_for_apply(
                table, row.xl_row, allow_defer_fk=True
            )
            for pu in row_pending:
                pu.db_rec = row.db_rec
            pending_updates.extend(row_pending)
            table.apply_xl_to_db(session, row.db_rec, transformed)
            result.updated += 1

        # Resolve deferred foreign keys now that all inserts ran.
        applied_deferred = 0
        for pu in pending_updates:
            if pu.db_rec is None:
                continue
            # Look up placeholder scoped to the target table.
            placeholder_key = (pu.fk_table_name, pu.placeholder)
            mapped = placeholder_to_id.get(placeholder_key)
            if mapped is None:
                continue
            setattr(pu.db_rec, pu.column_name, mapped)
            applied_deferred += 1

        if applied_deferred:
            result.deferred = applied_deferred
            session.flush()

        session.commit()

    # Store placeholder mapping in result for potential Excel file updates.
    result.placeholder_to_id = placeholder_to_id

    return result
