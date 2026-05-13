# Development helpers

This package is a **sandbox and reference implementation** for
[Ex-DRF](https://github.com/TNick/exdrf) (Extended
Datasets–Resources–Fields) in the same monorepo as `exdrf`. It is not a minimal
runtime dependency for applications that only use the core library; instead it
collects runnable examples, Qt UIs, and tooling that exercise Ex-DRF and
related packages end to end.

## What lives here

- **Sample domain models** under `exdrf_dev/db/`: SQLAlchemy entities with
  relationships (parents, children, tags, profiles, composite keys, related
  items, and association tables). They illustrate typical metadata and typing
  patterns used with Ex-DRF and `exdrf_al`.
- **Qt examples**: hand-written widgets under `exdrf_dev/qt/` plus generated
  scaffolding under `exdrf_dev/qt_gen/` and `exdrf_dev/attr_gen/`, showing how
  generated and custom pieces fit together for desktop UIs (PyQt5).
- **Command-line helpers** in `exdrf_dev/cli.py`: a Click group that loads
  `.env`, can print the environment, runs arbitrary subprocess commands (with
  optional `env:VAR` indirection), and reuses **`exdrf_al` migration
  commands** (upgrade, downgrade, list/set versions, auto migration).

## Dependencies and audience

Install **`exdrf-dev`** when you need the demo app, Qt samples, or CLI shortcuts
above. It depends on **`exdrf`** (core) and declares **PyQt5**, **click**, and
**python-dotenv**. Optional dev extras in `pyproject.toml` cover formatters,
linters, pytest, and factories for local quality work.

## Tests and monorepo runs

The helper module `exdrf_dev/pytest_dirs.py` runs pytest across several package
directories with a shared `PYTHONPATH` layout; the root `Makefile` references
`exdrf_dev.pytest_dirs` when driving **multi-package** test runs in this repo.

For day-to-day quality gates and release details for the whole monorepo, see
the root `README.md` and `Makefile`.
