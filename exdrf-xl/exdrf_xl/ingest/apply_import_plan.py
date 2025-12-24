"""Standalone function to apply an import plan to the database."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Callable

from attrs import define, field
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
    from exdrf_xl.column import XlColumn
    from exdrf_xl.table import XlTable

    XlTableAny = XlTable[Any]
else:
    XlTableAny = Any


logger = logging.getLogger(__name__)


class PlaceholderToIdDict(dict[tuple[str, str], int]):
    """Dictionary that normalizes placeholder keys to lowercase.

    Keys are tuples of (table_name, placeholder). Both parts are normalized
    to lowercase to ensure consistent lookups regardless of case.
    """

    def _normalize_key(self, key: tuple[str, str]) -> tuple[str, str]:
        """Normalize a key tuple to lowercase.

        Args:
            key: Tuple of (table_name, placeholder).

        Returns:
            Normalized tuple with both parts in lowercase.
        """
        return (key[0].lower(), key[1].lower())

    def __setitem__(self, key: tuple[str, str], value: int) -> None:
        """Set item with normalized key."""
        super().__setitem__(self._normalize_key(key), value)

    def __getitem__(self, key: tuple[str, str]) -> int:
        """Get item with normalized key."""
        return super().__getitem__(self._normalize_key(key))

    def __contains__(self, key: object) -> bool:
        """Check if normalized key exists."""
        if not isinstance(key, tuple) or len(key) != 2:
            return False
        if not isinstance(key[0], str) or not isinstance(key[1], str):
            return False
        return super().__contains__(self._normalize_key(key))

    def get(  # type: ignore[override]
        self, key: tuple[str, str], default: int | None = None
    ) -> int | None:
        """Get item with normalized key, returning default if not found."""
        return super().get(self._normalize_key(key), default)


@define
class ImportPlanApplier:
    """Applies an import plan to the database.

    Handles placeholder resolution, foreign key dependencies, and deferred
    updates for unresolved placeholders.

    Attributes:
        db: Database connection used to create a session for import.
        plan: Import plan previously created by `plan_import_from_file()`.
        accept_new: Whether to insert new rows.
        accept_modified: Whether to apply modifications to existing rows.
        is_db_pk: Predicate used to determine DB IDs.
        result: Result object to accumulate counts.
        placeholder_to_id: Map from (table_name, placeholder) to integer ID.
        pending_updates: List of deferred placeholder updates.
        table_fk_cols: Map from table name to set of FK column names.
    """

    db: Any
    plan: ImportPlan
    accept_new: bool
    accept_modified: bool
    is_db_pk: Callable[[Any], bool] = field(
        default=default_is_db_pk,
        converter=lambda x: default_is_db_pk if x is None else x,
    )
    result: ApplyResult = field(factory=ApplyResult, init=False)
    placeholder_to_id: PlaceholderToIdDict = field(
        factory=PlaceholderToIdDict, init=False
    )
    pending_updates: list[PendingUpdate] = field(factory=list, init=False)
    table_fk_cols: dict[str, set[str]] = field(factory=dict, init=False)
    _deps: dict[str, set[str]] = field(factory=dict, init=False, repr=False)
    _import_tables: list[Any] = field(factory=list, init=False, repr=False)

    def __call__(self) -> ApplyResult:
        """Apply the import plan and return results.

        Returns:
            An `ApplyResult` with counts and placeholder mappings.
        """
        to_insert, to_update = self._build_worklists()
        if not to_insert and not to_update:
            return self.result

        self._analyze_dependencies()
        to_insert = self._sort_by_dependencies(to_insert)

        with self.db.same_session() as session:
            self._insert_rows(session, to_insert)
            self._update_rows(session, to_update)
            self._resolve_deferred_updates(session)
            session.commit()

        self.result.placeholder_to_id = self.placeholder_to_id
        return self.result

    def _build_worklists(
        self,
    ) -> tuple[
        list[tuple[XlTableAny, RowDiff]], list[tuple[XlTableAny, RowDiff]]
    ]:
        """Build worklists of rows to insert and update.

        Returns:
            Tuple of (to_insert, to_update) lists.
        """
        to_insert: list[tuple[XlTableAny, RowDiff]] = []
        to_update: list[tuple[XlTableAny, RowDiff]] = []

        for table_plan in self.plan.tables:
            if self.accept_new:
                to_insert.extend(
                    (table_plan.table, r) for r in table_plan.new_rows
                )
            if self.accept_modified:
                to_update.extend(
                    (table_plan.table, r) for r in table_plan.modified_rows
                )

        return to_insert, to_update

    def _analyze_dependencies(self) -> None:
        """Analyze foreign key dependencies between tables in the plan."""
        import_tables = [table_plan.table for table_plan in self.plan.tables]
        ref_to_xl_name = build_import_table_ref_map(import_tables)

        deps: dict[str, set[str]] = {
            tbl.xl_name: set() for tbl in import_tables
        }
        self.table_fk_cols = {tbl.xl_name: set() for tbl in import_tables}

        for tbl in import_tables:
            for c in tbl.columns:
                fk_ref = c.fk_table
                if not fk_ref:
                    continue

                # Only consider FK relations to tables that are part of this
                # import set; otherwise the column should behave like a normal
                # data column (no placeholder mapping / deferral).
                dep = ref_to_xl_name.get(str(fk_ref))
                if not dep or dep == tbl.xl_name:
                    continue

                deps[tbl.xl_name].add(dep)
                self.table_fk_cols[tbl.xl_name].add(c.xl_name)

        # Store for later use in sorting.
        self._deps = deps
        self._import_tables = import_tables

    def _sort_by_dependencies(
        self, to_insert: list[tuple[XlTableAny, RowDiff]]
    ) -> list[tuple[XlTableAny, RowDiff]]:
        """Sort insert worklist by table dependency order.

        Args:
            to_insert: List of (table, row) tuples to insert.

        Returns:
            Sorted list maintaining row order within each table.
        """
        table_names_in_plan_order = [tbl.xl_name for tbl in self._import_tables]
        insertion_order = toposort_tables(table_names_in_plan_order, self._deps)
        order_idx = {name: i for i, name in enumerate(insertion_order)}

        # Reorder by table insertion order; keep row order within each table
        # stable.
        to_insert.sort(key=lambda x: order_idx.get(x[0].xl_name, 10**9))
        return to_insert

    def _insert_rows(
        self, session: Any, to_insert: list[tuple[XlTableAny, RowDiff]]
    ) -> None:
        """Insert new rows, handling placeholder resolution iteratively.

        Args:
            session: Database session.
            to_insert: List of (table, row) tuples to insert.
        """
        transformer = RecordTransformer(
            self.table_fk_cols, self.placeholder_to_id, self.is_db_pk
        )

        insert_queue = list(to_insert)
        inserted_this_round = True

        while insert_queue and inserted_this_round:
            inserted_this_round = False
            remaining: list[tuple[XlTableAny, RowDiff]] = []

            for table, row in insert_queue:
                if not self._try_insert_row(session, table, row, transformer):
                    remaining.append((table, row))
                else:
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

    def _try_insert_row(
        self,
        session: Any,
        table: XlTableAny,
        row: RowDiff,
        transformer: "RecordTransformer",
    ) -> bool:
        """Try to insert a single row.

        Args:
            session: Database session.
            table: Table to insert into.
            row: Row to insert.
            transformer: Record transformer for placeholder resolution.

        Returns:
            True if inserted successfully, False if unresolved dependencies.
        """
        transformed, id_placeholder, unresolved_pk, row_pending = (
            transformer.transform_for_apply(
                table, row.xl_row, allow_defer_fk=True
            )
        )

        if unresolved_pk:
            return False

        db_rec = table.create_new_db_record(session, transformed)

        # Bind deferred updates to this newly created record.
        for pu in row_pending:
            pu.db_rec = db_rec
        self.pending_updates.extend(row_pending)

        try:
            # Use a savepoint so one failing row doesn't roll back prior
            # successful inserts.
            with session.begin_nested():
                table.apply_xl_to_db(session, db_rec, transformed)
                session.add(db_rec)
                session.flush()
        except IntegrityError:
            logger.error("Failed to insert record", exc_info=True)
            return False

        if id_placeholder is not None:
            new_id = db_rec.id
            assert new_id is not None
            # Store placeholder scoped to this table.
            placeholder_key = (table.xl_name, id_placeholder)
            self.placeholder_to_id[placeholder_key] = new_id

        self.result.inserted += 1
        return True

    def _update_rows(
        self, session: Any, to_update: list[tuple[XlTableAny, RowDiff]]
    ) -> None:
        """Update existing rows.

        Args:
            session: Database session.
            to_update: List of (table, row) tuples to update.
        """
        transformer = RecordTransformer(
            self.table_fk_cols, self.placeholder_to_id, self.is_db_pk
        )

        for table, row in to_update:
            assert row.db_rec is not None
            transformed, _, _, row_pending = transformer.transform_for_apply(
                table, row.xl_row, allow_defer_fk=True
            )

            for pu in row_pending:
                pu.db_rec = row.db_rec
            self.pending_updates.extend(row_pending)

            table.apply_xl_to_db(session, row.db_rec, transformed)
            self.result.updated += 1

    def _resolve_deferred_updates(self, session: Any) -> None:
        """Resolve deferred foreign key updates now that all inserts ran.

        Args:
            session: Database session.
        """
        applied_deferred = 0
        for pu in self.pending_updates:
            if pu.db_rec is None:
                continue

            # Look up placeholder scoped to the target table.
            placeholder_key = (pu.fk_table_name, pu.placeholder)
            mapped = self.placeholder_to_id.get(placeholder_key)
            if mapped is None:
                continue

            setattr(pu.db_rec, pu.column_name, mapped)
            applied_deferred += 1

        if applied_deferred:
            self.result.deferred = applied_deferred
            session.flush()


@define
class RecordTransformer:
    """Transforms Excel records for database application.

    Handles placeholder resolution, foreign key mapping, and deferred updates.

    Attributes:
        table_fk_cols: Map from table name to set of FK column names.
        placeholder_to_id: Map from (table_name, placeholder) to integer ID.
        is_db_pk: Predicate to determine if a value is a DB primary key.
        _column_lookup_cache: Cache of column lookups by table name.
    """

    table_fk_cols: dict[str, set[str]]
    placeholder_to_id: PlaceholderToIdDict
    is_db_pk: Callable[[Any], bool]
    _column_lookup_cache: dict[str, dict[str, Any]] = field(
        factory=dict, init=False, repr=False
    )

    def transform_for_apply(
        self,
        table: XlTableAny,
        xl_rec: XlRecord,
        *,
        allow_defer_fk: bool,
    ) -> tuple[XlRecord, str | None, list[str], list[PendingUpdate]]:
        """Prepare an Excel record dict for applying to a db record.

        Args:
            table: Table the record belongs to.
            xl_rec: Excel record to transform.
            allow_defer_fk: Whether to allow deferring FK updates.

        Returns:
            Tuple of (transformed_record, id_placeholder, unresolved_pk_columns,
            pending_updates).
        """
        transformed = dict(xl_rec)
        pk_cols = self._get_primary_cols(table)
        unresolved_pk: list[str] = []
        row_pending: list[PendingUpdate] = []
        fk_cols_in_plan = self._get_fk_cols_in_import_set(table)

        # Handle placeholder primary key for auto-generated id.
        id_placeholder = self._handle_id_placeholder(table, transformed)

        # Resolve placeholders in foreign key columns.
        col_by_name = self._build_column_lookup(table)
        self._process_foreign_keys(
            transformed,
            pk_cols,
            fk_cols_in_plan,
            col_by_name,
            allow_defer_fk,
            unresolved_pk,
            row_pending,
        )

        return transformed, id_placeholder, unresolved_pk, row_pending

    def _get_primary_cols(self, table: XlTableAny) -> list[str]:
        """Get primary key column names for a table.

        Args:
            table: Table to get PK columns for.

        Returns:
            List of primary key column names.
        """
        return (
            list(table.pk_columns)
            if table.pk_columns
            else [c.xl_name for c in table.columns if c.primary]
        )

    def _is_generated_id_pk(self, table: XlTableAny) -> bool:
        """Check if table has a single auto-generated 'id' primary key.

        Args:
            table: Table to check.

        Returns:
            True if table has single 'id' PK.
        """
        pk = self._get_primary_cols(table)
        return pk == ["id"]

    def _get_fk_cols_in_import_set(self, table: XlTableAny) -> set[str]:
        """Get foreign key columns that point to tables in this import set.

        Args:
            table: Table to get FK columns for.

        Returns:
            Set of foreign key column names.
        """
        return self.table_fk_cols.get(table.xl_name, set())

    def _handle_id_placeholder(
        self, table: XlTableAny, transformed: XlRecord
    ) -> str | None:
        """Handle placeholder in auto-generated ID column.

        Args:
            table: Table the record belongs to.
            transformed: Record being transformed (modified in place).

        Returns:
            Placeholder string if found, None otherwise.
        """
        if not self._is_generated_id_pk(table):
            return None

        raw_id = transformed.get("id", None)
        if raw_id is None or self.is_db_pk(raw_id):
            return None

        if isinstance(raw_id, str):
            id_placeholder = raw_id.strip()
            transformed["id"] = None
            return id_placeholder
        return None

    def _build_column_lookup(self, table: XlTableAny) -> dict[str, Any]:
        """Build a lookup map from column name to column object.

        Caches the result per table to avoid rebuilding for each record.

        Args:
            table: Table to build lookup for.

        Returns:
            Map from column name to column object.
        """
        table_name = table.xl_name
        result = self._column_lookup_cache.get(table_name, None)
        if result is not None:
            return result

        col_by_name: dict[str, Any] = {}
        for c in table.get_included_columns():
            col_by_name[c.xl_name] = c
        self._column_lookup_cache[table_name] = col_by_name
        return col_by_name

    def _process_foreign_keys(
        self,
        transformed: XlRecord,
        pk_cols: list[str],
        fk_cols_in_plan: set[str],
        col_by_name: dict[str, Any],
        allow_defer_fk: bool,
        unresolved_pk: list[str],
        row_pending: list[PendingUpdate],
    ) -> None:
        """Process foreign key columns, resolving placeholders.

        Args:
            transformed: Record being transformed (modified in place).
            pk_cols: List of primary key column names.
            fk_cols_in_plan: Set of FK column names in import set.
            col_by_name: Map from column name to column object.
            allow_defer_fk: Whether to allow deferring FK updates.
            unresolved_pk: List to append unresolved PK columns to.
            row_pending: List to append pending updates to.
        """
        for key, value in list(transformed.items()):
            if value is None:
                continue

            # Only treat placeholders specially for FK columns in import set.
            if key not in fk_cols_in_plan:
                continue

            # Normalize empty strings to None for FK columns.
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

            fk_table_name = self._get_fk_table_name(key, col_by_name)
            if fk_table_name is None:
                continue

            # Try to resolve placeholder.
            placeholder_key = (fk_table_name, placeholder)
            mapped = self.placeholder_to_id.get(placeholder_key)
            if mapped is not None:
                transformed[key] = mapped
                continue

            # Unresolved placeholder in PK -> row can't be inserted yet.
            if key in pk_cols and key in fk_cols_in_plan:
                unresolved_pk.append(key)
                continue

            # Unresolved placeholder in FK column -> defer update.
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

    def _get_fk_table_name(
        self, column_name: str, col_by_name: dict[str, "XlColumn"]
    ) -> str | None:
        """Get the foreign key table name for a column.

        Args:
            column_name: Name of the column.
            col_by_name: Map from column name to column object.

        Returns:
            Foreign key table name or None if not found.
        """
        col = col_by_name.get(column_name)
        if col is None:
            return None
        return col.fk_table


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
    applier = ImportPlanApplier(
        db,
        plan,
        accept_new=accept_new,
        accept_modified=accept_modified,
        is_db_pk=is_db_pk,
    )
    return applier()
