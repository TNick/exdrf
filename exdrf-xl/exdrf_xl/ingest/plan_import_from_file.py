"""Standalone function to build an import plan from an Excel workbook."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Callable

from openpyxl import load_workbook  # type: ignore[import]
from sqlalchemy import and_, or_, select
from sqlalchemy.exc import DataError

from exdrf_xl.ingest.cell_diff import CellDiff
from exdrf_xl.ingest.import_plan import ImportPlan
from exdrf_xl.ingest.row_diff import RowDiff, XlRecord
from exdrf_xl.ingest.table_diff import TableDiff
from exdrf_xl.ingest.tools import (
    default_is_db_pk,
    is_datetime_type,
    iter_chunks,
    normalize_unknown_datetime,
)

if TYPE_CHECKING:
    from exdrf_xl.schema import XlSchema

logger = logging.getLogger(__name__)


def plan_import_from_file(
    schema: "XlSchema",
    db: Any,
    path: str,
    *,
    is_db_pk: Callable[[Any], bool] | None = None,
    batch_size: int = 100,
    wb: Any | None = None,
) -> ImportPlan:
    """Build an import plan from an Excel workbook.

    This inspects each configured `XlTable` present in the workbook and
    classifies each row as:
    - new row (primary key looks like a placeholder), or
    - existing row (primary key looks like a DB id and can be found), or
    - modified existing row (existing row with changed values)

    Args:
        schema: The XlSchema instance containing table definitions.
        db: Database connection used to create a session for comparisons.
        path: Input `.xlsx` file path (used if `wb` is None).
        is_db_pk: Optional predicate used to determine whether a primary key
            cell comes from the database. Defaults to `default_is_db_pk`.
        batch_size: Batch size for database queries.
        wb: Optional workbook to use. If provided, `path` is only used for
            reference. If None, the workbook is loaded from `path`.

    Returns:
        An `ImportPlan` describing all detected new/modified rows.
    """
    is_db_pk = is_db_pk or default_is_db_pk

    should_close = False
    if wb is None:
        wb = load_workbook(filename=path, read_only=False, data_only=True)
        should_close = True

    assert wb is not None  # For type checker.

    try:
        with db.same_session() as session:
            table_plans: list[TableDiff] = []

            for table in schema.tables:
                ws_name = table.sheet_name[0:31]
                if ws_name not in wb.sheetnames:
                    continue
                ws = wb[ws_name]

                ws_table = ws.tables.get(table.xl_name)
                if ws_table is None:
                    continue

                pk_cols = [c.xl_name for c in table.columns if c.primary]
                new_rows: list[RowDiff] = []
                modified_rows: list[RowDiff] = []
                existing_rows = 0

                xl_rows_all: list[XlRecord] = list(
                    table.iter_excel_table(ws, ws_table)
                )
                total_rows = len(xl_rows_all)

                # Try the batched path if the table exposes a db model.
                db_model = None
                try:
                    db_model = table.get_db_model_class()
                except Exception:
                    db_model = None

                pk_cols_eff = (
                    table.get_pk_column_names()
                    if hasattr(table, "get_pk_column_names")
                    else pk_cols
                )

                def add_new_row(xl_rec: XlRecord) -> None:
                    pk = {k: xl_rec.get(k) for k in pk_cols_eff if k in xl_rec}
                    diffs = tuple(
                        CellDiff(
                            column=c.xl_name,
                            old_value=None,
                            new_value=xl_rec.get(c.xl_name, None),
                        )
                        for c in table.columns
                        if not bool(getattr(c, "read_only", False))
                        if c.xl_name in xl_rec
                    )
                    new_rows.append(
                        RowDiff(
                            table_name=table.xl_name,
                            is_new=True,
                            pk=pk,
                            xl_row=xl_rec,
                            db_rec=None,
                            diffs=diffs,
                        )
                    )

                def add_existing_row(db_rec: Any, xl_rec: XlRecord) -> None:
                    nonlocal existing_rows
                    existing_rows += 1
                    pk = {k: xl_rec.get(k) for k in pk_cols_eff if k in xl_rec}
                    cell_diffs: list[CellDiff] = []
                    for c in table.columns:
                        if bool(getattr(c, "read_only", False)):
                            continue
                        if c.xl_name not in xl_rec:
                            continue
                        new_val = xl_rec.get(c.xl_name, None)
                        old_val = c.value_from_record(db_rec)

                        # Normalize unknown datetime sentinel so we don't
                        # report diffs due to Excel range limitations.
                        if is_datetime_type(getattr(c, "type_name", None)):
                            new_val = normalize_unknown_datetime(new_val)
                            old_val = normalize_unknown_datetime(old_val)

                        if isinstance(new_val, str):
                            new_val = new_val.strip()
                        if isinstance(old_val, str):
                            old_val = old_val.strip()

                        if old_val != new_val:
                            cell_diffs.append(
                                CellDiff(
                                    column=c.xl_name,
                                    old_value=old_val,
                                    new_value=new_val,
                                )
                            )

                    if cell_diffs:
                        modified_rows.append(
                            RowDiff(
                                table_name=table.xl_name,
                                is_new=False,
                                pk=pk,
                                xl_row=xl_rec,
                                db_rec=db_rec,
                                diffs=tuple(cell_diffs),
                            )
                        )

                # Batched lookup path (preferred).
                if db_model is not None and pk_cols_eff:
                    pk_key_to_xl: dict[tuple[Any, ...], XlRecord] = {}
                    keyed_conditions: list[
                        tuple[tuple[Any, ...], tuple[Any, ...]]
                    ] = []

                    for xl_rec in xl_rows_all:
                        pk_key = tuple(xl_rec.get(k, None) for k in pk_cols_eff)

                        conds = None
                        try:
                            conds = table.pk_conditions(xl_rec, is_db_pk)
                        except Exception:
                            logger.exception(
                                "PK conditions failed for table %s",
                                table.xl_name,
                            )
                            conds = None

                        if conds is None:
                            add_new_row(xl_rec)
                            continue

                        pk_key_to_xl[pk_key] = xl_rec
                        keyed_conditions.append((pk_key, conds))

                    found_keys: set[tuple[Any, ...]] = set()
                    for chunk in iter_chunks(keyed_conditions, batch_size):
                        try:
                            where_clause = or_(
                                *[and_(*conds) for _, conds in chunk]
                            )
                            stmt = select(db_model).where(where_clause)
                            for db_rec in session.scalars(stmt):
                                db_key = tuple(
                                    getattr(db_rec, k) for k in pk_cols_eff
                                )
                                xl_rec_opt = pk_key_to_xl.get(db_key)
                                if xl_rec_opt is None:
                                    continue
                                found_keys.add(db_key)
                                add_existing_row(db_rec, xl_rec_opt)
                        except DataError:
                            # Postgres aborts the transaction on DataError;
                            # rollback before continuing with fallback.
                            session.rollback()
                            # Fallback to per-row lookup for this chunk.
                            for pk_key, _conds in chunk:
                                xl_rec_opt = pk_key_to_xl.get(pk_key)
                                if xl_rec_opt is None:
                                    continue
                                db_rec = None
                                try:
                                    db_rec = table.find_db_rec(
                                        session, xl_rec_opt, is_db_pk
                                    )
                                except DataError:
                                    session.rollback()
                                    db_rec = None

                                if db_rec is None:
                                    add_new_row(xl_rec_opt)
                                else:
                                    found_keys.add(pk_key)
                                    add_existing_row(db_rec, xl_rec_opt)

                    # Any DB-looking PKs not found are treated as new.
                    for pk_key, _conds in keyed_conditions:
                        if pk_key in found_keys:
                            continue
                        xl_rec_opt = pk_key_to_xl.get(pk_key)
                        if xl_rec_opt is not None:
                            add_new_row(xl_rec_opt)

                else:
                    # Legacy fallback: per-row `find_db_rec`.
                    for xl_rec in xl_rows_all:
                        pk_is_db = pk_cols_eff and all(
                            is_db_pk(xl_rec.get(k)) for k in pk_cols_eff
                        )

                        db_rec = None
                        if pk_is_db:
                            try:
                                db_rec = table.find_db_rec(
                                    session, xl_rec, is_db_pk
                                )
                            except DataError:
                                session.rollback()
                                db_rec = None

                        if db_rec is None:
                            add_new_row(xl_rec)
                        else:
                            add_existing_row(db_rec, xl_rec)

                if new_rows or modified_rows:
                    table_plans.append(
                        TableDiff(
                            table=table,
                            new_rows=tuple(new_rows),
                            modified_rows=tuple(modified_rows),
                            existing_rows=existing_rows,
                            total_rows=total_rows,
                        )
                    )

            return ImportPlan(source_path=path, tables=tuple(table_plans))
    finally:
        if should_close:
            wb.close()
