"""Tests for cache module."""

import unittest

from exdrf_qt.models.cache import SparseList


class TestSparseListInit(unittest.TestCase):
    """Tests for SparseList initialization."""

    def test_init_with_factory(self) -> None:
        """Test initialization with a factory function."""

        def factory():
            return 0

        sparse_list = SparseList[int](factory)
        self.assertEqual(sparse_list._size, 0)
        self.assertEqual(len(sparse_list._data), 0)
        self.assertEqual(sparse_list._default_factory, factory)


class TestSparseListTrueSize(unittest.TestCase):
    """Tests for true_size property."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.sparse_list = SparseList[int](lambda: 0)

    def test_true_size_empty(self) -> None:
        """Test true_size for empty list."""
        self.assertEqual(self.sparse_list.true_size, 0)

    def test_true_size_after_get(self) -> None:
        """Test true_size after accessing an item."""
        self.sparse_list.set_size(5)
        _ = self.sparse_list[2]
        self.assertEqual(self.sparse_list.true_size, 1)

    def test_true_size_after_set(self) -> None:
        """Test true_size after setting an item."""
        self.sparse_list[0] = 10
        self.assertEqual(self.sparse_list.true_size, 1)

    def test_true_size_multiple_items(self) -> None:
        """Test true_size with multiple items."""
        self.sparse_list.set_size(10)
        self.sparse_list[0] = 1
        self.sparse_list[5] = 2
        self.sparse_list[9] = 3
        self.assertEqual(self.sparse_list.true_size, 3)


class TestSparseListGetItem(unittest.TestCase):
    """Tests for __getitem__ method."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.sparse_list = SparseList[int](lambda: 42)

    def test_getitem_within_range_creates_item(self) -> None:
        """Test getting an item creates it if missing."""
        self.sparse_list.set_size(5)
        value = self.sparse_list[2]
        self.assertEqual(value, 42)
        self.assertEqual(self.sparse_list.true_size, 1)

    def test_getitem_returns_existing_item(self) -> None:
        """Test getting an existing item returns stored value."""
        self.sparse_list.set_size(5)
        self.sparse_list[2] = 100
        value = self.sparse_list[2]
        self.assertEqual(value, 100)

    def test_getitem_out_of_range_raises(self) -> None:
        """Test getting item out of range raises IndexError."""
        self.sparse_list.set_size(3)
        with self.assertRaises(IndexError) as context:
            _ = self.sparse_list[5]
        self.assertIn("out of range", str(context.exception))

    def test_getitem_negative_index_not_in_range(self) -> None:
        """Test getting negative index raises IndexError."""
        self.sparse_list.set_size(3)
        with self.assertRaises(IndexError):
            _ = self.sparse_list[-1]

    def test_getitem_zero_index(self) -> None:
        """Test getting item at index 0."""
        self.sparse_list.set_size(1)
        value = self.sparse_list[0]
        self.assertEqual(value, 42)

    def test_getitem_creates_only_once(self) -> None:
        """Test getting same item multiple times creates only once."""
        self.sparse_list.set_size(5)
        value1 = self.sparse_list[2]
        value2 = self.sparse_list[2]
        self.assertEqual(value1, 42)
        self.assertEqual(value2, 42)
        self.assertEqual(self.sparse_list.true_size, 1)


class TestSparseListSetItem(unittest.TestCase):
    """Tests for __setitem__ method."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.sparse_list = SparseList[int](lambda: 0)

    def test_setitem_within_size(self) -> None:
        """Test setting item within current size."""
        self.sparse_list.set_size(5)
        self.sparse_list[2] = 100
        self.assertEqual(self.sparse_list[2], 100)
        self.assertEqual(self.sparse_list._size, 5)

    def test_setitem_expands_size(self) -> None:
        """Test setting item beyond size expands the list."""
        self.sparse_list.set_size(3)
        self.sparse_list[5] = 200
        self.assertEqual(self.sparse_list[5], 200)
        self.assertEqual(self.sparse_list._size, 6)

    def test_setitem_overwrites_existing(self) -> None:
        """Test setting item overwrites existing value."""
        self.sparse_list.set_size(5)
        self.sparse_list[2] = 100
        self.sparse_list[2] = 200
        self.assertEqual(self.sparse_list[2], 200)

    def test_setitem_zero_index(self) -> None:
        """Test setting item at index 0."""
        self.sparse_list[0] = 50
        self.assertEqual(self.sparse_list[0], 50)
        self.assertEqual(self.sparse_list._size, 1)


class TestSparseListContains(unittest.TestCase):
    """Tests for __contains__ method."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.sparse_list = SparseList[int](lambda: 0)

    def test_contains_within_range(self) -> None:
        """Test contains returns True for valid indices."""
        self.sparse_list.set_size(5)
        self.assertTrue(0 in self.sparse_list)
        self.assertTrue(4 in self.sparse_list)
        self.assertTrue(2 in self.sparse_list)

    def test_contains_out_of_range(self) -> None:
        """Test contains returns False for out of range indices."""
        self.sparse_list.set_size(5)
        self.assertFalse(5 in self.sparse_list)
        self.assertFalse(10 in self.sparse_list)

    def test_contains_negative_index(self) -> None:
        """Test contains returns False for negative indices."""
        self.sparse_list.set_size(5)
        self.assertFalse(-1 in self.sparse_list)

    def test_contains_empty_list(self) -> None:
        """Test contains returns False for empty list."""
        self.assertFalse(0 in self.sparse_list)


class TestSparseListLen(unittest.TestCase):
    """Tests for __len__ method."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.sparse_list = SparseList[int](lambda: 0)

    def test_len_empty(self) -> None:
        """Test length of empty list."""
        self.assertEqual(len(self.sparse_list), 0)

    def test_len_after_set_size(self) -> None:
        """Test length after setting size."""
        self.sparse_list.set_size(10)
        self.assertEqual(len(self.sparse_list), 10)

    def test_len_after_setitem(self) -> None:
        """Test length after setting item expands size."""
        self.sparse_list[5] = 100
        self.assertEqual(len(self.sparse_list), 6)

    def test_len_unchanged_by_getitem(self) -> None:
        """Test length unchanged when accessing items."""
        self.sparse_list.set_size(5)
        _ = self.sparse_list[2]
        self.assertEqual(len(self.sparse_list), 5)


class TestSparseListKeys(unittest.TestCase):
    """Tests for keys method."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.sparse_list = SparseList[int](lambda: 0)

    def test_keys_empty(self) -> None:
        """Test keys for empty list."""
        keys = self.sparse_list.keys()
        self.assertEqual(len(keys), 0)
        self.assertEqual(list(keys), [])

    def test_keys_after_getitem(self) -> None:
        """Test keys includes indices accessed via getitem."""
        self.sparse_list.set_size(5)
        _ = self.sparse_list[2]
        keys = list(self.sparse_list.keys())
        self.assertEqual(keys, [2])

    def test_keys_after_setitem(self) -> None:
        """Test keys includes indices set via setitem."""
        self.sparse_list[0] = 10
        self.sparse_list[3] = 20
        keys = sorted(self.sparse_list.keys())
        self.assertEqual(keys, [0, 3])

    def test_keys_returns_dict_keys_view(self) -> None:
        """Test keys returns a dict_keys view."""
        self.sparse_list.set_size(3)
        self.sparse_list[1] = 100
        keys = self.sparse_list.keys()
        self.assertIsInstance(keys, type({}.keys()))


class TestSparseListClear(unittest.TestCase):
    """Tests for clear method."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.sparse_list = SparseList[int](lambda: 0)

    def test_clear_empty_list(self) -> None:
        """Test clearing empty list."""
        self.sparse_list.clear()
        self.assertEqual(len(self.sparse_list), 0)
        self.assertEqual(self.sparse_list.true_size, 0)

    def test_clear_with_items(self) -> None:
        """Test clearing list with items."""
        self.sparse_list.set_size(10)
        self.sparse_list[0] = 1
        self.sparse_list[5] = 2
        self.sparse_list.clear()
        self.assertEqual(len(self.sparse_list), 0)
        self.assertEqual(self.sparse_list.true_size, 0)
        self.assertEqual(list(self.sparse_list.keys()), [])

    def test_clear_resets_size(self) -> None:
        """Test clear resets size to zero."""
        self.sparse_list.set_size(20)
        self.sparse_list.clear()
        self.assertEqual(self.sparse_list._size, 0)


class TestSparseListSetSize(unittest.TestCase):
    """Tests for set_size method."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.sparse_list = SparseList[int](lambda: 0)

    def test_set_size_increase(self) -> None:
        """Test increasing size."""
        self.sparse_list.set_size(3)
        self.sparse_list.set_size(10)
        self.assertEqual(len(self.sparse_list), 10)

    def test_set_size_decrease(self) -> None:
        """Test decreasing size removes items."""
        self.sparse_list.set_size(10)
        self.sparse_list[5] = 100
        self.sparse_list[8] = 200
        self.sparse_list.set_size(6)
        self.assertEqual(len(self.sparse_list), 6)
        self.assertEqual(list(self.sparse_list.keys()), [5])

    def test_set_size_decrease_to_zero(self) -> None:
        """Test setting size to zero removes all items."""
        self.sparse_list.set_size(10)
        self.sparse_list[3] = 100
        self.sparse_list.set_size(0)
        self.assertEqual(len(self.sparse_list), 0)
        self.assertEqual(self.sparse_list.true_size, 0)

    def test_set_size_same(self) -> None:
        """Test setting size to same value."""
        self.sparse_list.set_size(5)
        self.sparse_list[2] = 100
        self.sparse_list.set_size(5)
        self.assertEqual(len(self.sparse_list), 5)
        self.assertEqual(self.sparse_list.true_size, 1)

    def test_set_size_zero(self) -> None:
        """Test setting size to zero initially."""
        self.sparse_list.set_size(0)
        self.assertEqual(len(self.sparse_list), 0)

    def test_set_size_negative_raises(self) -> None:
        """Test setting negative size raises AssertionError."""
        with self.assertRaises(AssertionError):
            self.sparse_list.set_size(-1)

    def test_set_size_boundary_items(self) -> None:
        """Test set_size removes items exactly at boundary."""
        self.sparse_list.set_size(10)
        self.sparse_list[4] = 100
        self.sparse_list[5] = 200
        self.sparse_list.set_size(5)
        self.assertEqual(list(self.sparse_list.keys()), [4])


class TestSparseListIntegration(unittest.TestCase):
    """Integration tests for SparseList."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.sparse_list = SparseList[str](lambda: "default")

    def test_full_workflow(self) -> None:
        """Test a complete workflow of operations."""
        self.sparse_list.set_size(10)
        self.assertEqual(len(self.sparse_list), 10)
        self.assertEqual(self.sparse_list.true_size, 0)

        value1 = self.sparse_list[0]
        self.assertEqual(value1, "default")
        self.assertEqual(self.sparse_list.true_size, 1)

        self.sparse_list[5] = "custom"
        self.assertEqual(self.sparse_list[5], "custom")
        self.assertEqual(self.sparse_list.true_size, 2)

        self.assertTrue(0 in self.sparse_list)
        self.assertTrue(5 in self.sparse_list)
        self.assertFalse(10 in self.sparse_list)

        keys = sorted(self.sparse_list.keys())
        self.assertEqual(keys, [0, 5])

        self.sparse_list.set_size(3)
        self.assertEqual(len(self.sparse_list), 3)
        self.assertEqual(self.sparse_list.true_size, 1)
        self.assertEqual(list(self.sparse_list.keys()), [0])

        self.sparse_list.clear()
        self.assertEqual(len(self.sparse_list), 0)
        self.assertEqual(self.sparse_list.true_size, 0)
