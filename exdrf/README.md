# Datasets-Resources-Fields

**exdrf** is the core library of **Ex-DRF**
(Extended Datasets–Resources–Fields). It lets you describe **datasets**: each
**resource** is made of typed **fields** and relationships. That single tree
drives reflection from ORMs or Pydantic, code generation (via sibling
**`exdrf-gen-*`** packages), labels, and shared UI metadata.

## What it provides

- A typed model of fields (including references and enums) and how they group
  into resources and categories.
- Helpers such as **label DSL** (`exdrf.label_dsl`) for human-readable record
  labels and generated code.
- **`FieldInfo`**, **`ResExtraInfo`**, and related types that companion packages
  populate from SQLAlchemy `info` dicts or Pydantic constraints.

## Dependencies

Declared in `pyproject.toml`: **attrs**, **inflect**, **SQLAlchemy**,
**Unidecode**. Python **3.12.2+** is required.

## Related packages

Pair **`exdrf`** with **exdrf-al** (SQLAlchemy), **exdrf-pd** (Pydantic),
**exdrf-qt** (desktop UI primitives), **exdrf-gen** and **exdrf-gen-*** plugins
for codegen, and optional **exdrf-xl**, **exdrf-ts**, **exdrf-rcv**,
**exdrf-util** as needed. Monorepo layout and quality commands are documented in
the repository root **README.md**.
