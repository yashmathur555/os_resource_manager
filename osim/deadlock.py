"""Module 3 - Deadlock handling: Banker's algorithm (avoidance) and the
detection algorithm for multiple-instance resources."""
from typing import List

from .errors import ValidationError
from .logger import get_logger
from .validators import validate_banker, validate_detection

log = get_logger("deadlock")


def _need(maxm, alloc):
    return [[maxm[i][j] - alloc[i][j] for j in range(len(maxm[0]))] for i in range(len(maxm))]


def is_safe(available: List[int], maxm, alloc):
    """Return (safe, safe_sequence, trace). Trace lists each pick with the work vector."""
    need = _need(maxm, alloc)
    n, m = len(maxm), len(available)
    work, finish, seq, trace = list(available), [False] * n, [], []
    progress = True
    while progress:
        progress = False
        for i in range(n):
            if not finish[i] and all(need[i][j] <= work[j] for j in range(m)):
                trace.append({"process": f"P{i}", "need": list(need[i]), "work_before": list(work)})
                for j in range(m):
                    work[j] += alloc[i][j]
                finish[i] = True
                seq.append(f"P{i}")
                progress = True
    return all(finish), seq, trace


def check_state(data: dict) -> dict:
    validate_banker(data)
    safe, seq, trace = is_safe(data["available"], data["max"], data["allocation"])
    log.info("Banker safety check: safe=%s sequence=%s", safe, seq)
    return {"safe": safe, "sequence": seq, "trace": trace,
            "need": _need(data["max"], data["allocation"])}


def request_resources(data: dict, pid: int, request: List[int]) -> dict:
    """Banker's resource-request algorithm. Does not mutate `data`."""
    validate_banker(data)
    n, m = len(data["max"]), len(data["available"])
    if not isinstance(pid, int) or not 0 <= pid < n:
        raise ValidationError(f"Process id must be between 0 and {n - 1}.")
    if len(request) != m or any((not isinstance(v, int)) or v < 0 for v in request):
        raise ValidationError(f"Request must be {m} non-negative integers.")
    need = _need(data["max"], data["allocation"])[pid]
    if any(request[j] > need[j] for j in range(m)):
        log.error("P%d request %s exceeds declared need %s", pid, request, need)
        return {"granted": False, "reason": "Request exceeds the process's maximum claim."}
    if any(request[j] > data["available"][j] for j in range(m)):
        log.warning("P%d request %s must wait: not enough available", pid, request)
        return {"granted": False, "reason": "Resources not available - process must wait."}
    avail = [data["available"][j] - request[j] for j in range(m)]
    alloc = [row[:] for row in data["allocation"]]
    alloc[pid] = [alloc[pid][j] + request[j] for j in range(m)]
    safe, seq, _ = is_safe(avail, data["max"], alloc)
    if not safe:
        log.warning("P%d request %s denied: would leave system unsafe", pid, request)
        return {"granted": False, "reason": "Granting would leave the system in an UNSAFE state."}
    log.info("P%d request %s granted; safe sequence %s", pid, request, seq)
    return {"granted": True, "reason": "Safe - request granted.", "sequence": seq,
            "new_available": avail, "new_allocation": alloc}


def detect_deadlock(data: dict) -> dict:
    """Deadlock detection (multiple instances). Returns deadlocked process list."""
    validate_detection(data)
    alloc, req, work = data["allocation"], data["request"], list(data["available"])
    n, m = len(alloc), len(work)
    finish = [all(v == 0 for v in alloc[i]) for i in range(n)]   # holds nothing -> can't be in a cycle
    order, progress = [], True
    while progress:
        progress = False
        for i in range(n):
            if not finish[i] and all(req[i][j] <= work[j] for j in range(m)):
                for j in range(m):
                    work[j] += alloc[i][j]
                finish[i] = True
                order.append(f"P{i}")
                progress = True
    dead = [f"P{i}" for i in range(n) if not finish[i]]
    log.info("Deadlock detection: deadlocked=%s", dead)
    return {"deadlocked": dead, "has_deadlock": bool(dead), "completion_order": order}
