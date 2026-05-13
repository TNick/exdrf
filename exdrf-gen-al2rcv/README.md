# exdrf-gen-al2rcv

The **remote-controlled-view (RCV)** stack renders **exdrf** resources and
companion data into UI shapes the SPA requests from the API.

**exdrf-gen-al2rcv** is an **`exdrf-gen`** plugin that emits FastAPI-oriented
**backend** modules: a root **`api.py`**, per-resource
**`{res_snake}_rcv_paths.py`** files under the category tree, and
**`exdrf-rcv`**-compatible plans derived from SQLAlchemy models.

We generate a plan for each resource type based on the information extracted
from SQLAlchemy database models.

Emitted layout includes a root **`__init__.py`** (imports **`api`**) and root
**`api.py`** (scaffold), one **`{res_snake}_rcv_paths.py`** per resource under
its category tree, and per-category **`__init__.py`** plus empty **`api.py`**.

## Command-line usage

```bash
exdrf-gen al2rcv DATASET OUT-PATH --get-db MODULE:CALLABLE
```

Or: `python -m exdrf_gen al2rcv ...`.

- **DATASET** — `module.path:DeclarativeBase` (same **`GetDataset`** convention
  as **`al2r`**).
- **OUT-PATH** — output directory (or **`EXDRF_AL2RCV_PATH`**).
- **`--get-db`** / **`EXDRF_AL2RCV_GET_DB`** — required
  ``dotted.module:callable`` for root ``api.py`` (same shape as **`al2r`**’s
  ``--get-db`` / ``EXDRF_AL2R_GET_DB``).

## Dependencies

**`exdrf-gen`**, **`exdrf-al`**, **`exdrf-rcv`**, **`click`**. Generated root
``api.py`` imports **FastAPI** and **SQLAlchemy** (add them in the host app).

## Plugin registration

```toml
[project.entry-points.'exdrf.plugins']
exdrf_gen = 'exdrf_gen_al2rcv'
```

## See also

- **`exdrf-rcv`** — shared runtime imported by generated RCV modules.
- **`exdrf-gen-al2r`** — FastAPI routers; same folder pattern for categories.
- **`exdrf-gen`** — [`README.md`](../exdrf-gen/README.md).
