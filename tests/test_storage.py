import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from osim import storage
from osim.errors import SimulationError, ValidationError

REQ = [98, 183, 37, 122, 14, 124, 65, 67]


class TestDisk(unittest.TestCase):
    def test_known_totals(self):
        exp = {"FCFS": 640, "SSTF": 236, "SCAN": 331, "C-SCAN": 382, "LOOK": 299, "C-LOOK": 322}
        for a, v in exp.items():
            self.assertEqual(storage.run(a, 53, REQ, 200, "up").movement, v, a)

    def test_every_request_serviced(self):
        for a in storage.DISK_ALGOS:
            self.assertTrue(set(REQ) <= set(storage.run(a, 53, REQ).order), a)

    def test_direction_down(self):
        r = storage.run("LOOK", 53, REQ, 200, "down")
        self.assertEqual(r.order[0], 37)

    # boundary
    def test_head_on_request_costs_nothing(self):
        self.assertEqual(storage.run("FCFS", 10, [10], 50).movement, 0)

    def test_head_at_edges(self):
        self.assertEqual(storage.run("SCAN", 0, [5, 10], 20, "up").movement, 10)
        self.assertEqual(storage.run("SSTF", 19, [0, 19], 20).movement, 19)

    def test_minimum_disk(self):
        # 2 cylinders: 0 -> 1 (request & last) -> jump to 0  => 1 + 1
        self.assertEqual(storage.run("C-SCAN", 0, [1], 2).movement, 2)

    # invalid
    def test_invalid_inputs(self):
        with self.assertRaises(ValidationError):
            storage.run("FCFS", 200, REQ, 200)          # head out of range
        with self.assertRaises(ValidationError):
            storage.run("FCFS", 5, [999], 200)          # request out of range
        with self.assertRaises(ValidationError):
            storage.run("FCFS", 5, [], 200)
        with self.assertRaises(ValidationError):
            storage.run("FCFS", 5, [1], 200, "sideways")
        with self.assertRaises(SimulationError):
            storage.run("ELEVATOR9000", 5, [1], 200)


if __name__ == "__main__":
    unittest.main()
