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
    uniq_id: int = field(hash=True)

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
        uniq_id = self.uniq_gen
        self.uniq_gen += 1
        return RecordRequest(start, count, uniq_id)

    def add_request(self, req: "RecordRequest") -> None:
        """Add a request to the list of requests.

        Args:
            req: The request to add.
        """
        self.requests[req.uniq_id] = req

    def trim_request(self, req: "RecordRequest") -> bool:
        """Trim the size of a request based on the requests already in progress.

        Args:
            req: The request to trim.

        Returns:
            False if the request is empty, True otherwise.
        """
        for other in self.requests.values():
            if (
                other.start <= req.start
                and other.start + other.count > req.start
            ):
                req.count = req.start + req.count - other.start - other.count
            elif (
                req.start <= other.start and req.start + req.count > other.start
            ):
                req.count = other.start + other.count - req.start - req.count
            if req.count == 0:
                break
        return req.count > 0
