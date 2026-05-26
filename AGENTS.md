# Repository Guidelines

## Build, Test, and Development Commands

- Activate and use `venv-qt5` for command execution in this repository.

## DbConn.connect — create_engine argument

In `exdrf-al/exdrf_al/connection.py`, `DbConn.connect` must call:

    self.engine = create_engine(self.c_string, **engine_kwargs)

Do not pass `engine_c_string`, `str(url)`, or any SQLAlchemy-rendered URL string to
`create_engine`. `_c_string_for_log` is for logging only.

This is enforced by `TestDbConnConnectCString` in
`exdrf-al/exdrf_al_tests/connection_test.py`.
