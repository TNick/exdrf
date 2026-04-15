"""Tests for ``rcv_field_emit`` helpers."""

import ast

from exdrf_gen_al2rcv.rcv_field_emit import (
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
