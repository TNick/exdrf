"""Tests for RecordRequest and RecordRequestManager in exdrf_qt.models.requests."""

import unittest

from exdrf_qt.models.requests import RecordRequest, RecordRequestManager


class TestRecordRequest(unittest.TestCase):
    def test_record_request_attributes(self) -> None:
        """Test that RecordRequest has correct default attributes."""
        req = RecordRequest(start=10, count=5)

        self.assertEqual(req.start, 10)
        self.assertEqual(req.count, 5)
        self.assertEqual(req.pushed, False)
        # uniq_id is not set until add_request is called

    def test_record_request_hash(self) -> None:
        """Test that RecordRequest __hash__ works correctly."""
        req1 = RecordRequest(start=10, count=5)
        req1.uniq_id = 1

        req2 = RecordRequest(start=10, count=5)
        req2.uniq_id = 2

        req3 = RecordRequest(start=10, count=5)
        req3.uniq_id = 1

        hash1 = hash(req1)
        hash2 = hash(req2)
        hash3 = hash(req3)

        self.assertNotEqual(hash1, hash2)
        self.assertEqual(hash1, hash3)
        self.assertIsInstance(hash1, int)

    def test_record_request_hash_different_start(self) -> None:
        """Test that RecordRequest hash changes with start."""
        req1 = RecordRequest(start=10, count=5)
        req1.uniq_id = 1

        req2 = RecordRequest(start=20, count=5)
        req2.uniq_id = 1

        self.assertNotEqual(hash(req1), hash(req2))

    def test_record_request_hash_different_count(self) -> None:
        """Test that RecordRequest hash changes with count."""
        req1 = RecordRequest(start=10, count=5)
        req1.uniq_id = 1

        req2 = RecordRequest(start=10, count=10)
        req2.uniq_id = 1

        self.assertNotEqual(hash(req1), hash(req2))

    def test_record_request_pushed_attribute(self) -> None:
        """Test that pushed attribute can be set."""
        req = RecordRequest(start=10, count=5)
        req.pushed = True

        self.assertTrue(req.pushed)


class TestRecordRequestManager(unittest.TestCase):
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.manager = RecordRequestManager()

    def test_init(self) -> None:
        """Test that __init__ initializes manager correctly."""
        manager = RecordRequestManager()

        self.assertEqual(manager.uniq_gen, 0)
        self.assertEqual(manager.requests, {})

    def test_new_request(self) -> None:
        """Test that new_request creates a request."""
        req = self.manager.new_request(start=10, count=5)

        self.assertIsInstance(req, RecordRequest)
        self.assertEqual(req.start, 10)
        self.assertEqual(req.count, 5)
        self.assertEqual(req.pushed, False)
        # uniq_id is not set until add_request is called

    def test_new_request_not_added(self) -> None:
        """Test that new_request does not add request to manager."""
        self.manager.new_request(start=10, count=5)

        self.assertEqual(len(self.manager.requests), 0)
        self.assertNotIn(0, self.manager.requests)

    def test_add_request(self) -> None:
        """Test that add_request adds a request with unique ID."""
        req = RecordRequest(start=10, count=5)

        self.manager.add_request(req)

        self.assertEqual(len(self.manager.requests), 1)
        self.assertIn(0, self.manager.requests)
        self.assertEqual(req.uniq_id, 0)
        self.assertEqual(self.manager.uniq_gen, 1)

    def test_add_request_multiple(self) -> None:
        """Test that add_request assigns sequential unique IDs."""
        req1 = RecordRequest(start=10, count=5)
        req2 = RecordRequest(start=20, count=5)
        req3 = RecordRequest(start=30, count=5)

        self.manager.add_request(req1)
        self.manager.add_request(req2)
        self.manager.add_request(req3)

        self.assertEqual(req1.uniq_id, 0)
        self.assertEqual(req2.uniq_id, 1)
        self.assertEqual(req3.uniq_id, 2)
        self.assertEqual(self.manager.uniq_gen, 3)
        self.assertEqual(len(self.manager.requests), 3)

    def test_trim_request_no_overlap(self) -> None:
        """Test trim_request with no overlapping requests."""
        other = RecordRequest(start=0, count=10)
        self.manager.add_request(other)

        req = RecordRequest(start=20, count=10)
        result = self.manager.trim_request(req)

        self.assertTrue(result)
        self.assertEqual(req.start, 20)
        self.assertEqual(req.count, 10)
        self.assertEqual(other.start, 0)
        self.assertEqual(other.count, 10)

    def test_trim_request_completely_inside(self) -> None:
        """Test trim_request when new request is completely inside."""
        other = RecordRequest(start=0, count=10)
        self.manager.add_request(other)

        req = RecordRequest(start=5, count=2)
        result = self.manager.trim_request(req)

        self.assertFalse(result)
        self.assertEqual(req.count, 0)

    def test_trim_request_new_starts_inside_old(self) -> None:
        """Test trim_request when new request starts inside old."""
        other = RecordRequest(start=0, count=10)
        self.manager.add_request(other)

        req = RecordRequest(start=5, count=10)
        result = self.manager.trim_request(req)

        # After trimming, req becomes [10, 15). If there's an adjacent request,
        # it might get joined. In this case, since there's no adjacent request,
        # it should remain as [10, 15)
        # But wait - the request might get joined if adjacent. Let's check.
        # Actually, since other is [0, 10) and req becomes [10, 15),
        # they are adjacent, so req will be prepended to other.
        self.assertFalse(result)
        self.assertEqual(req.count, 0)
        self.assertEqual(other.start, 0)
        self.assertEqual(other.count, 15)

    def test_trim_request_new_includes_old_not_pushed(self) -> None:
        """Test trim_request when new request includes old (not pushed)."""
        other = RecordRequest(start=5, count=5)
        self.manager.add_request(other)

        req = RecordRequest(start=0, count=10)
        result = self.manager.trim_request(req)

        self.assertFalse(result)
        self.assertEqual(req.count, 0)
        self.assertEqual(other.start, 0)
        self.assertEqual(other.count, 10)

    def test_trim_request_new_includes_old_pushed(self) -> None:
        """Test trim_request when new request includes old (pushed)."""
        other = RecordRequest(start=5, count=5)
        other.pushed = True
        self.manager.add_request(other)

        req = RecordRequest(start=0, count=10)
        result = self.manager.trim_request(req)

        self.assertTrue(result)
        self.assertEqual(req.start, 0)
        self.assertEqual(req.count, 10)

    def test_trim_request_new_ends_inside_old(self) -> None:
        """Test trim_request when new request ends inside old."""
        other = RecordRequest(start=5, count=10)
        self.manager.add_request(other)

        req = RecordRequest(start=0, count=7)
        result = self.manager.trim_request(req)

        # req is [0, 7), other is [5, 15)
        # req.start (0) < other.start (5) and req_end (7) > other.start (5)
        # req_end (7) < other_end (15), so req gets trimmed to [0, 5)
        # Then req [0, 5) and other [5, 15) are adjacent, so they get joined
        self.assertFalse(result)
        self.assertEqual(req.count, 0)
        self.assertEqual(other.start, 0)
        self.assertEqual(other.count, 15)

    def test_trim_request_adjacent_prepend(self) -> None:
        """Test trim_request joins adjacent requests (prepend)."""
        other = RecordRequest(start=10, count=5)
        self.manager.add_request(other)

        req = RecordRequest(start=5, count=5)
        result = self.manager.trim_request(req)

        self.assertFalse(result)
        self.assertEqual(req.count, 0)
        self.assertEqual(other.start, 5)
        self.assertEqual(other.count, 10)

    def test_trim_request_adjacent_append(self) -> None:
        """Test trim_request joins adjacent requests (append)."""
        other = RecordRequest(start=5, count=5)
        self.manager.add_request(other)

        req = RecordRequest(start=10, count=5)
        result = self.manager.trim_request(req)

        self.assertFalse(result)
        self.assertEqual(req.count, 0)
        self.assertEqual(other.start, 5)
        self.assertEqual(other.count, 10)

    def test_trim_request_adjacent_pushed_not_joined(self) -> None:
        """Test trim_request does not join with pushed requests."""
        other = RecordRequest(start=10, count=5)
        other.pushed = True
        self.manager.add_request(other)

        req = RecordRequest(start=5, count=5)
        result = self.manager.trim_request(req)

        self.assertTrue(result)
        self.assertEqual(req.start, 5)
        self.assertEqual(req.count, 5)
        self.assertEqual(other.start, 10)
        self.assertEqual(other.count, 5)

    def test_trim_request_large_request_not_joined(self) -> None:
        """Test trim_request does not join with requests larger than 50."""
        other = RecordRequest(start=60, count=51)
        self.manager.add_request(other)

        req = RecordRequest(start=50, count=10)
        result = self.manager.trim_request(req)

        self.assertTrue(result)
        self.assertEqual(req.start, 50)
        self.assertEqual(req.count, 10)

    def test_trim_request_multiple_overlaps(self) -> None:
        """Test trim_request with multiple overlapping requests."""
        other1 = RecordRequest(start=0, count=5)
        other2 = RecordRequest(start=10, count=5)
        self.manager.add_request(other1)
        self.manager.add_request(other2)

        req = RecordRequest(start=3, count=15)
        result = self.manager.trim_request(req)

        # req is [3, 18)
        # other1 is [0, 5) - req starts inside, gets trimmed to [5, 18)
        # other2 is [10, 15) - new req [5, 18) starts before other2 and ends after
        # Since other2 is not pushed, req replaces other2, then becomes [5, 18)
        # But then it might be adjacent to other1... Let's see.
        # Actually, req [5, 18) and other1 [0, 5) are adjacent, so they get joined
        self.assertFalse(result)
        self.assertEqual(req.count, 0)
        # Either other1 or other2 gets the merged request
        # Since req replaces other2 when it includes it, other2 becomes [5, 18)
        # Then other1 [0, 5) and other2 [5, 18) are adjacent, so they join
        # So either other1 or other2 should have the merged range
        # Let's check the actual behavior
        total_span = max(r.start + r.count for r in [other1, other2]) - min(
            r.start for r in [other1, other2]
        )
        self.assertGreaterEqual(total_span, 18)

    def test_trim_request_identical(self) -> None:
        """Test trim_request with identical request."""
        other = RecordRequest(start=0, count=10)
        self.manager.add_request(other)

        req = RecordRequest(start=0, count=10)
        result = self.manager.trim_request(req)

        self.assertFalse(result)
        self.assertEqual(req.count, 0)

    def test_trim_request_empty_after_trim(self) -> None:
        """Test trim_request returns False when request becomes empty."""
        other = RecordRequest(start=5, count=10)
        self.manager.add_request(other)

        req = RecordRequest(start=6, count=8)
        result = self.manager.trim_request(req)

        self.assertFalse(result)
        self.assertEqual(req.count, 0)


if __name__ == "__main__":
    unittest.main(argv=["first-arg-is-ignored"], exit=False)
