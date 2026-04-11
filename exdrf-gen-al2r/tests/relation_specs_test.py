"""Tests for :mod:`exdrf_gen_al2r.relation_specs`."""

from __future__ import annotations

from exdrf_gen_al2r.relation_specs import extra_orm_classes_for_relations


def test_extra_orm_classes_sorted_and_deduped() -> None:
    """ORM extras list is sorted and skips the primary resource class name."""

    specs = [
        {"assoc_class": "LinkAB", "payload_name": "a_ids"},
        {"assoc_class": "LinkAB"},
        {"child_class": "ChildRow"},
    ]
    assert extra_orm_classes_for_relations("Main", specs) == [
        "ChildRow",
        "LinkAB",
    ]


def test_extra_orm_classes_empty_when_only_main() -> None:
    """No secondary ORM names yields an empty list."""

    assert extra_orm_classes_for_relations("Main", []) == []
