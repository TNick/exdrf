"""Smoke tests for the ``exdrf_util`` package."""


def test_exdrf_util_core_modules_importable() -> None:
    """Core modules load without optional PDF/Excel dependencies."""

    import exdrf_util.check as check_mod
    import exdrf_util.rotate_backups as rotate_mod
    import exdrf_util.task as task_mod
    import exdrf_util.typedefs as typedefs_mod

    assert check_mod.ResultState.PASSED.value == "passed"
    assert task_mod.TaskState.INPUT.value == "input"
    assert rotate_mod.rotate_backups is not None
    assert typedefs_mod.HasTranslate is not None
