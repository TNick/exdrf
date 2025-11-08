from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from exdrf_qt.comparator.logic.manager import ComparatorManager
    from exdrf_qt.comparator.logic.nodes import ParentNode


class ComparatorAdapter:
    """Defines the interface that needs to be implemented so that data can be
    extracted from a source.
    """

    def get_compare_data(self, mng: "ComparatorManager") -> "ParentNode":
        """Get the data that will be used for comparison.

        Args:
            mng: The manager that this adapter belongs to.

        Returns:
            A single parent node that will not be used in the comparison but
            will be used only as a container for the data.
        """
        raise NotImplementedError("get_compare_data")
