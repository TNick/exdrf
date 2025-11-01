import unittest
from unittest.mock import ANY, MagicMock, patch

from exdrf.filter import FieldFilter, FilterType

from exdrf_qt.models.selector import Selector

# Mock SQLAlchemy components that are returned or used by Selector
MockColumnElement = MagicMock
MockSelect = MagicMock
mock_and_ = MagicMock()
mock_or_ = MagicMock()
mock_not_ = MagicMock()

# Mock QtModel and QtField as they are dependencies
MockQtModel = MagicMock
MockQtField = MagicMock


class TestSelectorApplyFieldFilter(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_db_model = MagicMock(name="DBModel")
        self.mock_base_select = MockSelect(name="BaseSelect")
        self.mock_qt_field_id = MockQtField(name="IdField")
        self.mock_qt_field_name = MockQtField(name="NameField")

        self.fields_map = {
            "id": self.mock_qt_field_id,
            "name": self.mock_qt_field_name,
        }
        self.selector = Selector(
            db_model=self.mock_db_model,  # type: ignore
            base=self.mock_base_select,
            fields=self.fields_map,  # type: ignore
        )

    def test_apply_field_filter_with_dict(self) -> None:
        """Test apply_field_filter with a dictionary input."""
        filter_dict = {"fld": "id", "op": "==", "vl": 1}
        mock_filter_result = MockColumnElement(name="IdFilterResult")
        self.mock_qt_field_id.apply_filter.return_value = mock_filter_result

        result = self.selector.apply_field_filter(filter_dict)

        self.mock_qt_field_id.apply_filter.assert_called_once()
        # Check that FieldFilter was constructed and passed
        _args, kwargs = self.mock_qt_field_id.apply_filter.call_args
        self.assertIsInstance(kwargs["item"], FieldFilter)
        self.assertEqual(kwargs["item"].fld, "id")
        self.assertEqual(kwargs["item"].op, "==")
        self.assertEqual(kwargs["item"].vl, 1)
        self.assertEqual(kwargs["selector"], self.selector)
        self.assertEqual(result, mock_filter_result)

    def test_apply_field_filter_with_field_filter_instance(self) -> None:
        """Test apply_field_filter with a FieldFilter instance."""
        field_filter_instance = FieldFilter(fld="name", op="like", vl="test%")
        mock_filter_result = MockColumnElement(name="NameFilterResult")
        self.mock_qt_field_name.apply_filter.return_value = mock_filter_result

        result = self.selector.apply_field_filter(field_filter_instance)

        self.mock_qt_field_name.apply_filter.assert_called_once_with(
            item=field_filter_instance, selector=self.selector
        )
        self.assertEqual(result, mock_filter_result)

    def test_apply_field_filter_non_existent_field(self) -> None:
        """Test apply_field_filter raises KeyError for a non-existent field."""
        filter_dict = {"fld": "non_existent", "op": "==", "vl": 1}
        with self.assertRaises(KeyError):
            self.selector.apply_field_filter(filter_dict)


@patch("exdrf_qt.models.selector.and_", mock_and_)
@patch("exdrf_qt.models.selector.or_", mock_or_)
@patch("exdrf_qt.models.selector.not_", mock_not_)
class TestSelectorApplySubsetAndRun(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_db_model = MagicMock(name="TestDBModel")
        self.mock_base_select = MockSelect(name="BaseSelectInstance")
        self.mock_id_field = MockQtField(name="IdField")
        self.mock_name_field = MockQtField(name="NameField")
        self.mock_other_field = MockQtField(name="OtherField")

        self.fields = {
            "id": self.mock_id_field,
            "name": self.mock_name_field,
            "other": self.mock_other_field,
        }

        # Reset mocks for each test
        mock_and_.reset_mock()
        mock_or_.reset_mock()
        mock_not_.reset_mock()
        self.mock_id_field.reset_mock()
        self.mock_name_field.reset_mock()
        self.mock_other_field.reset_mock()
        self.mock_base_select.reset_mock()
        self.mock_base_select.where.return_value = MockSelect(
            name="WhereSelect"
        )
        # For chaining
        self.mock_base_select.join.return_value = self.mock_base_select

        self.selector = Selector(
            db_model=self.mock_db_model,  # type: ignore
            base=self.mock_base_select,
            fields=self.fields,  # type: ignore
        )

        # Mock responses from QtField.apply_filter
        self.id_filter_1_eq = MockColumnElement(name="id_filter_1_eq")
        self.id_filter_2_eq = MockColumnElement(name="id_filter_2_eq")
        self.name_filter_like = MockColumnElement(name="name_filter_like")
        self.other_filter_gt = MockColumnElement(name="other_filter_gt")

        def mock_apply_filter_side_effect(item, selector):
            if item.fld == "id" and item.vl == 1:
                return self.id_filter_1_eq
            if item.fld == "id" and item.vl == 2:
                return self.id_filter_2_eq
            if item.fld == "name" and item.op == "like":
                return self.name_filter_like
            if item.fld == "other" and item.op == ">":
                return self.other_filter_gt
            return MockColumnElement(
                name=f"GenericMockFilter_{item.fld}_{item.vl}"
            )

        self.mock_id_field.apply_filter.side_effect = (
            mock_apply_filter_side_effect  # type: ignore
        )
        self.mock_name_field.apply_filter.side_effect = (
            mock_apply_filter_side_effect
        )
        self.mock_other_field.apply_filter.side_effect = (
            mock_apply_filter_side_effect
        )

        # Mock return values for logical operators
        mock_and_.return_value = MockColumnElement(name="MockAndClause")
        mock_or_.return_value = MockColumnElement(name="MockOrClause")
        mock_not_.return_value = MockColumnElement(name="MockNotClause")

    def test_run_no_filters(self) -> None:
        """Test run with an empty filter list."""
        result_select = self.selector.run([])
        self.assertEqual(result_select, self.mock_base_select)
        self.mock_base_select.where.assert_not_called()

    def test_run_simple_field_filter_dict(self) -> None:
        """Test run with a single field filter as a dictionary."""
        filters: FilterType = [
            {"fld": "id", "op": "==", "vl": 1}  # type: ignore
        ]
        self.selector.run(filters)
        self.mock_id_field.apply_filter.assert_called_with(
            item=FieldFilter(fld="id", op="==", vl=1), selector=self.selector
        )
        self.mock_base_select.where.assert_called_once_with(self.id_filter_1_eq)

    def test_run_simple_field_filter_instance(self) -> None:
        """Test run with a single FieldFilter instance."""
        ff = FieldFilter(fld="name", op="like", vl="test")
        filters: FilterType = [ff]
        self.selector.run(filters)
        self.mock_name_field.apply_filter.assert_called_with(
            item=ff, selector=self.selector
        )
        self.mock_base_select.where.assert_called_once_with(
            self.name_filter_like
        )

    def test_run_implicit_and_multiple_filters(self) -> None:
        """Test run with a list of filters (implicit AND)."""
        filters: FilterType = [  # type: ignore
            {"fld": "id", "op": "==", "vl": 1},  # type: ignore
            {"fld": "name", "op": "like", "vl": "alpha"},  # type: ignore
        ]
        # We expect apply_subset to return a list of ColumnElements
        # and run to pass them to where.
        # _single_def will be called for each.

        self.selector.run(filters)

        self.mock_id_field.apply_filter.assert_any_call(
            item=FieldFilter(fld="id", op="==", vl=1), selector=self.selector
        )
        self.mock_name_field.apply_filter.assert_any_call(
            item=FieldFilter(fld="name", op="like", vl="alpha"),
            selector=self.selector,
        )
        # where should be called with the results of apply_filter
        self.mock_base_select.where.assert_called_once_with(
            self.id_filter_1_eq, ANY
        )

    def test_run_explicit_and_operator(self) -> None:
        """Test run with an explicit AND operator."""
        filters: FilterType = [  # type: ignore
            "AND",  # type: ignore
            [
                {"fld": "id", "op": "==", "vl": 1},  # type: ignore
                {"fld": "name", "op": "like", "vl": "beta"},  # type: ignore
            ],
        ]

        mock_and_.side_effect = None  # Clear any previous side_effect
        mock_and_.return_value = MockColumnElement("AND_Result")

        self.selector.run(filters)

        # apply_subset for the inner list
        self.mock_id_field.apply_filter.assert_any_call(
            item=FieldFilter(fld="id", op="==", vl=1), selector=self.selector
        )
        self.mock_name_field.apply_filter.assert_any_call(
            item=FieldFilter(fld="name", op="like", vl="beta"),
            selector=self.selector,
        )

        # Based on mocked apply_filter
        mock_and_.assert_called_once_with(self.id_filter_1_eq, ANY)
        self.mock_base_select.where.assert_called_once_with(
            mock_and_.return_value
        )

    def test_run_explicit_or_operator(self) -> None:
        """Test run with an explicit OR operator."""
        filters: FilterType = [  # type: ignore
            "OR",  # type: ignore
            [
                {"fld": "id", "op": "==", "vl": 2},  # type: ignore
                {"fld": "other", "op": ">", "vl": 10},  # type: ignore
            ],
        ]
        mock_or_.side_effect = None  # Clear any previous side_effect
        mock_or_.return_value = MockColumnElement("OR_Result")
        self.selector.run(filters)

        self.mock_id_field.apply_filter.assert_any_call(
            item=FieldFilter(fld="id", op="==", vl=2), selector=self.selector
        )
        self.mock_other_field.apply_filter.assert_any_call(
            item=FieldFilter(fld="other", op=">", vl=10), selector=self.selector
        )

        mock_or_.assert_called_once_with(
            self.id_filter_2_eq, self.other_filter_gt
        )
        self.mock_base_select.where.assert_called_once_with(
            mock_or_.return_value
        )

    def test_run_not_operator(self) -> None:
        """Test run with a NOT operator."""
        filters: FilterType = [
            "NOT",  # type: ignore
            {"fld": "id", "op": "==", "vl": 1},  # type: ignore
        ]

        mock_not_.return_value = MockColumnElement("NOT_Result")
        self.selector.run(filters)

        self.mock_id_field.apply_filter.assert_called_with(
            item=FieldFilter(fld="id", op="==", vl=1), selector=self.selector
        )
        mock_not_.assert_called_once_with(self.id_filter_1_eq)
        self.mock_base_select.where.assert_called_once_with(
            mock_not_.return_value
        )

    def test_run_complex_nested_filter(self) -> None:
        """Test run with a complex nested filter as provided by user."""
        filters: FilterType = [  # type: ignore
            "AND",  # type: ignore
            [
                ["OR", [{"fld": "id", "op": "==", "vl": 1}]],  # type: ignore
                ["OR", [{"fld": "id", "op": "==", "vl": 2}]],  # type: ignore
            ],
        ]

        # Mock specific return values for this complex structure
        or_result_1 = MockColumnElement("OR_ID_1")
        or_result_2 = MockColumnElement("OR_ID_2")
        and_final_result = MockColumnElement("AND_FINAL")

        # _single_def for {"fld": "id", "op": "==", "vl": 1} -> id_filter_1_eq
        # _single_def for ["OR", [{"fld": "id", "op": "==", "vl": 1}]]
        #   -> mock_or_ called with id_filter_1_eq, returns or_result_1

        # _single_def for {"fld": "id", "op": "==", "vl": 2} -> id_filter_2_eq
        # _single_def for ["OR", [{"fld": "id", "op": "==", "vl": 2}]]
        #   -> mock_or_ called with id_filter_2_eq, returns or_result_2

        # apply_subset for ["AND", [["OR", ...], ["OR", ...]]]
        # -> mock_and_ with or_result_1, or_result_2, returns and_final_result

        # Configure side effects for or_ and and_ to trace calls
        def or_side_effect(*args):
            if args == (self.id_filter_1_eq,):
                return or_result_1
            if args == (self.id_filter_2_eq,):
                return or_result_2
            return MockColumnElement(name=f"UnexpectedOrCall_{args}")

        mock_or_.side_effect = or_side_effect
        mock_and_.return_value = and_final_result

        self.selector.run(filters)

        # Check apply_filter calls for id fields
        self.mock_id_field.apply_filter.assert_any_call(
            item=FieldFilter(fld="id", op="==", vl=1), selector=self.selector
        )
        self.mock_id_field.apply_filter.assert_any_call(
            item=FieldFilter(fld="id", op="==", vl=2), selector=self.selector
        )

        # Check OR calls
        mock_or_.assert_any_call(self.id_filter_1_eq)
        mock_or_.assert_any_call(self.id_filter_2_eq)

        # Check AND call
        mock_and_.assert_called_once_with(or_result_1, or_result_2)

        # Check final where clause
        self.mock_base_select.where.assert_called_once_with(and_final_result)

    def test_run_with_joins(self) -> None:
        """Test that joins are applied if present."""
        mock_join_1 = MagicMock(name="Join1")
        mock_join_2 = MagicMock(name="Join2")
        self.selector.joins = [mock_join_1, mock_join_2]

        filters: FilterType = [
            {"fld": "id", "op": "==", "vl": 1}  # type: ignore
        ]
        self.selector.run(filters)

        # Ensure base select has join called correctly
        self.mock_base_select.join.assert_any_call(mock_join_1)
        self.mock_base_select.join.assert_any_call(mock_join_2)
        self.assertEqual(self.mock_base_select.join.call_count, 2)

        # The select object from the last join should be used for where. Our
        # mock_base_select.join returns self.mock_base_select, so this is fine.
        self.mock_base_select.where.assert_called_once_with(self.id_filter_1_eq)

    def test_run_with_join_with_kwargs(self) -> None:
        """Test that joins with kwargs are applied correctly."""
        mock_join_table = MagicMock(name="JoinTable")
        join_with_kwargs = (mock_join_table, {"isouter": True})
        self.selector.joins = [join_with_kwargs]

        filters: FilterType = [
            {"fld": "id", "op": "==", "vl": 1}  # type: ignore
        ]
        self.selector.run(filters)

        # Ensure join is called with kwargs
        self.mock_base_select.join.assert_called_once_with(
            mock_join_table, isouter=True
        )

    def test_run_with_join_tuple_no_kwargs(self) -> None:
        """Test that tuple joins without kwargs work."""
        mock_join_table = MagicMock(name="JoinTable")
        join_tuple = (mock_join_table,)
        self.selector.joins = [join_tuple]

        filters: FilterType = [
            {"fld": "id", "op": "==", "vl": 1}  # type: ignore
        ]
        self.selector.run(filters)

        self.mock_base_select.join.assert_called_once_with(mock_join_table)

    def test_apply_subset_malformed_logical_op_length(self) -> None:
        filters: FilterType = [  # type: ignore
            ["AND", {"fld": "id", "op": "==", "vl": 1}, "extra"]  # type: ignore
        ]
        # This will be caught by _single_def when processing the inner list
        err_msg = "Def for logical op `and` must be 2 items"
        with self.assertRaisesRegex(ValueError, err_msg):
            self.selector.apply_subset(filters)

    def test_single_def_malformed_logical_op_length(self) -> None:
        # Test _single_def directly for coverage of its specific error messages
        definition = ["AND", {"fld": "id", "op": "==", "vl": 1}, "extra"]
        err_msg = "Def for logical op `and` must be 2 items"
        with self.assertRaisesRegex(ValueError, err_msg):
            self.selector._single_def(definition)

    def test_single_def_and_or_operand_not_list(self) -> None:
        # Operand not a list
        definition_and = ["AND", {"fld": "id", "op": "==", "vl": 1}]
        err_msg_and = "Operands for 'and' operator must be a list."
        with self.assertRaisesRegex(ValueError, err_msg_and):
            self.selector._single_def(definition_and)

        # Operand not a list
        definition_or = ["OR", {"fld": "id", "op": "==", "vl": 1}]
        err_msg_or = "Operands for 'or' operator must be a list."
        with self.assertRaisesRegex(ValueError, err_msg_or):
            self.selector._single_def(definition_or)

    def test_single_def_invalid_operator_in_list_def(self) -> None:
        # Operator not string
        definition = [123, [{"fld": "id", "op": "==", "vl": 1}]]
        err_msg = "Operator in list-based filter definition must be a string"
        with self.assertRaisesRegex(ValueError, err_msg):
            self.selector._single_def(definition)

    def test_single_def_invalid_definition_type(self) -> None:
        err_msg = "Invalid filter definition type"
        with self.assertRaisesRegex(TypeError, err_msg):
            self.selector._single_def(12345)

    def test_single_def_empty_list_returns_none(self) -> None:
        """Test _single_def with empty list returns None."""
        result = self.selector._single_def([])
        self.assertIsNone(result)

    def test_apply_subset_empty_returns_empty_list(self) -> None:
        """Test apply_subset with empty list returns empty list."""
        result = self.selector.apply_subset([])
        self.assertEqual(result, [])

    def test_apply_subset_handles_exception_in_single_def(self) -> None:
        """Test apply_subset handles exceptions during _single_def gracefully."""
        # Create a filter that will cause an error in _single_def
        # (non-existent field)
        filters: FilterType = [
            {"fld": "nonexistent", "op": "==", "vl": 1}  # type: ignore
        ]

        # apply_subset should catch the exception and log it
        result = self.selector.apply_subset(filters)

        # Should return empty list since the filter failed
        self.assertEqual(result, [])


class TestSelectorFromQtModel(unittest.TestCase):
    def test_from_qt_model(self) -> None:
        """Test class method from_qt_model."""
        mock_qt_model_instance = MockQtModel(name="QtModelInstance")
        mock_qt_model_instance.db_model = MagicMock(name="ActualDBModel")
        mock_qt_model_instance.base_selection = MockSelect(
            name="BaseSelFromQtModel"
        )

        mock_field1 = MockQtField(name="Field1Instance")
        mock_field1.name = "field_one"
        mock_field2 = MockQtField(name="Field2Instance")
        mock_field2.name = "field_two"
        mock_qt_model_instance.fields = [mock_field1, mock_field2]

        selector_instance = Selector.from_qt_model(mock_qt_model_instance)

        self.assertIsInstance(selector_instance, Selector)
        self.assertEqual(
            selector_instance.db_model, mock_qt_model_instance.db_model
        )
        self.assertEqual(
            selector_instance.base, mock_qt_model_instance.base_selection
        )
        self.assertEqual(len(selector_instance.fields), 2)
        self.assertEqual(selector_instance.fields["field_one"], mock_field1)
        self.assertEqual(selector_instance.fields["field_two"], mock_field2)
        self.assertEqual(selector_instance.qt_model, mock_qt_model_instance)
        self.assertEqual(selector_instance.joins, [])  # Default
        self.assertEqual(selector_instance.depth, 0)  # Default


if __name__ == "__main__":
    unittest.main(argv=["first-arg-is-ignored"], exit=False)
