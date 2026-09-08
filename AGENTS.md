# Repository Guidelines

## Changelog

Log changes only for **production code** edits (not tests). Before finishing a
task that changed application or library source, update the nearest
`CHANGELOG.md` (walk up from edited paths). If none exists, create one at the
repository root with `## [Unreleased]` and Added/Changed/Fixed sections. Add at
least one bullet describing what changed for users.

**Do not** update the changelog when: the task was read-only; you are in **Plan
mode** or only writing/updating plans (including `.cursor/plans/`); changes are
**tests only** (`tests/`, `*_test.py`, test fixtures); or the user asked not to
update it.

## Build, Test, and Development Commands

- Activate and use `venv-qt5` for command execution in this repository.

## DbConn.connect — create_engine argument

In `exdrf-al/exdrf_al/connection.py`, `DbConn.connect` must pass
`self.c_string` verbatim to `create_engine` for non-SQLite databases (so URL
components such as passwords are not altered). For SQLite, use the URL returned
by `_sqlite_engine_url` (rendered with `hide_password=False`) so shared
``file:`` in-memory URIs include ``uri=true``. Use ``c_string_for_log`` for
logging only, not ``create_engine``.

`TestDbConnConnectCString` enforces verbatim PostgreSQL URLs.
`TestDbConnConnect.test_shared_file_uri_from_subdirectory` enforces SQLite
``file:`` normalization.
