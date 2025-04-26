"""
Available fixtures:

- **`cache`**: Provides access to `pytest`'s cache system to store and retrieve
  data between test runs.
- **`capfd`**: Captures output to file descriptors (`stdout`/`stderr`) during
  tests (low-level, including C extensions).
- **`capfdbinary`**: Like `capfd`, but captures binary data instead of text.
- **`caplog`**: Captures log messages for inspection during tests.
- **`capsys`**: Captures standard output and error (`sys.stdout`/`sys.stderr`)
  during tests.
- **`capsysbinary`**: Like `capsys`, but captures binary data instead of text.
- **`class_mocker`**: Like `mocker` but scoped to a test class (provided by
  `pytest-mock` plugin).
- **`cov`**: Provides access to coverage data (enabled by `pytest-cov` plugin).
- **`doctest_namespace`**: Allows injecting variables into the namespace of
  doctests.
- **`mocker`**: Provides an easy way to use `unittest.mock` functions
  (patching, mocking) in tests.
- **`module_mocker`**: Like `mocker` but scoped to a module (provided by
  `pytest-mock` plugin).
- **`monkeypatch`**: Allows safely modifying or patching attributes,
  environment variables, and dictionaries during tests.
- **`no_cover`**: Marker to disable coverage measurement for specific tests
  (from `pytest-cov`).
- **`package_mocker`**: Like `mocker` but scoped to a package (provided by
  `pytest-mock` plugin).
- **`pytestconfig`**: Provides access to `pytest` configuration and
  command-line options inside tests.
- **`record_property`**: Records key-value metadata for reporting (especially
  useful with JUnit XML output).
- **`record_testsuite_property`**: Records properties that apply to the entire
  test suite (JUnit XML).
- **`record_xml_attribute`**: Records additional XML attributes for a specific
  test result.
- **`recwarn`**: Captures and inspects warnings emitted during a test.
- **`session_mocker`**: Like `mocker` but scoped to the whole session (provided
  by `pytest-mock` plugin).
- **`tmp_path`**: Provides a temporary directory (as a `pathlib.Path`) unique
  to the test function.
- **`tmp_path_factory`**: Factory for creating multiple `tmp_path` directories,
  scoped at session level.
- **`tmpdir`**: Provides a temporary directory (as a `py.path.local`) unique to
  the test function (older, pre-Pathlib version).
- **`tmpdir_factory`**: Factory for creating multiple `tmpdir` directories,
  scoped at session level.

"""

import pytest
from sqlalchemy.orm import clear_mappers

from exdrf_al.base import Base


@pytest.fixture
def LocalBase():
    """
    Fixture to provide a local instance of the Base class for testing. This is
    useful for creating mock models without affecting the global registry.
    """
    yield Base
    clear_mappers()
