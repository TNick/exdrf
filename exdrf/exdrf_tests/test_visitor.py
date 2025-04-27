from unittest.mock import MagicMock

from exdrf.visitor import ExVisitor


class TestExVisitor:
    def test_visit_dataset(self):
        visitor = ExVisitor()
        mock_dataset = MagicMock()
        result = visitor.visit_dataset(mock_dataset)
        assert result is True

    def test_visit_category(self):
        visitor = ExVisitor()
        name = "category_name"
        level = 1
        content = {"sub_category": {}, "resource": {}}
        result = visitor.visit_category(name, level, content)
        assert result is True

    def test_visit_resource(self):
        visitor = ExVisitor()
        mock_resource = MagicMock()
        result = visitor.visit_resource(mock_resource)
        assert result is True

    def test_visit_field(self):
        visitor = ExVisitor()
        mock_field = MagicMock()
        result = visitor.visit_field(mock_field)
        assert result is True
