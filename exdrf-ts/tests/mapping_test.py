"""Tests for ``exdrf_ts.mapping``."""

from __future__ import annotations

from exdrf_ts.mapping import model_rel_import, py_type_to_ts


def test_py_type_to_ts_primitives() -> None:
    """Primitive names map to TS keywords."""

    assert py_type_to_ts("str") == "string"
    assert py_type_to_ts("int") == "number"
    assert py_type_to_ts("float") == "number"
    assert py_type_to_ts("bool") == "boolean"


def test_py_type_to_ts_containers_and_optional() -> None:
    """List, optional, and dict string forms map as expected."""

    assert py_type_to_ts("List[str]") == "string[]"
    assert py_type_to_ts("List[int]") == "number[]"
    assert py_type_to_ts("Optional[str]") == "string | undefined"
    assert py_type_to_ts("Optional[List[int]]") == "number[] | undefined"
    assert py_type_to_ts("Dict[str, int]") == "{ [key: string]: number }"
    assert py_type_to_ts("Dict[int, float]") == "{ [key: number]: number }"


def test_py_type_to_ts_runtime_pep604_and_generics() -> None:
    """Runtime ``type`` / union objects map like annotations."""

    assert py_type_to_ts(str | None) == "string | undefined"
    assert py_type_to_ts(list[int]) == "number[]"
    assert py_type_to_ts(dict[str, int]) == "{ [key: string]: number }"


def test_model_rel_import_relative_paths() -> None:
    """Category segments from ``__module__`` yield stable relative paths."""

    def _model_with_category_segments(segments: list[str]) -> type:
        """Build a type whose ``ExModelVisitor.category`` is ``segments``."""

        class M:
            pass

        M.__module__ = "pkg." + ".".join(segments) + ".resource"
        return M

    model = _model_with_category_segments(["Api", "Users", "Profiles"])
    ref = _model_with_category_segments(["Api"])
    assert model_rel_import(model, ref) == "Users/Profiles"

    model = _model_with_category_segments(["Api", "Users"])
    ref = _model_with_category_segments(["Api", "Posts"])
    assert model_rel_import(model, ref) == "../Users"

    model = _model_with_category_segments(["Api", "Users"])
    ref = _model_with_category_segments(["Api", "Users"])
    assert model_rel_import(model, ref) == ""
