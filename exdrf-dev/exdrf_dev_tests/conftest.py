"""Pytest configuration for exdrf-dev tests."""


def pytest_configure(config):
    """Register exdrf-dev plugin hooks before any tests run."""
    from exdrf_dev.qt_gen.plugins import register_all_hooks

    register_all_hooks()
