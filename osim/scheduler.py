"""Module 1 - CPU / process scheduling.

Algorithms: FCFS, SJF (non-preemptive), SRTF (preemptive SJF),
Priority (non-preemptive, lower number = higher priority), Round Robin.
"""
from collections import deque
from typing import Callable, Dict, List

from .errors import SimulationError
from .logger import get_logger
from .models import Process, ScheduleResult
from .validators import validate_processes, validate_quantum

log = get_logger("scheduler")

ALGORITHMS = ["FCFS", "SJF", "SRTF", "PRIORITY", "RR"]


def _add(gantt, pid, start, end):
    """Append a Gantt slice, merging with the previous one if contiguous."""
    if end <= start:
        return
    if gantt and gantt[-1][0] == pid and gantt[-1][2] == start:
        gantt[-1] = (pid, gantt[-1][1], end)
    else:
        gantt.append((pid, start, end))


def _non_preemptive(procs: List[Process], key: Callable[[Process], tuple]):
    remaining, t, gantt = list(procs), min(p.arrival for p in procs), []
    while remaining:
        ready = [p for p in remaining if p.arrival <= t]
        if not ready:
            nxt = min(p.arrival for p in remaining)
            _add(gantt, None, t, nxt)
            t = nxt
            continue
        p = min(ready, key=key)
        _add(gantt, p.pid, t, t + p.burst)
        t += p.burst
        remaining.remove(p)
    return gantt


def _srtf(procs: List[Process]):
    rem = {p.pid: p.burst for p in procs}
    t, gantt = min(p.arrival for p in procs), []
    while any(v > 0 for v in rem.values()):
        ready = [p for p in procs if p.arrival <= t and rem[p.pid] > 0]
        if not ready:
            nxt = min(p.arrival for p in procs if rem[p.pid] > 0)
            _add(gantt, None, t, nxt)
            t = nxt
            continue
        p = min(ready, key=lambda x: (rem[x.pid], x.arrival, x.pid))
        future = [q.arrival for q in procs if q.arrival > t and rem[q.pid] > 0]
        run = rem[p.pid] if not future else min(rem[p.pid], min(future) - t)
        _add(gantt, p.pid, t, t + run)
        t += run
        rem[p.pid] -= run
    return gantt


def _round_robin(procs: List[Process], quantum: int):
    order = sorted(procs, key=lambda p: (p.arrival, p.pid))
    rem = {p.pid: p.burst for p in order}
    queue, gantt, i, t = deque(), [], 0, order[0].arrival

    def admit(upto):
        nonlocal i
        while i < len(order) and order[i].arrival <= upto:
            queue.append(order[i].pid)
            i += 1

    admit(t)
    while queue or i < len(order):
        if not queue:
            nxt = order[i].arrival
            _add(gantt, None, t, nxt)
            t = nxt
            admit(t)
            continue
        pid = queue.popleft()
        run = min(quantum, rem[pid])
        _add(gantt, pid, t, t + run)
        t += run
        rem[pid] -= run
        admit(t)                      # arrivals during the slice enter first
        if rem[pid] > 0:
            queue.append(pid)
    return gantt


def _metrics(name: str, procs: List[Process], gantt) -> ScheduleResult:
    first, done = {}, {}
    for pid, s, e in gantt:
        if pid is None:
            continue
        first.setdefault(pid, s)
        done[pid] = e
    rows = []
    for p in sorted(procs, key=lambda x: x.pid):
        if p.pid not in done:
            raise SimulationError(f"Process {p.pid} never completed (internal error).")
        tat = done[p.pid] - p.arrival
        rows.append({"pid": p.pid, "arrival": p.arrival, "burst": p.burst,
                     "priority": p.priority, "start": first[p.pid],
                     "completion": done[p.pid], "turnaround": tat,
                     "waiting": tat - p.burst, "response": first[p.pid] - p.arrival})
    n = len(rows)
    busy = sum(e - s for pid, s, e in gantt if pid is not None)
    span = max(done.values()) - min(p.arrival for p in procs)
    busy_slices = [g[0] for g in gantt if g[0] is not None]
    switches = sum(1 for a, b in zip(busy_slices, busy_slices[1:]) if a != b)
    summary = {
        "algorithm": name,
        "avg_waiting": round(sum(r["waiting"] for r in rows) / n, 2),
        "avg_turnaround": round(sum(r["turnaround"] for r in rows) / n, 2),
        "avg_response": round(sum(r["response"] for r in rows) / n, 2),
        "cpu_utilization": round(100.0 * busy / span, 2) if span else 100.0,
        "throughput": round(n / span, 4) if span else float(n),
        "context_switches": switches,
        "makespan": span,
    }
    return ScheduleResult(name, gantt, rows, summary)


def run(procs: List[Process], algorithm: str, quantum: int = 4) -> ScheduleResult:
    validate_processes(procs)
    algo = algorithm.upper()
    if algo not in ALGORITHMS:
        raise SimulationError(f"Unknown scheduling algorithm {algorithm!r}. Choose from {ALGORITHMS}.")
    if algo == "FCFS":
        g, name = _non_preemptive(procs, lambda p: (p.arrival, p.pid)), "FCFS"
    elif algo == "SJF":
        g, name = _non_preemptive(procs, lambda p: (p.burst, p.arrival, p.pid)), "SJF"
    elif algo == "PRIORITY":
        g, name = _non_preemptive(procs, lambda p: (p.priority, p.arrival, p.pid)), "Priority"
    elif algo == "SRTF":
        g, name = _srtf(procs), "SRTF"
    else:
        q = validate_quantum(quantum)
        g, name = _round_robin(procs, q), f"RR(q={q})"
    result = _metrics(name, procs, g)
    log.info("%s on %d processes: avg_wait=%.2f avg_tat=%.2f util=%.1f%%", name, len(procs),
             result.summary["avg_waiting"], result.summary["avg_turnaround"],
             result.summary["cpu_utilization"])
    return result


def compare_all(procs: List[Process], quantum: int = 4) -> Dict[str, ScheduleResult]:
    return {a: run(procs, a, quantum) for a in ALGORITHMS}
