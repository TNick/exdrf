"""Tests for ``rcv_field_emit`` helpers."""

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
