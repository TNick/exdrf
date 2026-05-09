# Ex-DRF monorepo

The Extended Datasets-Resources-Fields (Ex-DRF) monorepo is a collection of
packages and tools designed to work together to provide a comprehensive
solution for managing datasets, resources, and fields in a variety of contexts.
The monorepo includes the following packages:

- `exdrf`: The core package that provides the main functionality for working with
  datasets, resources, and fields.
- `exdrf-al`: A package that provides support for using SQLAlchemy with Ex-DRF.
- `exdrf-pd`: A package that provides support for using Pydantic with Ex-DRF.

## Unified quality checks

Use the root `Makefile` as the single interface for quality validation:

- `make lint`: Ruff lint checks (canonical lint tool).
- `make delint`: UI regeneration + autoflake + Ruff autofixes and formatting.
- `make format`: UI regeneration + autoflake + Ruff formatting.
- `make type`: mandatory mypy gate with an inferred baseline error budget.
- `make test`: multi-package pytest runner (`exdrf_dev.pytest_dirs`).
- `make coverage`: mandatory coverage gate with inferred fail-under baseline.
- `make check`: authoritative CI contract (`lint + type + coverage`).

Threshold defaults are defined in `Makefile` and can be overridden when needed
via `MYPY_MAX_ERRORS` and `COVERAGE_FAIL_UNDER`.

## Releases and PyPI

CI runs tests on every push/PR (see ``.github/workflows/tests.yml``). Tagged
releases use ``.github/workflows/publish.yml`` (TestPyPI first, then PyPI after
approval). Maintainer-only steps and Trusted Publishing setup are documented in
[`playground/publish.md`](playground/publish.md). Makefile targets:
``build-packages``, ``collect-dist``, ``publish-test``, ``publish``,
``fake-publish``, and ``release`` (set ``EXDRF_RELEASE_ARGS``, e.g.
``--bump patch``).
