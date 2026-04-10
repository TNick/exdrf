# exdrf-gen-al2pd

**exdrf-gen-al2pd** is an **`exdrf-gen`** plugin intended to generate
**Pydantic**-oriented code from SQLAlchemy-backed **`ExDataset`** metadata.
It registers the **`al2pd`** CLI command and an **`al2pd_templates`** package
(currently a placeholder aside from **`__init__.py`**) ready for Jinja
templates.

Python **3.12.10+** is required.

## Current status

The **`al2pd`** command currently **only prints a short message**; it does not
yet invoke a code generator or require **`OUT-PATH`** at runtime (the argument
is optional and tied to **`EXDRF_AL2PD_PATH`**). Treat this package as a **stub**
for wiring and templates until generation logic is implemented.

## Dependencies

Declared in `pyproject.toml`:

- **`pydantic`**

For the DATASET loader and CLI you will also need **`exdrf-gen`**, **`exdrf-al`**
(with **`click`**), once the command is fully implemented.

## Command-line usage (stub)

```bash
exdrf-gen al2pd DATASET [OUT-PATH]
```

Or: `python -m exdrf_gen al2pd DATASET [OUT-PATH]`.

- **DATASET** — `module.path:Symbol` for the SQLAlchemy declarative base (same
  convention as other **al2\*** plugins).
- **OUT-PATH** — optional; env var **`EXDRF_AL2PD_PATH`** may be used instead
  when generation is implemented.

## Plugin registration

```toml
[project.entry-points.'exdrf.plugins']
exdrf_gen = 'exdrf_gen_al2pd'
```

On import, **`install_plugin`** registers **`al2pd_templates`** on the shared
Jinja loader.

## See also

- **`exdrf-gen`** — [`README.md`](../exdrf-gen/README.md) (plugin pattern,
  `install_plugin`, `load_plugins`)
