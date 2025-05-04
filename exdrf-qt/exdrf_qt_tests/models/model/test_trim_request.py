from unittest.mock import MagicMock

import pytest

from exdrf_qt.context import QtContext
from exdrf_qt.models.model import QtModel
from exdrf_qt.models.requests import RecordRequest


@pytest.fixture
def model():
    return QtModel(
        ctx=MagicMock(spec=QtContext),
        db_model=MagicMock(),  # type: ignore
        selection=MagicMock(),  # type: ignore
        fields=[],
        prevent_total_count=True,
    )


class TestTrimRequest:
    def test_outside(self, model):
        """We test that two requests that do not overlap
        and are not adjacent are not modified.
        """
        other = RecordRequest(
            start=0,
            count=10,
        )
        model.requests = {0: other}
        req = RecordRequest(
            start=20,
            count=10,
        )
        assert model.trim_request(req) is True
        assert req.start == 20
        assert req.count == 10
        assert other.start == 0
        assert other.count == 10
        assert other.pushed is False
        assert model.requests == {0: other}

    def test_inside(self, model):
        """We test that two requests where the existing one includes
        the new one result in the old one staying the same and the
        new one being discarded.
        """
        other = RecordRequest(
            start=0,
            count=10,
        )
        model.requests = {0: other}
        req = RecordRequest(
            start=5,
            count=2,
        )
        assert model.trim_request(req) is False
        assert req.start == 5
        assert req.count == 0
        assert other.start == 0
        assert other.count == 10
        assert model.requests == {0: other}

    def test_inside_start_equal(self, model):
        """We test that two requests where the start of the new one
        is equal to the start of the old and the end is inside
        the old one result in the old one staying the same and the
        new one being discarded.
        """
        other = RecordRequest(
            start=0,
            count=10,
        )
        model.requests = {0: other}
        req = RecordRequest(
            start=0,
            count=2,
        )
        assert model.trim_request(req) is False
        assert req.start == 0
        assert req.count == 0
        assert other.start == 0
        assert other.count == 10
        assert model.requests == {0: other}

    def test_inside_end_equal(self, model):
        """We test that two requests where the end of the new one
        is equal to the end of the old and the start is inside
        the old one result in the old one staying the same and the
        new one being discarded.
        """
        other = RecordRequest(
            start=0,
            count=10,
        )
        model.requests = {0: other}
        req = RecordRequest(
            start=8,
            count=2,
        )
        assert model.trim_request(req) is False
        assert req.start == 8
        assert req.count == 0
        assert other.start == 0
        assert other.count == 10
        assert model.requests == {0: other}

    def test_identical(self, model):
        """We test that two requests that are identical result in
        the old one staying the same and the new one being discarded.
        """
        other = RecordRequest(
            start=0,
            count=10,
        )
        model.requests = {0: other}
        req = RecordRequest(
            start=0,
            count=10,
        )
        assert model.trim_request(req) is False
        assert req.start == 0
        assert req.count == 0
        assert other.start == 0
        assert other.count == 10
        assert model.requests == {0: other}

    def test_adjacent_start_pushed(self, model):
        """When the new request includes the start of the old request
        and the old request is pushed, we want the new request to be
        trimmed at the end and the old one to not be modified.
        """
        other = RecordRequest(
            start=5,
            count=5,
        )
        other.pushed = True
        model.requests = {0: other}
        req = RecordRequest(
            start=0,
            count=7,
        )
        assert model.trim_request(req) is True
        assert req.start == 0
        assert req.count == 5
        assert other.start == 5
        assert other.count == 5
        assert model.requests == {0: other}

    def test_adjacent_start_not_pushed(self, model):
        """When the new request includes the start of the old request
        and the old request is not pushed, we want the old request
        to include the new request and the new one to be discarded.
        """
        other = RecordRequest(
            start=5,
            count=5,
        )
        model.requests = {0: other}
        req = RecordRequest(
            start=0,
            count=7,
        )
        assert model.trim_request(req) is False
        assert req.start == 0
        assert req.count == 0
        assert other.start == 0
        assert other.count == 10
        assert model.requests == {0: other}

    def test_adjacent_end_pushed(self, model):
        """When the new request includes the end of the old request
        and the old request is pushed, we want the new request to be
        trimmed at the start and the old one to not be modified.
        """
        other = RecordRequest(
            start=0,
            count=5,
        )
        other.pushed = True
        model.requests = {0: other}
        req = RecordRequest(
            start=3,
            count=4,
        )
        assert model.trim_request(req) is True
        assert req.start == 5
        assert req.count == 2
        assert other.start == 0
        assert other.count == 5
        assert model.requests == {0: other}

    def test_adjacent_end_not_pushed(self, model):
        """When the new request includes the end of the old request
        and the old request is not pushed, we want the old request
        to include the new request and the new one to be discarded.
        """
        other = RecordRequest(
            start=0,
            count=5,
        )
        model.requests = {0: other}
        req = RecordRequest(
            start=3,
            count=7,
        )
        assert model.trim_request(req) is False
        assert req.start == 5, "Because it was trimmed."
        assert req.count == 0
        assert other.start == 0
        assert other.count == 10
        assert model.requests == {0: other}

    def test_new_includes_not_pushed(self, model):
        """When the new request includes the old request and the old
        request is not pushed, we want the old request to be replaced
        by the new one.
        """
        other = RecordRequest(
            start=1,
            count=4,
        )
        model.requests = {0: other}
        req = RecordRequest(
            start=0,
            count=10,
        )
        assert model.trim_request(req) is False
        assert req.start == 0
        assert req.count == 0
        assert other.start == 0
        assert other.count == 10
        assert model.requests == {0: other}

    def test_new_includes_pushed(self, model):
        """When the new request includes the old request and the old
        request is pushed, we want the new request and the old one
        to not be modified.
        """
        other = RecordRequest(
            start=1,
            count=4,
        )
        other.pushed = True
        model.requests = {0: other}
        req = RecordRequest(
            start=0,
            count=10,
        )
        assert model.trim_request(req) is True
        assert req.start == 0
        assert req.count == 10
        assert other.start == 1
        assert other.count == 4
        assert model.requests == {0: other}
