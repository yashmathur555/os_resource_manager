import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from osim import scheduler
from osim.errors import SimulationError, ValidationError
from osim.models import Process

TEXTBOOK = [Process("P1", 0, 8), Process("P2", 1, 4), Process("P3", 2, 9), Process("P4", 3, 5)]


class TestScheduler(unittest.TestCase):
    # ---- valid
    def test_known_averages(self):
        expected = {"FCFS": 8.75, "SJF": 7.75, "SRTF": 6.5}
        for algo, wait in expected.items():
            self.assertEqual(scheduler.run(TEXTBOOK, algo).summary["avg_waiting"], wait, algo)

    def test_every_process_completes_and_conserves_cpu_time(self):
        for algo in scheduler.ALGORITHMS:
            res = scheduler.run(TEXTBOOK, algo, 3)
            busy = sum(e - s for p, s, e in res.gantt if p)
            self.assertEqual(busy, sum(p.burst for p in TEXTBOOK), algo)
            for r in res.rows:
                self.assertEqual(r["turnaround"], r["waiting"] + r["burst"])

    def test_priority_picks_lowest_number_first(self):
        procs = [Process("A", 0, 5, 3), Process("B", 0, 5, 1)]
        self.assertEqual(scheduler.run(procs, "PRIORITY").gantt[0][0], "B")

    def test_round_robin_quantum(self):
        res = scheduler.run([Process("A", 0, 5), Process("B", 0, 5)], "RR", 2)
        self.assertEqual([g[0] for g in res.gantt], ["A", "B", "A", "B", "A", "B"])

    # ---- boundary
    def test_single_process(self):
        res = scheduler.run([Process("A", 0, 1)], "SRTF")
        self.assertEqual(res.summary["avg_waiting"], 0)
        self.assertEqual(res.summary["cpu_utilization"], 100.0)

    def test_idle_gap_recorded(self):
        res = scheduler.run([Process("A", 0, 2), Process("B", 10, 2)], "FCFS")
        self.assertIn((None, 2, 10), res.gantt)
        self.assertLess(res.summary["cpu_utilization"], 100)

    def test_quantum_larger_than_bursts_equals_fcfs(self):
        rr = scheduler.run(TEXTBOOK, "RR", 1000).summary["avg_waiting"]
        self.assertEqual(rr, scheduler.run(TEXTBOOK, "FCFS").summary["avg_waiting"])

    def test_all_arrive_late(self):
        res = scheduler.run([Process("A", 50, 3)], "FCFS")
        self.assertEqual(res.rows[0]["response"], 0)

    # ---- invalid
    def test_empty_workload(self):
        with self.assertRaises(ValidationError):
            scheduler.run([], "FCFS")

    def test_zero_burst_and_negative_arrival(self):
        with self.assertRaises(ValidationError):
            scheduler.run([Process("A", 0, 0)], "FCFS")
        with self.assertRaises(ValidationError):
            scheduler.run([Process("A", -1, 3)], "FCFS")

    def test_duplicate_pid(self):
        with self.assertRaises(ValidationError):
            scheduler.run([Process("A", 0, 3), Process("A", 1, 3)], "FCFS")

    def test_bad_quantum_and_algorithm(self):
        with self.assertRaises(ValidationError):
            scheduler.run(TEXTBOOK, "RR", 0)
        with self.assertRaises(SimulationError):
            scheduler.run(TEXTBOOK, "LOTTERY")


if __name__ == "__main__":
    unittest.main()
