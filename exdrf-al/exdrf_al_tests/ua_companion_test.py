"""Tests for :mod:`exdrf_al.ua_companion`."""

from __future__ import annotations

from exdrf_al.ua_companion import apply_ua_companion_fields


def test_apply_skips_missing_keys() -> None:
    """Absent source keys leave the payload unchanged for that pair."""

    payload: dict[str, object] = {"other": 1}
    apply_ua_companion_fields(payload, (("name", "ua_name"),))
    assert payload == {"other": 1}


def test_apply_sets_none_when_source_is_none() -> None:
    """Explicit ``None`` in the payload clears the companion column."""

    payload: dict[str, object] = {"name": None}
    apply_ua_companion_fields(payload, (("name", "ua_name"),))
    assert payload == {"name": None, "ua_name": None}


def test_apply_unidecodes_string() -> None:
    """Non-``None`` strings are lowercased and passed through ``unidecode``."""

    payload: dict[str, object] = {"name": "Ștefan"}
    apply_ua_companion_fields(payload, (("name", "ua_name"),))
    assert payload["ua_name"] == "stefan"


def test_apply_multiple_pairs() -> None:
    """Several pairs are applied in order."""

    payload: dict[str, object] = {"a": "X", "b": "Y"}
    apply_ua_companion_fields(
        payload,
        (("a", "ua_a"), ("b", "ua_b")),
    )
    assert payload["ua_a"] == "x"
    assert payload["ua_b"] == "y"
