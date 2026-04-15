# exdrf-gen-al2xl

**exdrf-gen-al2xl** is an **`exdrf-gen`** plugin that generates **Python helpers
for Excel-oriented workflows** (import/export style) from SQLAlchemy-backed
**`ExDataset`** metadata. It mirrors the **category / resource** tree used by
**al2at**, and adds **`schema_from_text.py`** for parsing structured text into
rows.

Despite the name similarity to **attrs**, this package is **not** the same as
**exdrf-gen-al2at**: it focuses on **spreadsheet** tooling (`type_to_xl`,
`read_only_columns`, custom **`sorted_fields`**), not generic attrs models.

Python **3.12.2+** is required.

## What it generates

Under the output path:

- **`__init__.py`**, **`api.py`**, **`schema_from_text.py`**
- Per category: **`{category}/__init__.py`**, **`{category}/api.py`**
- Per resource: **`{category}/{resource}.py`**

Templates live under **`exdrf_gen_al2xl/al2xl_templates/`**.

## Dependencies

Declared in `pyproject.toml`:

- **`attrs`**

Runtime (with your app and models):

- **`exdrf-gen`**, **`exdrf-al`**, **`click`**

## Command-line usage

```bash
exdrf-gen al2xl DATASET OUT-PATH OUT-MODULE DB-MODULE
```

Or: `python -m exdrf_gen al2xl ...` with the same arguments.

- **DATASET** — `module.path:Symbol` for the SQLAlchemy declarative base.
- **OUT-PATH** — output directory. Env: **`EXDRF_AL2XL_PATH`**.
- **OUT-MODULE** — target Python package for generated imports.
- **DB-MODULE** — module containing SQLAlchemy models (for templates).

## Python API

```python
from exdrf_gen_al2xl.creator import generate_xl_from_alchemy
from exdrf_gen.jinja_support import jinja_env

generate_xl_from_alchemy(
    d_set=dataset,
    out_path="/path/to/out",
    out_module="my_app.xl_gen",
    db_module="my_app.db.models",
    env=jinja_env,
)
```

Template context includes **`type_to_xl`**, **`sorted_fields`**,
**`read_only_columns`**, and the usual **`out_module`** / **`db_module`** /
**`source_module`** fields.

## Plugin registration

```toml
[project.entry-points.'exdrf.plugins']
exdrf_gen = 'exdrf_gen_al2xl'
```

## See also

- **`exdrf-gen-al2at`** — attrs-focused sibling generator
- **`exdrf-gen`** — [`README.md`](../exdrf-gen/README.md)
