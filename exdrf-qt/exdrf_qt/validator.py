from typing import Any, Generic, Optional, TypeVar

from attrs import define, field

T = TypeVar("T")


@define
class ValidationResult(Generic[T]):
    """Validation result class.

    Attributes:
        result: A code indicating the error.
        reason: The error message if validation fails.
        value: The validated value of type T if validation succeeds.
    """

    reason: Optional[str] = field(default=None)
    error: Optional[str] = field(default=None)
    value: Optional[T] = field(default=None)

    @property
    def is_valid(self) -> bool:
        """Check if the validation result is valid."""
        return self.error is None

    @property
    def is_invalid(self) -> bool:
        """Check if the validation result is invalid."""
        return not self.is_valid


class Validator(Generic[T]):
    """A class that can validate a value."""

    def validate_value(self, in_value: Any) -> ValidationResult[T]:
        """Validate the input value.

        Args:
            in_value: The value to validate.

        Returns:
            ValidationResult: The result of the validation.
        """
        raise NotImplementedError(
            "Subclasses must implement validate_value method."
        )
