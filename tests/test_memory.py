import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from osim import memory
from osim.errors import SimulationError, ValidationError

REFS = [7, 0, 1, 2, 0, 3, 0, 4, 2, 3, 0, 3, 2, 1, 2, 0, 1, 7, 0, 1]
BELADY = [1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5]


class TestPaging(unittest.TestCase):
    def test_known_fault_counts(self):
        got = {a: memory.simulate_pages(REFS, 3, a).faults for a in ("FIFO", "LRU", "OPT")}
        self.assertEqual(got, {"FIFO": 15, "LRU": 12, "OPT": 9})

    def test_optimal_is_never_worse(self):
        for f in range(1, 6):
            opt = memory.simulate_pages(REFS, f, "OPT").faults
            for a in ("FIFO", "LRU", "CLOCK"):
                self.assertLessEqual(opt, memory.simulate_pages(REFS, f, a).faults)

    def test_belady_anomaly(self):
        self.assertEqual(memory.simulate_pages(BELADY, 3, "FIFO").faults, 9)
        self.assertEqual(memory.simulate_pages(BELADY, 4, "FIFO").faults, 10)

    def test_faults_plus_hits_equals_references(self):
        r = memory.simulate_pages(REFS, 3, "LRU")
        self.assertEqual(r.faults + r.hits, len(REFS))

    # boundary
    def test_one_frame_every_change_faults(self):
        self.assertEqual(memory.simulate_pages([1, 1, 2, 2, 1], 1, "FIFO").faults, 3)

    def test_frames_ge_distinct_pages_only_cold_faults(self):
        self.assertEqual(memory.simulate_pages(REFS, 8, "LRU").faults, len(set(REFS)))

    def test_single_reference(self):
        self.assertEqual(memory.simulate_pages([5], 2, "OPT").faults, 1)

    # invalid
    def test_invalid_inputs(self):
        with self.assertRaises(ValidationError):
            memory.simulate_pages(REFS, 0, "FIFO")
        with self.assertRaises(ValidationError):
            memory.simulate_pages([], 3, "FIFO")
        with self.assertRaises(SimulationError):
            memory.simulate_pages(REFS, 3, "RANDOM")


class TestAllocation(unittest.TestCase):
    OPS = [("alloc", "A", 300), ("alloc", "B", 200), ("alloc", "C", 100), ("free", "B", 0)]

    def test_first_best_worst_differ(self):
        first = memory.Allocator(1000, "first")
        best = memory.Allocator(1000, "best")
        for a in (first, best):
            for op, n, s in self.OPS:
                a.alloc(n, s) if op == "alloc" else a.free(n)
            a.alloc("D", 150)
        self.assertEqual(first.allocs["D"][0], 300)     # first hole (freed B)
        self.assertEqual(best.allocs["D"][0], 300)      # 200-hole is tightest fit

    def test_coalescing(self):
        a = memory.Allocator(100, "first")
        a.alloc("A", 40); a.alloc("B", 40)
        a.free("A"); a.free("B")
        self.assertEqual(a.holes, [[0, 100]])

    def test_allocation_failure_logged(self):
        a = memory.Allocator(100, "first")
        self.assertFalse(a.alloc("BIG", 101))
        self.assertEqual(a.failed, ["BIG"])

    def test_exact_fit_removes_hole(self):
        a = memory.Allocator(100, "best")
        self.assertTrue(a.alloc("A", 100))
        self.assertEqual(a.holes, [])
        self.assertEqual(a.stats()["utilization_pct"], 100.0)

    def test_invalid(self):
        a = memory.Allocator(100, "first")
        with self.assertRaises(ValidationError):
            a.free("ghost")
        with self.assertRaises(ValidationError):
            a.alloc("Z", 0)
        a.alloc("A", 10)
        with self.assertRaises(ValidationError):
            a.alloc("A", 10)
        with self.assertRaises(SimulationError):
            memory.Allocator(100, "random")


if __name__ == "__main__":
    unittest.main()
