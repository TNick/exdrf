"""Tests for :mod:`exdrf_ts.json_schema_ts`."""

from __future__ import annotations

from exdrf_ts.json_schema_ts import json_schema_to_ts


class TestJsonSchemaToTsPrimitives:
    """Primitive and array JSON Schema types."""

    def test_string(self) -> None:
        """``type: string`` maps to TypeScript ``string``."""

        assert json_schema_to_ts({"type": "string"}) == "string"

    def test_integer_and_number(self) -> None:
        """Numeric JSON Schema types map to ``number``."""

        assert json_schema_to_ts({"type": "integer"}) == "number"
        assert json_schema_to_ts({"type": "number"}) == "number"

    def test_boolean(self) -> None:
        """``type: boolean`` maps to ``boolean``."""

        assert json_schema_to_ts({"type": "boolean"}) == "boolean"

    def test_array_of_string(self) -> None:
        """``type: array`` with ``items`` maps to element type plus ``[]``."""

        out = json_schema_to_ts(
            {"type": "array", "items": {"type": "string"}},
        )
        assert out == "string[]"

    def test_nullable_string(self) -> None:
        """OpenAPI 3 ``nullable: true`` adds ``| null``."""

        assert (
            json_schema_to_ts({"type": "string", "nullable": True})
            == "string | null"
        )


class TestJsonSchemaToTsRef:
    """``$ref`` resolution against a synthetic OpenAPI document."""

    def test_components_schema_ref(self) -> None:
        """``#/components/schemas/Name`` emits the schema name."""

        root = {
            "components": {
                "schemas": {
                    "Foo": {
                        "type": "object",
                        "properties": {"a": {"type": "integer"}},
                    }
                }
            }
        }
        out = json_schema_to_ts({"$ref": "#/components/schemas/Foo"}, root)
        assert "a" in out
        assert "number" in out


class TestJsonSchemaToTsEnum:
    """Enum keyword."""

    def test_string_enum(self) -> None:
        """String ``enum`` becomes a union of string literals."""

        out = json_schema_to_ts({"type": "string", "enum": ["a", "b"]})
        assert '"a"' in out
        assert '"b"' in out
        assert " | " in out


class TestJsonSchemaToTsLogical:
    """``oneOf`` / ``anyOf`` / ``allOf``."""

    def test_one_of_primitives(self) -> None:
        """``oneOf`` joins alternatives with ``|``."""

        out = json_schema_to_ts(
            {"oneOf": [{"type": "string"}, {"type": "integer"}]},
        )
        assert "string" in out
        assert "number" in out


class TestJsonSchemaToTsSpecial:
    """Boolean schema and empty shapes."""

    def test_true_schema(self) -> None:
        """JSON Schema ``true`` accepts anything → ``unknown``."""

        assert json_schema_to_ts(True) == "unknown"

    def test_false_schema(self) -> None:
        """JSON Schema ``false`` is unsatisfiable → ``never``."""

        assert json_schema_to_ts(False) == "never"
