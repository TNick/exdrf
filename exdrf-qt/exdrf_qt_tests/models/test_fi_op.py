"""Tests for filter operators in exdrf_qt.models.fi_op."""

import unittest
from unittest.mock import MagicMock, patch

from sqlalchemy import Integer, String
from sqlalchemy.sql.elements import ColumnClause
from sqlalchemy.sql.operators import eq, gt, in_op, lt, ne, regexp_match_op

from exdrf_qt.models.fi_op import (
    EqFiOp,
    FiOp,
    FiOpRegistry,
    GreaterFiOp,
    ILikeFiOp,
    InFiOp,
    IsNoneFiOp,
    NotEqFiOp,
    RegexFiOp,
    SmallerFiOp,
    filter_op_registry,
    is_none,
)


class TestFiOp(unittest.TestCase):
    def test_base_class_attributes(self) -> None:
        """Test that FiOp base class has required attributes."""
        op = FiOp(uniq="test", predicate=eq)
        self.assertEqual(op.uniq, "test")
        self.assertEqual(op.predicate, eq)


class TestEqFiOp(unittest.TestCase):
    def test_uniq_attribute(self) -> None:
        """Test that EqFiOp has correct uniq attribute."""
        op = EqFiOp()
        self.assertEqual(op.uniq, "eq")

    def test_predicate_attribute(self) -> None:
        """Test that EqFiOp has correct predicate attribute."""
        op = EqFiOp()
        self.assertEqual(op.predicate, eq)


class TestNotEqFiOp(unittest.TestCase):
    def test_uniq_attribute(self) -> None:
        """Test that NotEqFiOp has correct uniq attribute."""
        op = NotEqFiOp()
        self.assertEqual(op.uniq, "not_eq")

    def test_predicate_attribute(self) -> None:
        """Test that NotEqFiOp has correct predicate attribute."""
        op = NotEqFiOp()
        self.assertEqual(op.predicate, ne)


class TestILikeFiOp(unittest.TestCase):
    def test_uniq_attribute(self) -> None:
        """Test that ILikeFiOp has correct uniq attribute."""
        op = ILikeFiOp()
        self.assertEqual(op.uniq, "ilike")

    def test_predicate_is_callable(self) -> None:
        """Test that ILikeFiOp predicate is callable."""
        op = ILikeFiOp()
        self.assertTrue(callable(op.predicate))

    def test_predicate_with_string_column(self) -> None:
        """Test _predicate method with a String column."""
        mock_column = MagicMock(spec=ColumnClause)
        mock_column.type = String()
        mock_column.type.__class__.__name__ = "String"
        mock_value = "test%"
        mock_result = MagicMock()

        with patch("exdrf_qt.models.fi_op.ilike_op") as mock_ilike:
            mock_ilike.return_value = mock_result
            result = ILikeFiOp._predicate(mock_column, mock_value)

            mock_ilike.assert_called_once_with(mock_column, mock_value)
            self.assertEqual(result, mock_result)

    def test_predicate_with_non_string_column(self) -> None:
        """Test _predicate method with a non-String column."""
        mock_column = MagicMock(spec=ColumnClause)
        mock_column.type = Integer()
        mock_column.type.__class__.__name__ = "Integer"
        mock_value = "test%"
        mock_cast_column = MagicMock()
        mock_result = MagicMock()

        with (
            patch("exdrf_qt.models.fi_op.al_cast") as mock_cast,
            patch("exdrf_qt.models.fi_op.ilike_op") as mock_ilike,
        ):
            mock_cast.return_value = mock_cast_column
            mock_ilike.return_value = mock_result
            result = ILikeFiOp._predicate(mock_column, mock_value)

            mock_cast.assert_called_once_with(mock_column, String)
            mock_ilike.assert_called_once_with(mock_cast_column, mock_value)
            self.assertEqual(result, mock_result)

    def test_predicate_with_invalid_column(self) -> None:
        """Test _predicate method with invalid column."""
        mock_column = MagicMock()
        del mock_column.type
        mock_value = "test%"

        with patch("exdrf_qt.models.fi_op.logger") as mock_logger:
            result = ILikeFiOp._predicate(mock_column, mock_value)

            self.assertFalse(result)
            mock_logger.warning.assert_called_once()


class TestRegexFiOp(unittest.TestCase):
    def test_uniq_attribute(self) -> None:
        """Test that RegexFiOp has correct uniq attribute."""
        op = RegexFiOp()
        self.assertEqual(op.uniq, "regex")

    def test_predicate_attribute(self) -> None:
        """Test that RegexFiOp has correct predicate attribute."""
        op = RegexFiOp()
        self.assertEqual(op.predicate, regexp_match_op)


class TestIsNoneFunction(unittest.TestCase):
    def test_is_none_function(self) -> None:
        """Test the is_none function."""
        mock_column = MagicMock()
        mock_column.is_.return_value = "is_none_result"

        result = is_none(mock_column, None)

        mock_column.is_.assert_called_once_with(None)
        self.assertEqual(result, "is_none_result")


class TestIsNoneFiOp(unittest.TestCase):
    def test_uniq_attribute(self) -> None:
        """Test that IsNoneFiOp has correct uniq attribute."""
        op = IsNoneFiOp()
        self.assertEqual(op.uniq, "none")

    def test_predicate_attribute(self) -> None:
        """Test that IsNoneFiOp has correct predicate attribute."""
        op = IsNoneFiOp()
        self.assertEqual(op.predicate, is_none)


class TestGreaterFiOp(unittest.TestCase):
    def test_uniq_attribute(self) -> None:
        """Test that GreaterFiOp has correct uniq attribute."""
        op = GreaterFiOp()
        self.assertEqual(op.uniq, "gt")

    def test_predicate_attribute(self) -> None:
        """Test that GreaterFiOp has correct predicate attribute."""
        op = GreaterFiOp()
        self.assertEqual(op.predicate, gt)


class TestSmallerFiOp(unittest.TestCase):
    def test_uniq_attribute(self) -> None:
        """Test that SmallerFiOp has correct uniq attribute."""
        op = SmallerFiOp()
        self.assertEqual(op.uniq, "lt")

    def test_predicate_attribute(self) -> None:
        """Test that SmallerFiOp has correct predicate attribute."""
        op = SmallerFiOp()
        self.assertEqual(op.predicate, lt)


class TestInFiOp(unittest.TestCase):
    def test_uniq_attribute(self) -> None:
        """Test that InFiOp has correct uniq attribute."""
        op = InFiOp()
        self.assertEqual(op.uniq, "in")

    def test_predicate_attribute(self) -> None:
        """Test that InFiOp has correct predicate attribute."""
        op = InFiOp()
        self.assertEqual(op.predicate, in_op)


class TestFiOpRegistry(unittest.TestCase):
    def test_registry_initialization(self) -> None:
        """Test that registry is initialized with all operators."""
        registry = FiOpRegistry()

        self.assertIsInstance(registry._registry["eq"], EqFiOp)
        self.assertIsInstance(registry._registry["not_eq"], NotEqFiOp)
        self.assertIsInstance(registry._registry["ilike"], ILikeFiOp)
        self.assertIsInstance(registry._registry["regex"], RegexFiOp)
        self.assertIsInstance(registry._registry["none"], IsNoneFiOp)
        self.assertIsInstance(registry._registry["gt"], GreaterFiOp)
        self.assertIsInstance(registry._registry["lt"], SmallerFiOp)
        self.assertIsInstance(registry._registry["in"], InFiOp)

    def test_registry_symbolic_aliases(self) -> None:
        """Test that registry contains symbolic aliases."""
        registry = FiOpRegistry()

        self.assertEqual(registry._registry["=="], registry._registry["eq"])
        self.assertEqual(registry._registry["~="], registry._registry["ilike"])
        self.assertEqual(registry._registry[">"], registry._registry["gt"])
        self.assertEqual(registry._registry["<"], registry._registry["lt"])
        self.assertEqual(registry._registry["!="], registry._registry["not_eq"])

    def test_getitem_with_valid_key(self) -> None:
        """Test __getitem__ with a valid operator key."""
        registry = FiOpRegistry()

        result = registry["eq"]

        self.assertIsInstance(result, EqFiOp)

    def test_getitem_with_alias(self) -> None:
        """Test __getitem__ with a symbolic alias."""
        registry = FiOpRegistry()

        result = registry["=="]

        self.assertIsInstance(result, EqFiOp)
        self.assertEqual(result, registry["eq"])

    def test_getitem_with_invalid_key(self) -> None:
        """Test __getitem__ raises KeyError for invalid key."""
        registry = FiOpRegistry()

        with self.assertRaises(KeyError):
            _ = registry["invalid_key"]

    def test_get_with_valid_key(self) -> None:
        """Test get method with a valid operator key."""
        registry = FiOpRegistry()

        result = registry.get("eq")

        self.assertIsNotNone(result)
        self.assertIsInstance(result, EqFiOp)

    def test_get_with_alias(self) -> None:
        """Test get method with a symbolic alias."""
        registry = FiOpRegistry()

        result = registry.get("==")

        self.assertIsNotNone(result)
        self.assertIsInstance(result, EqFiOp)

    def test_get_with_invalid_key(self) -> None:
        """Test get method returns None for invalid key."""
        registry = FiOpRegistry()

        result = registry.get("invalid_key")

        self.assertIsNone(result)


class TestFilterOpRegistry(unittest.TestCase):
    def test_global_registry_instance(self) -> None:
        """Test that filter_op_registry is a FiOpRegistry instance."""
        self.assertIsInstance(filter_op_registry, FiOpRegistry)

    def test_global_registry_has_operators(self) -> None:
        """Test that global registry contains all operators."""
        self.assertIn("eq", filter_op_registry._registry)
        self.assertIn("not_eq", filter_op_registry._registry)
        self.assertIn("ilike", filter_op_registry._registry)
        self.assertIn("regex", filter_op_registry._registry)
        self.assertIn("none", filter_op_registry._registry)
        self.assertIn("gt", filter_op_registry._registry)
        self.assertIn("lt", filter_op_registry._registry)
        self.assertIn("in", filter_op_registry._registry)

    def test_global_registry_has_aliases(self) -> None:
        """Test that global registry contains symbolic aliases."""
        self.assertIn("==", filter_op_registry._registry)
        self.assertIn("~=", filter_op_registry._registry)
        self.assertIn(">", filter_op_registry._registry)
        self.assertIn("<", filter_op_registry._registry)
        self.assertIn("!=", filter_op_registry._registry)

    def test_global_registry_access(self) -> None:
        """Test accessing operators through global registry."""
        eq_op = filter_op_registry["eq"]
        self.assertIsInstance(eq_op, EqFiOp)

        eq_op_alias = filter_op_registry["=="]
        self.assertEqual(eq_op, eq_op_alias)

        none_op = filter_op_registry.get("invalid")
        self.assertIsNone(none_op)


if __name__ == "__main__":
    unittest.main(argv=["first-arg-is-ignored"], exit=False)
