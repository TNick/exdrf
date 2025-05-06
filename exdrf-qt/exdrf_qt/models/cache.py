from typing import Dict, Generic, TypeVar

T = TypeVar("T")


class SparseList(Generic[T]):
    def __init__(self, default_factory):
        self._data: Dict[int, T] = {}
        self._default_factory = default_factory
        self._size = 0

    def __getitem__(self, index: int) -> T:
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
        self._data[index] = value
        if index >= self._size:
            self._size = index + 1

    def __contains__(self, index: int) -> bool:
        """Check if the index is in the sparse list."""
        return 0 <= index < self._size

    def __len__(self) -> int:
        return self._size

    def keys(self):
        return self._data.keys()

    def clear(self) -> None:
        """Clear the sparse list."""
        self._data.clear()
        self._size = 0

    def set_size(self, size: int) -> None:
        """Set the size of the sparse list."""
        assert size >= 0, "Size must be non-negative."
        if size < self._size:
            to_del = []
            for i in self._data.keys():
                if i >= size:
                    to_del.append(i)
            for i in to_del:
                del self._data[i]
        self._size = size
