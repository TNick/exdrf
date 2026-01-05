from typing import TYPE_CHECKING, Dict, Optional

from attrs import define, field

if TYPE_CHECKING:
    from exdrf_qt.models.model import ModelWork

MERGE_LIMIT = 50


@define(slots=True)
class RecordRequest:
    """A class that represents a request for items from the database.

    Attributes:
        start: The starting index of the items to load.
        count: The number of items to load.
        uniq_id: A unique identifier for the request.
        pushed: Whether this request has been pushed to the database.
    """

    start: int = field(hash=True)
    count: int = field(hash=True)
    uniq_id: int = field(hash=True, init=False)
    pushed: bool = field(default=False, init=False, hash=False)
    work: Optional["ModelWork"] = field(
        default=None, init=False, repr=False, hash=False
    )
    _cancelled: bool = field(default=False, init=False, hash=False)
    priority: int = field(default=0, init=False, hash=False)

    def __hash__(self) -> int:
        """Return the hash of the request.

        Returns:
            A hash value based on start, count, and uniq_id.
        """
        return hash((self.start, self.count, self.uniq_id))

    @property
    def cancelled(self) -> bool:
        """Return whether the request has been cancelled."""
        if self._cancelled:
            return True
        return self.work is not None and self.work.cancelled

    @cancelled.setter
    def cancelled(self, value: bool) -> None:
        """Set whether the request has been cancelled."""
        if self.work is not None:
            self.work.cancelled = value
        self._cancelled = value


class RecordRequestManager:
    """A class that manages requests for items from the database.

    Attributes:
        uniq_gen: A unique identifier generator for requests.
        requests: A dictionary mapping unique IDs to requests.
    """

    uniq_gen: int
    requests: Dict[int, RecordRequest]

    def __init__(self) -> None:
        """Initialize the request manager with empty state."""
        self.uniq_gen = 0
        self.requests = {}

    def new_request(self, start: int, count: int) -> "RecordRequest":
        """Create a new request for items from the database.

        Args:
            start: The starting index of the items to load.
            count: The number of items to load.

        Returns:
            A new RecordRequest instance (not yet added to the manager).
        """
        return RecordRequest(start, count)

    def add_request(self, req: "RecordRequest") -> None:
        """Add a request to the list of requests.

        Args:
            req: The request to add.
        """
        uniq_id = self.uniq_gen
        self.uniq_gen += 1
        req.uniq_id = uniq_id
        req.priority = uniq_id
        self.requests[uniq_id] = req

    def trim_request(self, req: "RecordRequest") -> bool:
        """Trim the size of a request based on the requests already in progress.

        Args:
            req: The request to trim.

        Returns:
            False if the request is empty, True otherwise.
        """
        req_end = req.start + req.count
        # First eliminate intervals from this request that are already
        # part of other requests (even if those are already pushed).
        for other in self.requests.values():
            other_end = other.start + other.count
            if other.start <= req.start and other_end > req.start:
                # OTHER:   |------------------|
                # NEW:          |------------------|
                # NEW:          |----------|

                # The start is inside older request.
                if other_end >= req_end:
                    # The new request is completely inside the old one.
                    req.count = 0
                    other.priority = max(other.priority, req.priority)
                    return False

                req.count = req_end - other_end
                req.start = other_end
                assert req.count >= 0, (
                    f"Request count should be positive, but got {req.count}. "
                    f"Request: {req}, Other: {other}."
                )
            elif req.start <= other.start and req_end > other.start:
                # OTHER:    |------------------|
                # NEW:   |------------------|
                # NEW:   |---------------------------|
                # The start of the new request is inside the old one.
                if req_end >= other_end:
                    # The old request is completely inside the new one.
                    if not other.pushed:
                        # Replace the old request with the new one.
                        other.start = req.start
                        other.count = req.count
                        req.count = 0
                        other.priority = max(other.priority, req.priority)
                        return False
                    else:
                        other.priority = max(other.priority, req.priority)
                else:
                    req.count = other.start - req.start
                    other.priority = max(other.priority, req.priority)
                    req.priority = other.priority
                    assert req.count >= 0, (
                        "Request count should be positive, but got "
                        f"{req.count}. Request: {req}, Other: {other}."
                    )
            if req.count == 0:
                return False

        # Next, attempt to join this request to another, adjacent request.
        # Because of the above trim, the only time when we can join is when
        # the limits are exactly equal.
        for other in self.requests.values():
            if other.pushed:
                other.priority = max(other.priority, req.priority)
                continue
            if other.count > MERGE_LIMIT:
                # Don't join requests that are too big.
                continue
            if other.start == req.start + req.count:
                # Prepend the request to the other one.
                other.count += req.count
                other.start = req.start
                req.count = 0
                other.priority = max(other.priority, req.priority)
                assert other.count > 0, (
                    f"Request count should be positive, but got {other.count}. "
                    f"Request: {req}, Other: {other}."
                )
                return False
            elif req.start == other.start + other.count:
                # Append the request to the other one.
                other.count += req.count
                req.count = 0
                other.priority = max(other.priority, req.priority)
                assert other.count > 0, (
                    f"Request count should be positive, but got {other.count}. "
                    f"Request: {req}, Other: {other}."
                )
                return False

        return req.count > 0
