"""Module 2 - Memory management.

Part A: page replacement (FIFO, LRU, Optimal, Clock/second-chance).
Part B: contiguous allocation (first / best / worst fit) with fragmentation stats.
"""
from typing import Dict, List

from .errors import SimulationError, ValidationError
from .logger import get_logger
from .models import PageResult
from .validators import validate_frames

log = get_logger("memory")
PAGE_ALGOS = ["FIFO", "LRU", "OPT", "CLOCK"]


# ------------------------------------------------------------- page replacement
def _victim_opt(frames, refs, pos):
    best, far = None, -1
    for page in frames:
        try:
            nxt = refs.index(page, pos + 1)
        except ValueError:
            return page                 # never used again -> ideal victim
        if nxt > far:
            best, far = page, nxt
    return best


def simulate_pages(refs: List[int], nframes: int, algorithm: str) -> PageResult:
    nframes = validate_frames(nframes)
    if not refs:
        raise ValidationError("Reference string is empty.")
    algo = algorithm.upper()
    if algo not in PAGE_ALGOS:
        raise SimulationError(f"Unknown page-replacement algorithm {algorithm!r}.")

    frames: List[int] = []
    last_used: Dict[int, int] = {}
    ref_bit: Dict[int, int] = {}
    hand = 0
    faults = hits = 0
    steps = []

    for pos, page in enumerate(refs):
        evicted = None
        if page in frames:
            hits += 1
            fault = False
            last_used[page] = pos
            ref_bit[page] = 1
        else:
            fault = True
            faults += 1
            if len(frames) < nframes:
                frames.append(page)
                ref_bit[page] = 1
            else:
                if algo == "FIFO":
                    idx = 0
                elif algo == "LRU":
                    idx = frames.index(min(frames, key=lambda f: last_used[f]))
                elif algo == "OPT":
                    idx = frames.index(_victim_opt(frames, refs, pos))
                else:  # CLOCK
                    while ref_bit[frames[hand]]:
                        ref_bit[frames[hand]] = 0
                        hand = (hand + 1) % nframes
                    idx = hand
                    hand = (hand + 1) % nframes
                evicted = frames[idx]
                ref_bit.pop(evicted, None)
                if algo == "FIFO":
                    frames.pop(0)
                    frames.append(page)
                else:
                    frames[idx] = page
                ref_bit[page] = 1
            last_used[page] = pos
        steps.append({"ref": page, "frames": list(frames), "fault": fault, "evicted": evicted})
    log.info("Paging %s frames=%d refs=%d faults=%d", algo, nframes, len(refs), faults)
    return PageResult(algo, nframes, faults, hits, steps)


def sweep_frames(refs: List[int], max_frames: int) -> Dict[str, List[int]]:
    """Fault counts for 1..max_frames frames for every algorithm (for charts)."""
    return {a: [simulate_pages(refs, f, a).faults for f in range(1, max_frames + 1)]
            for a in PAGE_ALGOS}


# -------------------------------------------------------- contiguous allocation
class Allocator:
    """Dynamic-partition allocator with hole coalescing."""
    STRATEGIES = ("first", "best", "worst")

    def __init__(self, total: int, strategy: str):
        if strategy not in self.STRATEGIES:
            raise SimulationError(f"Strategy must be one of {self.STRATEGIES}.")
        if total < 1:
            raise ValidationError("Total memory must be positive.")
        self.total, self.strategy = total, strategy
        self.holes: List[List[int]] = [[0, total]]      # [start, size]
        self.allocs: Dict[str, tuple] = {}
        self.failed: List[str] = []

    def alloc(self, name: str, size: int) -> bool:
        if size < 1:
            raise ValidationError(f"{name}: size must be >= 1.")
        if name in self.allocs:
            raise ValidationError(f"{name} already has an allocation.")
        fits = [h for h in self.holes if h[1] >= size]
        if not fits:
            self.failed.append(name)
            log.warning("Allocation of %s (%d) failed under %s-fit", name, size, self.strategy)
            return False
        hole = (fits[0] if self.strategy == "first" else
                min(fits, key=lambda h: h[1]) if self.strategy == "best" else
                max(fits, key=lambda h: h[1]))
        self.allocs[name] = (hole[0], size)
        if hole[1] == size:
            self.holes.remove(hole)
        else:
            hole[0] += size
            hole[1] -= size
        return True

    def free(self, name: str) -> None:
        if name not in self.allocs:
            raise ValidationError(f"Cannot free {name!r}: no such allocation.")
        start, size = self.allocs.pop(name)
        self.holes.append([start, size])
        self.holes.sort()
        merged = [self.holes[0]]
        for s, z in self.holes[1:]:
            if merged[-1][0] + merged[-1][1] == s:
                merged[-1][1] += z
            else:
                merged.append([s, z])
        self.holes = merged

    def stats(self) -> dict:
        free_total = sum(h[1] for h in self.holes)
        largest = max((h[1] for h in self.holes), default=0)
        frag = round(100.0 * (1 - largest / free_total), 2) if free_total else 0.0
        return {"strategy": self.strategy, "used": self.total - free_total,
                "free": free_total, "largest_hole": largest, "holes": len(self.holes),
                "external_fragmentation_pct": frag, "failed": list(self.failed),
                "utilization_pct": round(100.0 * (self.total - free_total) / self.total, 2)}


def run_allocation(total: int, ops, strategy: str) -> dict:
    a = Allocator(total, strategy)
    for op, name, size in ops:
        a.alloc(name, size) if op == "alloc" else a.free(name)
    out = a.stats()
    out["layout"] = sorted((s, z, n) for n, (s, z) in a.allocs.items())
    out["holes_list"] = [tuple(h) for h in a.holes]
    log.info("Allocation %s-fit total=%d failed=%s", strategy, total, out["failed"])
    return out
