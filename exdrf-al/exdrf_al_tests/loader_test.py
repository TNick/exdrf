from unittest.mock import MagicMock

import pytest
from exdrf.resource import ExResource
from sqlalchemy import Integer
from sqlalchemy.orm import mapped_column

from exdrf_al.loader import (
    dataset_from_sqlalchemy,
    field_from_sql_col,
    field_from_sql_rel,
    res_by_table_name,
    sql_col_to_type,
)


class TestResByTableName:
    def test_not_found(self, TwoResNoFields):
        dataset, db_conn, MockModelA, MockModelB = TwoResNoFields

        with pytest.raises(KeyError):
            res_by_table_name(dataset, "xxx")

    def test_found(self, TwoResNoFields):
        dataset, db_conn, MockModelA, MockModelB = TwoResNoFields

        res = res_by_table_name(dataset, "mock_a")
        assert res.name == "MockModelA"
        assert res.src == MockModelA

        res = res_by_table_name(dataset, "mock_b")
        assert res.name == "MockModelB"
        assert res.src == MockModelB

    def test_multiple_found(self, LocalBase, TwoResNoFields):
        dataset, db_conn, MockModelA, MockModelB = TwoResNoFields

        # Create a second resource with the same table name
        MockModelC = MagicMock(spec=LocalBase)
        MockModelC.__tablename__ = "mock_a"
        MockModelC.id = mapped_column(
            Integer, primary_key=True, doc="Primary key of mock_a."
        )

        dataset.resources.append(
            ExResource(
                name="MockModelC",
                src=MockModelC,
                dataset=dataset,
            )
        )

        with pytest.raises(ValueError):
            res_by_table_name(dataset, "mock_a")


class TestSqlColToType:
    @pytest.mark.parametrize(
        "column_type, expected_field, expected_info, extra_updates",
        [
            ("BLOB", "BlobField", "BlobInfo", {}),
            ("INTEGER", "IntField", "IntInfo", {}),
            ("TEXT", "StrField", "StrInfo", {}),
            ("FLOAT", "FloatField", "FloatInfo", {}),
            ("BOOLEAN", "BoolField", "BoolInfo", {}),
            ("DATE", "DateField", "DateInfo", {}),
            ("TIME", "TimeField", "TimeInfo", {}),
            ("DATETIME", "DateTimeField", "DateTimeInfo", {}),
            ("VARCHAR", "StrField", "StrInfo", {}),
            ("JSON", "FormattedField", "FormattedInfo", {"format": "json"}),
            ("VARCHAR(255)", "StrField", "StrInfo", {"max_length": 255}),
        ],
    )
    def test_sql_col_to_type(
        self, column_type, expected_field, expected_info, extra_updates
    ):

        column = MagicMock()
        column.type = MagicMock()
        column.type.__str__ = lambda _: column_type

        extra = {}
        field, info = sql_col_to_type(column, extra)

        assert field.__name__ == expected_field
        assert info.__name__ == expected_info
        for key, value in extra_updates.items():
            assert extra[key] == value

    def test_unknown_field_type(self):

        column = MagicMock()
        column.type = MagicMock()
        column.type.__str__ = lambda _: "UNKNOWN_TYPE"

        extra = {}
        with pytest.raises(AssertionError, match="Unknown field type"):
            sql_col_to_type(column, extra)


class TestFieldFromSqlCol:
    def test_field_creation(self, mocker):
        # Mock dependencies
        mock_resource = MagicMock(
            name="ExResource",
        )
        mock_column = MagicMock()
        mock_column.key = "test_column"
        mock_column.doc = "Test column description"
        mock_column.nullable = True
        mock_column.primary_key = False
        mock_column.info = {"example_key": "example_value"}

        mock_ctor = mocker.patch("exdrf_al.loader.IntField")
        mock_ctor.__name__ = "IntField"
        mock_parser = mocker.patch("exdrf_al.loader.IntInfo")
        mock_parser.model_validate.return_value.model_dump.return_value = {
            "example_key": "example_value"
        }

        mocker.patch(
            "exdrf_al.loader.sql_col_to_type",
            return_value=(mock_ctor, mock_parser),
        )

        # Call the function
        result = field_from_sql_col(
            mock_resource, mock_column, custom_arg="custom_value"
        )

        # Assertions
        mock_parser.model_validate.assert_called_once_with(
            mock_column.info, strict=True
        )
        mock_ctor.assert_called_once_with(
            resource=mock_resource,
            src=mock_column,
            name="test_column",
            title="Test Column",
            description="Test column description",
            nullable=True,
            primary=False,
            example_key="example_value",
            custom_arg="custom_value",
        )
        mock_resource.add_field.assert_called_once_with(mock_ctor.return_value)
        assert result == mock_ctor.return_value

    def test_field_creation_with_missing_info(self, mocker):
        # Mock dependencies
        mock_resource = MagicMock()
        mock_column = MagicMock()
        mock_column.key = "test_column"
        mock_column.doc = None
        mock_column.nullable = False
        mock_column.primary_key = True
        mock_column.info = {}

        mock_ctor = mocker.patch("exdrf_al.loader.StrField")
        mock_ctor.__name__ = "StrField"
        mock_parser = mocker.patch("exdrf_al.loader.StrInfo")
        mock_parser.model_validate.return_value.model_dump.return_value = {}

        mocker.patch(
            "exdrf_al.loader.sql_col_to_type",
            return_value=(mock_ctor, mock_parser),
        )

        # Call the function
        result = field_from_sql_col(mock_resource, mock_column)

        # Assertions
        mock_parser.model_validate.assert_called_once_with(
            mock_column.info, strict=True
        )
        mock_ctor.assert_called_once_with(
            resource=mock_resource,
            src=mock_column,
            name="test_column",
            title="Test Column",
            description=None,
            nullable=False,
            primary=True,
        )
        mock_resource.add_field.assert_called_once_with(mock_ctor.return_value)
        assert result == mock_ctor.return_value

    def test_field_creation_with_invalid_info(self, mocker):
        # Mock dependencies
        mock_resource = MagicMock()
        mock_column = MagicMock()
        mock_column.key = "test_column"
        mock_column.info = {"invalid_key": "invalid_value"}

        mock_parser = mocker.patch("exdrf_al.loader.IntInfo")
        mock_parser.model_validate.side_effect = ValueError("Invalid info")

        mocker.patch(
            "exdrf_al.loader.sql_col_to_type",
            return_value=(MagicMock(), mock_parser),
        )

        # Call the function and assert exception
        with pytest.raises(ValueError, match="Invalid info"):
            field_from_sql_col(mock_resource, mock_column)


class TestFieldFromSqlRel:
    def test_field_creation(self, mocker):
        # Mock dependencies
        mock_resource = MagicMock(name="ExResource")
        mock_relation = MagicMock()
        mock_relation.key = "test_relation"
        mock_relation.info = {
            "direction": "OneToMany",
            "example_key": "example_value",
        }
        mock_relation.uselist = True
        mock_relation.mapper.class_.__name__ = "RelatedModel"

        mock_ctor = mocker.patch("exdrf_al.loader.RefOneToManyField")
        mock_ctor.__name__ = "RefOneToManyField"
        mock_parser = mocker.patch("exdrf_al.loader.RelExtraInfo")
        mock_parser.model_validate.return_value.model_dump.return_value = {
            "direction": "OneToMany",
            "example_key": "example_value",
        }

        # Call the function
        result = field_from_sql_rel(
            resource=mock_resource,
            relation=mock_relation,
            custom_arg="custom_value",
        )

        # Assertions
        mock_parser.model_validate.assert_called_once_with(
            mock_relation.info, strict=True
        )
        mock_ctor.assert_called_once_with(
            ref=mock_resource.dataset["RelatedModel"],
            is_list=True,
            resource=mock_resource,
            src=mock_relation,
            name="test_relation",
            title="Test Relation",
            example_key="example_value",
            custom_arg="custom_value",
        )
        mock_resource.add_field.assert_called_once_with(mock_ctor.return_value)
        assert result == mock_ctor.return_value

    def test_invalid_direction(self, mocker):
        # Mock dependencies
        mock_resource = MagicMock(name="ExResource")
        mock_relation = MagicMock()
        mock_relation.key = "test_relation"
        mock_relation.info = {"direction": "InvalidDirection"}

        mock_parser = mocker.patch("exdrf_al.loader.RelExtraInfo")
        mock_parser.model_validate.return_value.model_dump.return_value = {
            "direction": "InvalidDirection"
        }

        # Call the function and assert exception
        with pytest.raises(ValueError, match="Invalid dir: InvalidDirection"):
            field_from_sql_rel(resource=mock_resource, relation=mock_relation)

    def test_missing_direction(self, mocker):
        # Mock dependencies
        mock_resource = MagicMock(name="ExResource")
        mock_relation = MagicMock()
        mock_relation.key = "test_relation"
        mock_relation.info = {}

        mock_parser = mocker.patch("exdrf_al.loader.RelExtraInfo")
        mock_parser.model_validate.return_value.model_dump.return_value = {}

        # Call the function and assert exception
        with pytest.raises(AssertionError, match="Direction must be specified"):
            field_from_sql_rel(resource=mock_resource, relation=mock_relation)

    def test_invalid_uselist(self, mocker):
        # Mock dependencies
        mock_resource = MagicMock(name="ExResource")
        mock_relation = MagicMock()
        mock_relation.key = "test_relation"
        mock_relation.info = {"direction": "OneToMany"}
        mock_relation.uselist = False

        mock_parser = mocker.patch("exdrf_al.loader.RelExtraInfo")
        mock_parser.model_validate.return_value.model_dump.return_value = {
            "direction": "OneToMany"
        }

        # Call the function and assert exception
        with pytest.raises(AssertionError, match="Invalid use of `uselist`"):
            field_from_sql_rel(resource=mock_resource, relation=mock_relation)

    def test_many_to_many_with_intermediate(self, mocker):
        # Mock dependencies
        mock_resource = MagicMock(name="ExResource")
        mock_relation = MagicMock()
        mock_relation.key = "test_relation"
        mock_relation.info = {"direction": "ManyToMany"}
        mock_relation.uselist = True
        mock_relation.secondary.key = "intermediate_table"
        mock_relation.mapper.class_.__name__ = "RelatedModel"

        mock_ctor = mocker.patch("exdrf_al.loader.RefManyToManyField")
        mock_ctor.__name__ = "RefManyToManyField"
        mock_parser = mocker.patch("exdrf_al.loader.RelExtraInfo")
        mock_parser.model_validate.return_value.model_dump.return_value = {
            "direction": "ManyToMany"
        }
        mock_res_by_table_name = mocker.patch(
            "exdrf_al.loader.res_by_table_name"
        )
        mock_res_by_table_name.return_value = "IntermediateResource"

        # Call the function
        result = field_from_sql_rel(
            resource=mock_resource, relation=mock_relation
        )

        # Assertions
        mock_parser.model_validate.assert_called_once_with(
            mock_relation.info, strict=True
        )
        mock_res_by_table_name.assert_called_once_with(
            mock_resource.dataset, "intermediate_table"
        )
        mock_ctor.assert_called_once_with(
            ref=mock_resource.dataset["RelatedModel"],
            is_list=True,
            resource=mock_resource,
            src=mock_relation,
            name="test_relation",
            title="Test Relation",
            ref_intermediate="IntermediateResource",
        )
        mock_resource.add_field.assert_called_once_with(mock_ctor.return_value)
        assert result == mock_ctor.return_value


class TestDatasetFromSqlAlchemy:
    def test_dataset_population(self, mocker):
        # Mock dependencies
        mock_dataset = MagicMock(name="ExDataset")
        mock_dataset.res_class = MagicMock(name="ExResource")
        mock_base = MagicMock(name="Base")

        mock_model = MagicMock(name="Model")
        mock_model.__name__ = "MockModel"
        mock_model.__doc__ = "Mock model docstring."
        mock_model.info = {}

        # mock_column = MagicMock(name="Column")
        # mock_relation = MagicMock(name="Relation")

        mock_visitor = mocker.patch("exdrf_al.loader.DbVisitor")
        mock_visitor.run.side_effect = lambda base: None

        mock_field_from_sql_col = mocker.patch(
            "exdrf_al.loader.field_from_sql_col"
        )
        mock_field_from_sql_rel = mocker.patch(
            "exdrf_al.loader.field_from_sql_rel"
        )

        # Call the function
        result = dataset_from_sqlalchemy(mock_dataset, base=mock_base)

        # Assertions
        mock_visitor.run.assert_any_call(base=mock_base)
        mock_field_from_sql_col.assert_not_called()  # No columns processed in this test
        # No relations processed in this test
        mock_field_from_sql_rel.assert_not_called()
        assert result == mock_dataset

    def test_error_parsing_label(self, mocker):
        # Mock dependencies
        mock_dataset = MagicMock(name="ExDataset")
        mock_dataset.res_class = MagicMock(name="ExResource")
        mock_base = MagicMock(name="Base")

        mock_model = MagicMock(name="Model")
        mock_model.__name__ = "MockModel"
        mock_model.__doc__ = "Mock model docstring."
        mock_model.info = {}

        mock_visitor = mocker.patch("exdrf_al.loader.DbVisitor")
        mock_visitor.run.side_effect = lambda base: None

        mock_extra_info = mocker.patch("exdrf_al.loader.DbVisitor.extra_info")
        mock_extra_info.return_value.get_layer_ast.side_effect = Exception(
            "Parsing error"
        )

        # Call the function and assert exception
        with pytest.raises(
            ValueError, match="Error parsing label for MockModel"
        ):
            dataset_from_sqlalchemy(mock_dataset, base=mock_base)

    def test_field_creation_from_columns(self, mocker):
        # Mock dependencies
        mock_dataset = MagicMock(name="ExDataset")
        mock_dataset.res_class = MagicMock(name="ExResource")
        mock_base = MagicMock(name="Base")

        mock_model = MagicMock(name="Model")
        mock_model.__name__ = "MockModel"
        mock_model.__doc__ = "Mock model docstring."
        mock_model.info = {}

        # mock_column = MagicMock(name="Column")

        mock_visitor = mocker.patch("exdrf_al.loader.DbVisitor")
        mock_visitor.run.side_effect = lambda base: None

        mock_field_from_sql_col = mocker.patch(
            "exdrf_al.loader.field_from_sql_col"
        )

        # Call the function
        dataset_from_sqlalchemy(mock_dataset, base=mock_base)

        # Assertions
        mock_field_from_sql_col.assert_not_called()  # No columns processed in this test

    def test_field_creation_from_relations(self, mocker):
        # Mock dependencies
        mock_dataset = MagicMock(name="ExDataset")
        mock_dataset.res_class = MagicMock(name="ExResource")
        mock_base = MagicMock(name="Base")

        mock_model = MagicMock(name="Model")
        mock_model.__name__ = "MockModel"
        mock_model.__doc__ = "Mock model docstring."
        mock_model.info = {}

        # mock_relation = MagicMock(name="Relation")

        mock_visitor = mocker.patch("exdrf_al.loader.DbVisitor")
        mock_visitor.run.side_effect = lambda base: None

        mock_field_from_sql_rel = mocker.patch(
            "exdrf_al.loader.field_from_sql_rel"
        )

        # Call the function
        dataset_from_sqlalchemy(mock_dataset, base=mock_base)

        # Assertions
        # No relations processed in this test
        mock_field_from_sql_rel.assert_not_called()
