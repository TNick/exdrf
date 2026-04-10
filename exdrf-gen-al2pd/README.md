# exdrf-gen-al2pd

**exdrf-gen-al2pd** is an **`exdrf-gen`** plugin that generates **Pydantic**
`ExModel` classes from SQLAlchemy-backed **`ExDataset`** metadata (same field
partitioning idea as bk-one **`db2m`**).

Python **3.12.10+** is required.

## Generated models per resource

For each **`ExResource`** the emitter writes one module (snake-case **plural**
stem, e.g. `widgets.py`) under the resource’s **category** path containing:

- **`Xxx`** — label fields (`minimum_field_set`) plus primary keys.
- **`XxxEx(Xxx)`** — extra scalars and relations (`PagedList[Related]` /
  optional nested related **label** types), with forward refs where needed.
- **`XxxCreate`** — writable create payload: excludes derived columns,
  `depends_on` FK scalars, `read_only`, audit names `created_on` /
  `updated_on`, and the lone PK when **`is_primary_simple`**. To-many
  relations use **`{rel}_ids`** (single related PK) or **`{rel}_keys`**
  (`list[dict[str, Any]]` for composite related PKs).
- **`XxxEdit`** — same payload rules for updates but **no primary-key
  fields**. Omitted when the resource is a **composite-PK link** with **only
  PK scalars** (then only **`XxxCreate`** is emitted).

The package also writes **`api.py`** at the output root with re-exports, and
adds **`__init__.py`** files so the tree is importable as a package.

## Command-line usage

```bash
exdrf-gen al2pd DATASET OUT-PATH
```

Or: `python -m exdrf_gen al2pd DATASET OUT-PATH`.

- **DATASET** — `module.path:DeclarativeBase` for SQLAlchemy (same as other
  **al2\*** plugins).
- **OUT-PATH** — required unless **`EXDRF_AL2PD_PATH`** is set; directory for
  generated Python modules.

## Dependencies

See `pyproject.toml`: **`exdrf`**, **`exdrf-al`**, **`exdrf-gen`**, **`exdrf-pd`**,
**`click`**, **`pydantic`**.

## Plugin registration

```toml
[project.entry-points.'exdrf.plugins']
exdrf_gen = 'exdrf_gen_al2pd'
```

## See also

- **`exdrf-gen-al2r`** — FastAPI routers that import these schemas.
- **`exdrf-gen`** — [`README.md`](../exdrf-gen/README.md).
