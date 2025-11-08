import pytest

from exdrf_qt.comparator.logic.adapter import ComparatorAdapter


def test_comparator_adapter_interface_not_implemented():
    """Base adapter must raise for abstract method."""
    adapter = ComparatorAdapter()
    with pytest.raises(NotImplementedError):
        adapter.get_compare_data(None)  # type: ignore[arg-type]
