"""Tests for ``rcv_field_emit`` helpers."""

import ast

from exdrf.field_types.int_field import IntField
from exdrf.label_dsl import parse_expr
from exdrf.resource import ExResource

from exdrf_gen_al2rcv.rcv_field_emit import (
    build_rcv_resource_data_access_dict,
    rcv_field_dicts_py_literal,
    validate_rcv_field_dicts,
)


class TestRcvFieldDictLiteral:
    """``rcv_field_dicts_py_literal`` emits parseable Python."""

    def test_round_trip_repr(self) -> None:
        """Literal eval via validation path."""

        rows = [
            {
                "name": "a",
                "kind": "string",
                "required": False,
                "data": {"max_length": 3},
            },
        ]
        lit = rcv_field_dicts_py_literal(rows)
        assert "max_length" in lit
        validate_rcv_field_dicts(rows)

    def test_long_description_wraps_and_round_trips(self) -> None:
        """Long ``description`` strings split so emitted lines stay bounded."""

        rows = [
            {
                "name": "k",
                "kind": "string",
                "required": True,
                "visible": True,
                "category": "keys",
                "sortable": True,
                "filterable": True,
                "title": "Kind",
                "qsearch": True,
                "resizable": True,
                "exportable": True,
                "read_only": False,
                "nullable": False,
                "primary": True,
                "description": (
                    "The type of the relation. N, E, S and W represent "
                    "neighboring parcels on the north, east, south and west "
                    "side. P and C represents the relations between a parcel "
                    "that was split and its children or between multiple "
                    "parcels that were merged and the resulted parcel."
                ),
                "data": {
                    "enum_values": [("N", "North"), ("S", "South")],
                    "multiline": False,
                },
            },
        ]
        lit = rcv_field_dicts_py_literal(rows)
        assert max(len(line) for line in lit.splitlines()) <= 120
        assert ast.literal_eval(lit) == rows
        validate_rcv_field_dicts(rows)


class TestRcvResourceDataAccessLiteral:
    """``build_rcv_resource_data_access_dict`` matches list URL layout."""

    def test_path_and_org_town_flags(self) -> None:
        """Category segments and plural kebab segment; flags from field names."""

        class _Orm:
            __tablename__ = "vals"

        res = ExResource(
            name="Validated",
            src=_Orm,
            categories=["l18"],
            fields=[
                IntField(name="id", primary=True, nullable=False),
                IntField(name="org_id", primary=False, nullable=True),
                IntField(name="town_id", primary=False, nullable=True),
            ],
            label_ast=parse_expr("id"),
        )
        d = build_rcv_resource_data_access_dict(res)
        assert d["url_pattern"] == "/classic/l18/validateds/"
        assert d["requires_org_id"] is True
        assert d["requires_town_id"] is True
