"""Ensure Qt shims re-export filter operators from ``exdrf``."""


class TestFiOpShim:
    """``exdrf_qt.models.fi_op`` stays aligned with ``exdrf.sa_filter_op``."""

    def test_fi_op_registry_reexports_match(self) -> None:
        """Core registry object is shared."""

        from exdrf.sa_filter_op import filter_op_registry as e_reg

        from exdrf_qt.models.fi_op import filter_op_registry as qt_reg

        assert qt_reg is e_reg
