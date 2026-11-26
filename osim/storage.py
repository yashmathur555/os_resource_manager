"""Module 4 - Storage: disk-head scheduling.

Algorithms: FCFS, SSTF, SCAN, C-SCAN, LOOK, C-LOOK.
Head movement includes the return jump of C-SCAN / C-LOOK (documented choice).
"""
from typing import List

from .errors import SimulationError
from .logger import get_logger
from .models import DiskResult
from .validators import validate_disk

log = get_logger("storage")
DISK_ALGOS = ["FCFS", "SSTF", "SCAN", "C-SCAN", "LOOK", "C-LOOK"]


def _order(algo: str, head: int, reqs: List[int], cylinders: int, direction: str) -> List[int]:
    """Return the sequence of head positions visited (starting after `head`)."""
    last = cylinders - 1
    if algo == "FCFS":
        return list(reqs)
    if algo == "SSTF":
        pending, pos, out = list(reqs), head, []
        while pending:
            nxt = min(pending, key=lambda r: (abs(r - pos), r))
            out.append(nxt)
            pending.remove(nxt)
            pos = nxt
        return out
    lower = sorted(r for r in reqs if r < head)
    upper = sorted(r for r in reqs if r >= head)
    up = direction == "up"
    if algo == "SCAN":
        return (upper + ([last] if lower else []) + lower[::-1]) if up else \
               (lower[::-1] + ([0] if upper else []) + upper)
    if algo == "C-SCAN":
        return (upper + [last, 0] + lower) if up else (lower[::-1] + [0, last] + upper[::-1])
    if algo == "LOOK":
        return (upper + lower[::-1]) if up else (lower[::-1] + upper)
    if algo == "C-LOOK":
        return (upper + lower) if up else (lower[::-1] + upper[::-1])
    raise SimulationError(f"Unknown disk algorithm {algo!r}.")


def run(algorithm: str, head: int, requests: List[int], cylinders: int = 200,
        direction: str = "up") -> DiskResult:
    validate_disk({"cylinders": cylinders, "head": head, "requests": requests, "direction": direction})
    algo = algorithm.upper()
    if algo not in DISK_ALGOS:
        raise SimulationError(f"Unknown disk algorithm {algorithm!r}. Choose from {DISK_ALGOS}.")
    order = _order(algo, head, requests, cylinders, direction)
    movement, pos = 0, head
    for c in order:
        movement += abs(c - pos)
        pos = c
    avg = round(movement / len(requests), 2)
    log.info("Disk %s head=%d requests=%d movement=%d", algo, head, len(requests), movement)
    return DiskResult(algo, order, movement, avg)


def compare_all(head, requests, cylinders=200, direction="up"):
    return {a: run(a, head, requests, cylinders, direction) for a in DISK_ALGOS}
