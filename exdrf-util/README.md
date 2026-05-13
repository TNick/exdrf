# Utilities for Ex-DRF

**exdrf-util** is a grab bag of **small, optional helpers** built on **exdrf**
types and attrs. It is useful for desktop or back-office scripts that already
depend on **exdrf** and need shared table/export or task scaffolding. It is not
a required dependency for minimal API or ORM-only stacks.

## Contents (high level)

Modules under **`exdrf_util`** include:

- **Tabular export**: turn **openpyxl** cell ranges into **PDF** or **Word**
  documents (`table2pdf`, `table2doc`, `table_writer`, `table2base`) using
  **reportlab** / **python-docx** when those libraries are available in the
  environment.
- **PDF utilities**: merge and manipulate PDFs (`merge_pdfs`), backup rotation
  (`rotate_backups`).
- **Tasks**: attrs-based **`Task`** state machine tied to **`ExFieldBase`** for
  form-like workflows (`task`).
- **Misc**: verbose checking helpers, shared typedefs for translation/context
  protocols.

Runtime **`dependencies`** in `pyproject.toml` list only **exdrf**; features
that import **openpyxl**, **reportlab**, or **docx** expect you to install those
packages next to **exdrf-util** when you use the corresponding modules.

Python **3.12.2+** is required.
