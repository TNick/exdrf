# Excel interface for Ex-DRF

**exdrf_xl** (PyPI distribution **`exdrf_xl`**) adds helpers for reading and
writing **Excel** (`.xlsx`) in line with **exdrf** resource and field metadata.
Use it for import/export pipelines, reports, or tooling that round-trips
tabular data without hand-rolling column semantics.

## Dependencies

**exdrf** and **openpyxl** (`pyproject.toml`). Python **3.12.2+** is required.

## Related packages

- **exdrf-gen-al2xl** — codegen plugin that emits Python modules for
  Excel-style workflows from SQLAlchemy-backed **`ExDataset`** metadata (helpers
  such as **`type_to_xl`**, read-only column lists, and **`schema_from_text`**).
  Install **exdrf-gen** plus **exdrf-gen-al2xl** when you want generated helpers
  rather than only the runtime library.
