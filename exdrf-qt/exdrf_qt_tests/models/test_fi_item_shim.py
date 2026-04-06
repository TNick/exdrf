"""Ensure Qt shims re-export generic SQL filter items from ``exdrf``."""


class TestFiItemShim:
    """``exdrf_qt.models.fi_item`` stays aligned with ``exdrf.sa_fi_item``."""

    def test_sq_fi_item_reexports_match(self) -> None:
        """Shim and canonical module expose the same symbols."""

        from exdrf.sa_fi_item import SqBaseFiItem as e_sq_base
        from exdrf.sa_fi_item import SqFiItem as e_sq

        from exdrf_qt.models.fi_item import SqBaseFiItem as qt_sq_base
        from exdrf_qt.models.fi_item import SqFiItem as qt_sq

        assert qt_sq_base is e_sq_base
        assert qt_sq is e_sq
