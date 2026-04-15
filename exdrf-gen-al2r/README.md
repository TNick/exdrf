# exdrf-gen-al2r

**exdrf-gen-al2r** is an **`exdrf-gen`** plugin that emits **FastAPI**
`APIRouter` stubs from SQLAlchemy-backed **`ExDataset`** metadata. List and
read handlers are typed with **`XxxEx`**; create uses **`XxxCreate`**. Patch
is emitted only when **`exdrf-gen-al2pd`** would emit **`XxxEdit`** (composite
PK–only link tables skip PATCH).

Python **3.12.2+** is required.

## Command-line usage

```bash
exdrf-gen al2r DATASET OUT-PATH DB-MODULE SCHEMAS-PKG
```

Or: `python -m exdrf_gen al2r ...`.

- **DATASET** — `module.path:DeclarativeBase`.
- **OUT-PATH** — directory for `*_routes.py` and `__init__.py` (or
  **`EXDRF_AL2R_PATH`**).
- **DB-MODULE** — dotted import path for ORM classes (`from DB-MODULE import
  Model`).
- **SCHEMAS-PKG** — dotted root package where **`al2pd`** wrote schemas (or
  **`EXDRF_AL2R_SCHEMAS`**). Import path per resource is
  `SCHEMAS-PKG.<categories...>.<snake_case_name_plural>` (e.g.
  `myapp.schemas.widgets` for `Widget` at the root category).

Path parameters for GET/PATCH follow **`resource.primary_fields()`** order
(e.g. `{left_id}/{right_id}` for composite keys).

## Dependencies

**`exdrf-gen`**, **`exdrf-al`**, **`click`**, **`exdrf-gen-al2pd`** (for
`resource_generates_edit_payload`). Generated routers import **FastAPI** and
**SQLAlchemy** — add those to the application environment.

## Plugin registration

```toml
[project.entry-points.'exdrf.plugins']
exdrf_gen = 'exdrf_gen_al2r'
```

## See also

- **`exdrf-gen-al2pd`** — generates the Pydantic modules **`al2r`** imports.
- **`exdrf-gen`** — [`README.md`](../exdrf-gen/README.md).
