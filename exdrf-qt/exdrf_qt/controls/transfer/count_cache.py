"""Shared cache for table row counts across transfer models/workers.

Provides simple, thread-safe storage for per-table counts for a given
pair of connections (source, destination). Also supports a lightweight
in-flight reservation to avoid duplicate counting by concurrent workers.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Dict, Optional, Set, Tuple

if TYPE_CHECKING:
    from exdrf_al.connection import DbConn

ConnKey = str
PairKey = Tuple[ConnKey, ConnKey]


def make_conn_key(conn: Optional["DbConn"]) -> ConnKey:
    if conn is None:
        return "<none>"
    # Include both connection string and schema to distinguish databases
    schema = conn.schema or ""
    return f"{conn.c_string}||{schema}"


def make_pair_key(src: Optional["DbConn"], dst: Optional["DbConn"]) -> PairKey:
    return (make_conn_key(src), make_conn_key(dst))


class CountCache:
    """Thread-safe cache for table counts keyed by connection pair + table."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # (src_key, dst_key, table) ->
        #   {"src": Optional[int], "dst": Optional[int]}
        self._data: Dict[
            Tuple[ConnKey, ConnKey, str],
            Dict[str, Optional[int]],
        ] = {}
        # Tracks tables currently being counted to prevent duplicate work
        self._inflight: Set[Tuple[ConnKey, ConnKey, str]] = set()

    def get_pair(
        self,
        pair: PairKey,
        table: str,
    ) -> Tuple[Optional[int], Optional[int]]:
        with self._lock:
            entry = self._data.get((pair[0], pair[1], table))
            if not entry:
                return (None, None)
            return (entry.get("src"), entry.get("dst"))

    def set_pair(
        self,
        pair: PairKey,
        table: str,
        src_value: Optional[int] = None,
        dst_value: Optional[int] = None,
    ) -> None:
        with self._lock:
            key = (pair[0], pair[1], table)
            entry: Optional[Dict[str, Optional[int]]] = self._data.get(key)
            if entry is None:
                # Create fresh entry
                entry = {
                    "src": None,
                    "dst": None,
                }
                self._data[key] = entry
            if src_value is not None:
                entry["src"] = int(src_value)
            if dst_value is not None:
                entry["dst"] = int(dst_value)

    def reserve(self, pair: PairKey, table: str) -> bool:
        """Reserve counting for a table if not already cached/in-flight.

        Returns True if reservation acquired; False otherwise.
        """
        with self._lock:
            key = (pair[0], pair[1], table)
            # If fully cached, no need to reserve
            entry = self._data.get(key)
            if (
                entry
                and entry.get("src") is not None
                and entry.get("dst") is not None
            ):
                return False
            if key in self._inflight:
                return False
            self._inflight.add(key)
            return True

    def release(self, pair: PairKey, table: str) -> None:
        with self._lock:
            key = (pair[0], pair[1], table)
            self._inflight.discard(key)

    def clear_pair(self, pair: PairKey) -> None:
        """Clear all cached rows and reservations for a connection pair."""
        with self._lock:
            keys_to_del = [
                k
                for k in self._data.keys()
                if k[0] == pair[0] and k[1] == pair[1]
            ]
            for k in keys_to_del:
                del self._data[k]
            inflight_to_del = [
                k for k in self._inflight if k[0] == pair[0] and k[1] == pair[1]
            ]
            for k in inflight_to_del:
                self._inflight.discard(k)


# Global singleton instance
count_cache = CountCache()
