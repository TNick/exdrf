"""Jinja2-based generation for ``exdrf`` datasets and related tooling.

Submodules:

- ``jinja_support``: shared Jinja2 ``Environment``, custom ``Loader``, filters
  and globals for dataset-oriented output.
- ``fs_support``: composite ``File`` / ``Dir`` trees over ``ExDataset``
  (requires ``exdrf-al`` for relationship helpers).
- ``cli_base``: Click CLI scaffold and context setup (``exdrf-gen`` console
  script and ``python -m exdrf_gen`` run ``__main__.main``).
- ``plugin_support``: entry-point discovery and Jinja extensions.
- ``py_support``: Click parameter type for ``module:symbol`` paths.

For a full description, install metadata, and usage patterns, see the package
``README.md`` at the repository root.
"""
