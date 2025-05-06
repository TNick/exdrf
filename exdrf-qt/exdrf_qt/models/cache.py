from typing import Dict, Generic, TypeVar

T = TypeVar("T")


class SparseList(Generic[T]):
    def __init__(self, default_factory):
        self._data: Dict[int, T] = {}
        self._default_factory = default_factory
        self._size = 0

    def __getitem__(self, index: int) -> T:
        result = self._data.get(index)
        if result is None:
            result = self._default_factory()
            self._data[index] = result
        if index >= self._size:
            self._size = index + 1
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
