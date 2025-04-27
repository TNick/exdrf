from unittest.mock import Mock

import pytest

from exdrf.constants import (
    FIELD_TYPE_REF_MANY_TO_MANY,
    FIELD_TYPE_REF_MANY_TO_ONE,
    FIELD_TYPE_REF_ONE_TO_MANY,
    FIELD_TYPE_REF_ONE_TO_ONE,
)
from exdrf.field import ExField


@pytest.fixture
def mock_resource():
    resource = Mock()
    resource.name = "test_resource"
    return resource


@pytest.fixture
def ex_field(mock_resource):
    return ExField(
        name="test_field",
        resource=mock_resource,
        type_name=FIELD_TYPE_REF_ONE_TO_MANY,
        is_list=True,
        primary=True,
        visible=True,
        read_only=False,
        nullable=False,
        sortable=True,
        filterable=True,
        exportable=True,
        qsearch=True,
        resizable=True,
    )


def test_exfield_initialization(ex_field):
    assert ex_field.name == "test_field"
    assert ex_field.resource.name == "test_resource"
    assert ex_field.type_name == FIELD_TYPE_REF_ONE_TO_MANY
    assert ex_field.is_list is True
    assert ex_field.primary is True
    assert ex_field.visible is True
    assert ex_field.read_only is False
    assert ex_field.nullable is False


def test_exfield_pascal_case_name(ex_field):
    assert ex_field.pascal_case_name == "TestField"


def test_exfield_snake_case_name(ex_field):
    assert ex_field.snake_case_name == "test_field"


def test_exfield_snake_case_name_plural(ex_field):
    ex_field.name = "test_field"
    assert ex_field.snake_case_name_plural == "test_fields"


def test_exfield_camel_case_name(ex_field):
    assert ex_field.camel_case_name == "testField"


def test_exfield_text_name(ex_field):
    assert ex_field.text_name == "Test Field"


def test_exfield_doc_lines(ex_field):
    ex_field.description = "This is a test field."
    assert ex_field.doc_lines == ["This is a test field."]


def test_exfield_is_ref_type(ex_field):
    assert ex_field.is_ref_type is True


def test_exfield_is_one_to_many_type(ex_field):
    assert ex_field.is_one_to_many_type is True


def test_exfield_is_one_to_one_type(ex_field):
    ex_field.type_name = FIELD_TYPE_REF_ONE_TO_ONE
    assert ex_field.is_one_to_one_type is True


def test_exfield_is_many_to_many_type(ex_field):
    ex_field.type_name = FIELD_TYPE_REF_MANY_TO_MANY
    assert ex_field.is_many_to_many_type is True


def test_exfield_is_many_to_one_type(ex_field):
    ex_field.type_name = FIELD_TYPE_REF_MANY_TO_ONE
    assert ex_field.is_many_to_one_type is True


def test_exfield_visit(ex_field):
    mock_visitor = Mock()
    mock_visitor.visit_field.return_value = True
    assert ex_field.visit(mock_visitor) is True
    mock_visitor.visit_field.assert_called_once_with(ex_field)


def test_exfield_extra_ref(ex_field):
    mock_dataset = Mock()
    assert ex_field.extra_ref(mock_dataset) == []
