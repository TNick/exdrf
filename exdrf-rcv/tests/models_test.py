"""Tests for ``RcvPlan`` and discriminated ``RcvField`` models."""

from datetime import date, datetime

from exdrf.constants import (
    FIELD_TYPE_BLOB,
    FIELD_TYPE_BOOL,
    FIELD_TYPE_DATE,
    FIELD_TYPE_DT,
    FIELD_TYPE_DURATION,
    FIELD_TYPE_ENUM,
    FIELD_TYPE_FILTER,
    FIELD_TYPE_FLOAT,
    FIELD_TYPE_FLOAT_LIST,
    FIELD_TYPE_FORMATTED,
    FIELD_TYPE_INT_LIST,
    FIELD_TYPE_INTEGER,
    FIELD_TYPE_REF_MANY_TO_MANY,
    FIELD_TYPE_REF_MANY_TO_ONE,
    FIELD_TYPE_REF_ONE_TO_MANY,
    FIELD_TYPE_REF_ONE_TO_ONE,
    FIELD_TYPE_SORT,
    FIELD_TYPE_STRING,
    FIELD_TYPE_STRING_LIST,
    FIELD_TYPE_TIME,
)

from exdrf_rcv.models import RcvPlan, RcvResourceDataAccess


class TestRCVPlanAcceptsAllFieldKinds:
    """``RcvPlan.fields`` round-trips every ``FIELD_TYPE_*`` variant."""

    def test_round_trip_one_field_per_kind(self) -> None:
        """Building a plan with each ``kind`` validates and preserves kinds."""

        fields: list = [
            {
                "name": "b",
                "kind": FIELD_TYPE_BLOB,
                "data": {"mime_type": "application/pdf"},
            },
            {"name": "bool_f", "kind": FIELD_TYPE_BOOL, "data": {}},
            {
                "name": "d",
                "kind": FIELD_TYPE_DATE,
                "data": {"min": date(2000, 1, 1), "format": "DD-MM-YYYY"},
            },
            {
                "name": "dt",
                "kind": FIELD_TYPE_DT,
                "data": {
                    "min": datetime(2000, 1, 1, 0, 0, 0),
                    "format": "ISO",
                },
            },
            {"name": "dur", "kind": FIELD_TYPE_DURATION, "data": {"min": 0.0}},
            {
                "name": "en",
                "kind": FIELD_TYPE_ENUM,
                "data": {"enum_values": ["a"]},
            },
            {"name": "flt", "kind": FIELD_TYPE_FILTER, "data": {}},
            {"name": "f", "kind": FIELD_TYPE_FLOAT, "data": {"precision": 2}},
            {"name": "fl", "kind": FIELD_TYPE_FLOAT_LIST, "data": {}},
            {
                "name": "fmt",
                "kind": FIELD_TYPE_FORMATTED,
                "data": {"format": "html"},
            },
            {"name": "i", "kind": FIELD_TYPE_INTEGER, "data": {"min": 0}},
            {"name": "il", "kind": FIELD_TYPE_INT_LIST, "data": {}},
            {
                "name": "m2m",
                "kind": FIELD_TYPE_REF_MANY_TO_MANY,
                "data": {"ref": "Tag"},
            },
            {
                "name": "m2o",
                "kind": FIELD_TYPE_REF_MANY_TO_ONE,
                "data": {"ref": "Parent"},
            },
            {
                "name": "o2m",
                "kind": FIELD_TYPE_REF_ONE_TO_MANY,
                "data": {"ref": "Child", "subordinate": True},
            },
            {
                "name": "o2o",
                "kind": FIELD_TYPE_REF_ONE_TO_ONE,
                "data": {"ref": "Profile"},
            },
            {"name": "srt", "kind": FIELD_TYPE_SORT, "data": {}},
            {
                "name": "s",
                "kind": FIELD_TYPE_STRING,
                "data": {"max_length": 10},
            },
            {"name": "sl", "kind": FIELD_TYPE_STRING_LIST, "data": {}},
            {"name": "t", "kind": FIELD_TYPE_TIME, "data": {"format": "HH:mm"}},
        ]
        plan = RcvPlan(
            category="c",
            resource="r",
            record_id=1,
            view_type="v",
            render_type="default",
            fields=fields,
            resource_data_access=RcvResourceDataAccess(
                url_pattern="/classic/c/r/",
                requires_org_id=True,
                requires_town_id=False,
            ),
        )
        dumped = plan.model_dump(mode="json")
        again = RcvPlan.model_validate(dumped)
        kinds = {f.kind for f in again.fields}
        assert kinds == {f["kind"] for f in fields}
        assert again.resource_data_access is not None
        assert again.resource_data_access.url_pattern == "/classic/c/r/"
        assert again.resource_data_access.requires_org_id is True
        assert again.resource_data_access.requires_town_id is False
