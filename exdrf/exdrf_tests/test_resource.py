from unittest.mock import Mock

import pytest

from exdrf.resource import ExResource


def test_exresource_initialization():
    resource = ExResource(name="TestResource")
    assert resource.name == "TestResource"
    assert resource.fields == []
    assert resource.categories == []
    assert resource.description == ""
    assert resource.src is None
    assert resource.label_ast is None


def test_exresource_repr():
    resource = ExResource(name="TestResource")
    assert repr(resource) == "<Resource TestResource (0 fields)>"


def test_exresource_add_field():
    mock_field = Mock()
    mock_field.name = "test_field"
    mock_field.type_name = "string"
    mock_field.category = None

    resource = ExResource(name="TestResource")
    resource.add_field(mock_field)

    assert len(resource.fields) == 1
    assert resource.fields[0] == mock_field
    assert mock_field.resource == resource


def test_exresource_getitem_by_index():
    mock_field = Mock()
    mock_field.name = "test_field"
    mock_field.type_name = "string"

    resource = ExResource(name="TestResource")
    resource.add_field(mock_field)

    assert resource[0] == mock_field


def test_exresource_getitem_by_name():
    mock_field = Mock()
    mock_field.name = "test_field"
    mock_field.type_name = "string"

    resource = ExResource(name="TestResource")
    resource.add_field(mock_field)

    assert resource["test_field"] == mock_field


def test_exresource_getitem_keyerror():
    resource = ExResource(name="TestResource")
    with pytest.raises(KeyError):
        _ = resource["nonexistent_field"]


def test_exresource_pascal_case_name():
    resource = ExResource(name="TestResource")
    assert resource.pascal_case_name == "TestResource"


def test_exresource_snake_case_name():
    resource = ExResource(name="TestResource")
    assert resource.snake_case_name == "test_resource"


def test_exresource_snake_case_name_plural():
    resource = ExResource(name="TestResource")
    assert resource.snake_case_name_plural == "test_resources"


def test_exresource_camel_case_name():
    resource = ExResource(name="TestResource")
    assert resource.camel_case_name == "testResource"


def test_exresource_text_name():
    resource = ExResource(name="TestResource")
    assert resource.text_name == "Test resource"


def test_exresource_doc_lines():
    resource = ExResource(
        name="TestResource", description="This is a test resource."
    )
    assert resource.doc_lines == ["This is a test resource."]


def test_exresource_get_dependencies():
    mock_field = Mock()
    mock_field.is_ref_type = True
    mock_field.ref = Mock()
    mock_field.ref.name = "DependencyResource"
    mock_field.extra_ref = Mock(return_value=[])

    resource = ExResource(name="TestResource")
    resource.add_field(mock_field)

    dependencies = resource.get_dependencies()
    assert len(dependencies) == 1
    assert list(dependencies)[0].name == "DependencyResource"
