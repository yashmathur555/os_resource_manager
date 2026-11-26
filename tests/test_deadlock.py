import copy, os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from osim import deadlock
from osim.errors import ValidationError

STATE = {"available": [3, 3, 2],
         "max": [[7, 5, 3], [3, 2, 2], [9, 0, 2], [2, 2, 2], [4, 3, 3]],
         "allocation": [[0, 1, 0], [2, 0, 0], [3, 0, 2], [2, 1, 1], [0, 0, 2]]}


class TestBanker(unittest.TestCase):
    def test_safe_sequence(self):
        r = deadlock.check_state(STATE)
        self.assertTrue(r["safe"])
        self.assertEqual(r["sequence"], ["P1", "P3", "P4", "P0", "P2"])

    def test_request_granted_when_safe(self):
        r = deadlock.request_resources(STATE, 1, [1, 0, 2])
        self.assertTrue(r["granted"])

    def test_request_denied_when_unavailable(self):
        s = copy.deepcopy(STATE)
        s["available"] = [2, 3, 0]
        self.assertFalse(deadlock.request_resources(s, 4, [3, 3, 0])["granted"])

    def test_request_denied_when_unsafe(self):
        s = copy.deepcopy(STATE)
        s["available"], s["allocation"][1] = [2, 3, 0], [3, 0, 2]
        r = deadlock.request_resources(s, 0, [0, 2, 0])
        self.assertFalse(r["granted"])
        self.assertIn("UNSAFE", r["reason"])

    def test_request_exceeding_need_denied(self):
        r = deadlock.request_resources(STATE, 1, [9, 9, 9])
        self.assertFalse(r["granted"])
        self.assertIn("maximum", r["reason"])

    def test_state_not_mutated(self):
        before = copy.deepcopy(STATE)
        deadlock.request_resources(STATE, 1, [1, 0, 2])
        self.assertEqual(before, STATE)

    def test_unsafe_state_detected(self):
        s = {"available": [1, 0], "max": [[3, 2], [2, 3]], "allocation": [[1, 1], [1, 2]]}
        self.assertFalse(deadlock.check_state(s)["safe"])

    # invalid / boundary
    def test_bad_process_and_vector(self):
        with self.assertRaises(ValidationError):
            deadlock.request_resources(STATE, 99, [0, 0, 0])
        with self.assertRaises(ValidationError):
            deadlock.request_resources(STATE, 1, [1, 0])
        with self.assertRaises(ValidationError):
            deadlock.request_resources(STATE, 1, [-1, 0, 0])

    def test_allocation_above_max_rejected(self):
        bad = {"available": [1], "max": [[2]], "allocation": [[3]]}
        with self.assertRaises(ValidationError):
            deadlock.check_state(bad)

    def test_ragged_matrix_rejected(self):
        with self.assertRaises(ValidationError):
            deadlock.check_state({"available": [1, 1], "max": [[1, 1], [1]], "allocation": [[0, 0], [0]]})

    def test_zero_request_is_granted(self):
        self.assertTrue(deadlock.request_resources(STATE, 0, [0, 0, 0])["granted"])


class TestDetection(unittest.TestCase):
    BASE = {"available": [0, 0, 0],
            "allocation": [[0, 1, 0], [2, 0, 0], [3, 0, 3], [2, 1, 1], [0, 0, 2]],
            "request": [[0, 0, 0], [2, 0, 2], [0, 0, 0], [1, 0, 0], [0, 0, 2]]}

    def test_no_deadlock(self):
        self.assertFalse(deadlock.detect_deadlock(self.BASE)["has_deadlock"])

    def test_deadlock_found(self):
        d = copy.deepcopy(self.BASE)
        d["request"][2] = [0, 0, 1]
        r = deadlock.detect_deadlock(d)
        self.assertEqual(r["deadlocked"], ["P1", "P2", "P3", "P4"])

    def test_missing_key(self):
        with self.assertRaises(ValidationError):
            deadlock.detect_deadlock({"available": [0]})


if __name__ == "__main__":
    unittest.main()
