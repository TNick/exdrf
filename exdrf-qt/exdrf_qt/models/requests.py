from typing import Dict

from attrs import define, field


@define
class RecordRequest:
    """A class that represents a request for items from the database.

    Attributes:
        start: The starting index of the items to load.
        count: The number of items to load.
        uniq_id: A unique identifier for the request.
    """

    start: int = field(hash=True)
    count: int = field(hash=True)
    uniq_id: int = field(hash=True, init=False)
    pushed: bool = field(default=False, init=False)

    def __hash__(self) -> int:
        return hash((self.start, self.count, self.uniq_id))


class RecordRequestManager:
    """A class that manages requests for items from the database.

    Attributes:
        uniq_gen: A unique identifier generator for requests.
        requests: A list of requests for items from the database.
    """

    uniq_gen: int
    requests: Dict[int, RecordRequest]

    def __init__(self) -> None:
        self.uniq_gen = 0
        self.requests = {}

    def new_request(self, start: int, count: int) -> "RecordRequest":
        """Create a new request for items from the database."""
        return RecordRequest(start, count)

    def add_request(self, req: "RecordRequest") -> None:
        """Add a request to the list of requests.

        Args:
            req: The request to add.
        """
        uniq_id = self.uniq_gen
        self.uniq_gen += 1
        req.uniq_id = uniq_id
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
                        return False
                else:
                    req.count = other.start - req.start
                    assert req.count >= 0, (
                        f"Request count should be positive, but got {req.count}. "
                        f"Request: {req}, Other: {other}."
                    )
            if req.count == 0:
                return False

        # Next, attempt to join this request to another, adjacent request.
        # Because of the above trim, the only time when we can join is when
        # the limits are exactly equal.
        for other in self.requests.values():
            if other.pushed:
                continue
            if other.count > 50:
                # Don't join requests that are too big.
                continue
            if other.start == req.start + req.count:
                # Prepend the request to the other one.
                other.count += req.count
                other.start = req.start
                req.count = 0
                assert other.count > 0, (
                    f"Request count should be positive, but got {other.count}. "
                    f"Request: {req}, Other: {other}."
                )
                return False
            elif req.start == other.start + other.count:
                # Append the request to the other one.
                other.count += req.count
                req.count = 0
                assert other.count > 0, (
                    f"Request count should be positive, but got {other.count}. "
                    f"Request: {req}, Other: {other}."
                )
                return False

        return req.count > 0
