"""Cache module providing sparse list implementation."""

from typing import Callable, Dict, Generic, TypeVar, KeysView

T = TypeVar("T")


class SparseList(Generic[T]):
    """A sparse list implementation that lazily creates items on access.

    This class provides a list-like interface where items are only created
    when accessed, using a factory function. This is useful for caching
    scenarios where you need a list of a certain size but don't want to
    create all items upfront.

    Attributes:
        true_size: Number of actually created items in the sparse list.
            This is a property that returns the count of items that have
            been created and stored.
    """

    def __init__(self, default_factory: Callable[[], T]) -> None:
        """Initialize a sparse list.

        Args:
            default_factory: A callable that creates a default value when
                an index is accessed for the first time.
        """
        self._data: Dict[int, T] = {}
        self._default_factory = default_factory
        self._size = 0

    @property
    def true_size(self) -> int:
        """Get the number of actually created items.

        Returns:
            The count of items that have been created and stored in the
            sparse list, which may be less than the logical size.
        """
        return len(self._data)

    def __getitem__(self, index: int) -> T:
        """Get an item at the specified index.

        If the item doesn't exist, it will be created using the
        default factory and stored.

        Args:
            index: The index to retrieve.

        Returns:
            The item at the specified index, creating it if necessary.

        Raises:
            IndexError: If the index is out of range (index >= size).
        """
        if index >= self._size:
            raise IndexError(
                f"Index {index} out of range. List has {self._size} items."
            )
        result = self._data.get(index)
        if result is None:
            result = self._default_factory()
            self._data[index] = result
        return result

    def __setitem__(self, index: int, value: T) -> None:
        """Set an item at the specified index.

        Args:
            index: The index to set.
            value: The value to store at the index.
        """
        self._data[index] = value
        if index >= self._size:
            self._size = index + 1

    def __contains__(self, index: int) -> bool:
        """Check if the index is within the valid range.

        Args:
            index: The index to check.

        Returns:
            True if the index is within the valid range [0, size),
            False otherwise.
        """
        return 0 <= index < self._size

    def __len__(self) -> int:
        """Get the logical size of the sparse list.

        Returns:
            The logical size, which is the maximum index that has been
            set plus one, or the size that has been explicitly set.
        """
        return self._size

    def keys(self) -> KeysView[int]:
        """Get the keys of all stored items.

        Returns:
            A dict_keys view of all indices that have been explicitly
            set or accessed.
        """
        return self._data.keys()

    def clear(self) -> None:
        """Clear all stored items and reset the size to zero."""
        self._data.clear()
        self._size = 0

    def set_size(self, size: int) -> None:
        """Set the logical size of the sparse list.

        If the new size is smaller than the current size, items at
        indices >= size will be removed from storage.

        Args:
            size: The new logical size. Must be non-negative.

        Raises:
            AssertionError: If size is negative.
        """
        assert size >= 0, "Size must be non-negative."
        if size < self._size:
            to_del = []
            for i in self._data.keys():
                if i >= size:
                    to_del.append(i)
            for i in to_del:
                del self._data[i]
        self._size = size
