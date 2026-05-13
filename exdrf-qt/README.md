# Qt5 components for Ex-DRF

**exdrf-qt** supplies **PyQt5** building blocks—models, editors, lists,
selectors, plugins, and HTML-backed viewers—that align with **exdrf** field
types and **exdrf-al**-derived datasets. Generated desktop UIs from
**exdrf-gen-al2qt** import this package for base classes and integration glue.

## Scope

The library is opinionated toward **desktop** workflows: it brings in **PyQt5**,
**PyQtWebEngine**, SVG and HTML helpers, and SQLAlchemy-related utilities for
data-bound widgets. It is heavier than **exdrf** alone; use it when you ship a
Qt client or run codegen that targets Qt.

## Dependencies

See `pyproject.toml`: **exdrf**, **exdrf-al**, **SQLAlchemy**, **PyQt5**,
**PyQtWebEngine**, and several small helpers (attrs, parse, filelock, etc.).
Python **3.12.2+** is required.

## Related packages

- **exdrf-gen-al2qt** — generates menus, routers, per-resource widgets, and
  field classes on top of **exdrf-qt**.
- **exdrf-dev** (in the same monorepo) — sample app and widgets that exercise
  the stack end to end.
