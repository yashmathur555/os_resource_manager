"""Shared data structures (dataclasses) used across modules."""
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass(frozen=True)
class Process:
    pid: str
    arrival: int
    burst: int
    priority: int = 0          # lower number = higher priority


@dataclass
class ScheduleResult:
    algorithm: str
    gantt: List[Tuple[Optional[str], int, int]]   # (pid or None for idle, start, end)
    rows: List[dict]                                # per-process metrics
    summary: dict                                   # aggregate metrics


@dataclass
class PageResult:
    algorithm: str
    frames: int
    faults: int
    hits: int
    steps: List[dict] = field(default_factory=list)

    @property
    def hit_ratio(self) -> float:
        total = self.faults + self.hits
        return self.hits / total if total else 0.0


@dataclass
class DiskResult:
    algorithm: str
    order: List[int]
    movement: int
    avg_seek: float
