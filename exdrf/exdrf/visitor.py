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

    def visit_category(self, name: str, level: int, content: dict):
        """Visit a category.

        Args:
            name: The key of the category.
            level: The depth level of the category.
            content: The content of the category. This is a dictionary
                where values can be other categories or resources. The key
                is the name of the resource or category.

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
