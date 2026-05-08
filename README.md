# Ex-DRF monorepo

The Extended Datasets-Resources-Fields (Ex-DRF) monorepo is a collection of
packages and tools designed to work together to provide a comprehensive
solution for managing datasets, resources, and fields in a variety of contexts.
The monorepo includes the following packages:

- `exdrf`: The core package that provides the main functionality for working with
  datasets, resources, and fields.
- `exdrf-al`: A package that provides support for using SQLAlchemy with Ex-DRF.
- `exdrf-pd`: A package that provides support for using Pydantic with Ex-DRF.

## Releases and PyPI

CI runs tests on every push/PR (see ``.github/workflows/tests.yml``). Tagged
releases use ``.github/workflows/publish.yml`` (TestPyPI first, then PyPI after
approval). Maintainer-only steps and Trusted Publishing setup are documented in
[`playground/publish.md`](playground/publish.md). Makefile targets:
``build-packages``, ``collect-dist``, ``publish-test``, ``publish``,
``fake-publish``, and ``release`` (set ``EXDRF_RELEASE_ARGS``, e.g.
``--bump patch``).
