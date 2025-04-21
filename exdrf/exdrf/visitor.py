from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from exdrf.dataset import ExDataset
    from exdrf.field import ExField
    from exdrf.resource import ExResource


class ExVisitor:
    """Visitor class that can explore datasets, resources and fields."""

    def visit_dataset(self, dataset: "ExDataset"):
        """Visit a dataset.

        Args:
            dataset: The dataset to visit.

        Returns:
            bool: True if the visit should continue, False otherwise.
        """
        return True

    def visit_resource(self, resource: "ExResource"):
        """Visit a resource.

        Args:
            resource: The resource to visit.

        Returns:
            bool: True if the visit should continue, False otherwise.
        """
        return True

    def visit_field(self, field: "ExField"):
        """Visit a field.

        Args:
            field: The field to visit.

        Returns:
            bool: True if the visit should continue, False otherwise.
        """
        return True
