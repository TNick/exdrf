# exdrf-gen-al2at

**exdrf-gen-al2at** is an **`exdrf-gen`** plugin that generates **attrs-based
Python modules** from an **`ExDataset`** built from your SQLAlchemy declarative
models. Output is driven by Jinja2 templates under `al2at_templates/` and the
composite tree in `exdrf_gen.fs_support` (`TopDir`, `CategDir`, `ResFile`, …).

Python **3.12.2+** is required.

## What it generates

Layout under the output directory:

- Root **`__init__.py`**, **`api.py`**
- Per category: **`{category}/__init__.py`**, **`{category}/api.py`**
- Per resource: **`{category}/{resource}.py`** from `c/m.py.j2`

Templates receive `out_module`, `db_module`, `type_to_attrs`, and standard
dataset/resource context from **`exdrf-gen`** (see the **`exdrf-gen`** README
for `fs_support` and preserve markers).

## Dependencies

Declared in `pyproject.toml` for this package:

- **`attrs`**

You also need (same environment as your SQLAlchemy models):

- **`exdrf-gen`** — shared CLI, Jinja environment, `fs_support`
- **`exdrf-al`** — `GetDataset` and `dataset_from_sqlalchemy` for the DATASET
  argument
- **`click`** — used by the CLI

Install the plugin package in editable or release form alongside those
dependencies.

## Command-line usage

The command is registered on the shared **`exdrf_gen`** Click group. With
**`exdrf-gen`** installed:

```bash
exdrf-gen al2at DATASET OUT-PATH OUT-MODULE DB-MODULE
```

Same entry point via **`python -m exdrf_gen`** (loads plugins, then the CLI):

```bash
python -m exdrf_gen al2at DATASET OUT-PATH OUT-MODULE DB-MODULE
```

Arguments:

- **DATASET** — `module.path:Symbol` pointing to your SQLAlchemy declarative
  **Base** (or equivalent). Resolved by **`exdrf_al.click_support.GetDataset`**.
- **OUT-PATH** — output directory (created as needed). Override with env var
  **`EXDRF_AL2AT_PATH`**.
- **OUT-MODULE** — Python package name for generated imports.
- **DB-MODULE** — module where SQLAlchemy model classes live (passed into
  templates).

Global options on the root group include **`--debug`**.

## Python API

```python
from exdrf_gen_al2at.creator import generate_attrs_from_alchemy
from exdrf_gen.jinja_support import jinja_env

generate_attrs_from_alchemy(
    d_set=dataset,
    out_path="/path/to/out",
    out_module="my_app.generated",
    db_module="my_app.db.models",
    env=jinja_env,
)
```

## Plugin registration

This package registers:

```toml
[project.entry-points.'exdrf.plugins']
exdrf_gen = 'exdrf_gen_al2at'
```

Importing **`exdrf_gen_al2at`** calls **`install_plugin`** with the template
directory so **`jinja_env`** can resolve **`al2at_templates`**.

## See also

- **`exdrf-gen`** — [`README.md`](../exdrf-gen/README.md) (plugins, Jinja,
  `fs_support`)
