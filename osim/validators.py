"""Input loading + validation. All file/user input passes through here so the
rest of the code can assume clean data. Raises ValidationError on bad input."""
import csv
import json
import os
from typing import List

from .errors import ValidationError
from .models import Process

MAX_PROCESSES = 10_000


def _require_file(path: str) -> None:
    if not isinstance(path, str) or not path.strip():
        raise ValidationError("File path must be a non-empty string.")
    if not os.path.isfile(path):
        raise ValidationError(f"File not found: {path}")


def parse_int(value, name: str, minimum=None, maximum=None) -> int:
    try:
        number = int(str(value).strip())
    except (TypeError, ValueError):
        raise ValidationError(f"{name} must be an integer, got {value!r}.")
    if minimum is not None and number < minimum:
        raise ValidationError(f"{name} must be >= {minimum}, got {number}.")
    if maximum is not None and number > maximum:
        raise ValidationError(f"{name} must be <= {maximum}, got {number}.")
    return number


# ---------------------------------------------------------------- scheduling
def validate_processes(procs: List[Process]) -> List[Process]:
    if not procs:
        raise ValidationError("Workload is empty: at least one process is required.")
    if len(procs) > MAX_PROCESSES:
        raise ValidationError(f"Too many processes (max {MAX_PROCESSES}).")
    seen = set()
    for p in procs:
        if p.pid in seen:
            raise ValidationError(f"Duplicate process id {p.pid!r}.")
        seen.add(p.pid)
        if p.arrival < 0:
            raise ValidationError(f"{p.pid}: arrival time cannot be negative.")
        if p.burst < 1:
            raise ValidationError(f"{p.pid}: burst time must be >= 1.")
        if p.priority < 0:
            raise ValidationError(f"{p.pid}: priority cannot be negative.")
    return procs


def load_processes(path: str) -> List[Process]:
    """CSV columns: pid,arrival,burst[,priority]. '#' lines are comments."""
    _require_file(path)
    procs: List[Process] = []
    with open(path, newline="", encoding="utf-8") as fh:
        lines = [ln for ln in fh if ln.strip() and not ln.lstrip().startswith("#")]
    if not lines:
        raise ValidationError(f"{path} contains no data.")
    reader = csv.DictReader(lines)
    needed = {"pid", "arrival", "burst"}
    if reader.fieldnames is None or not needed.issubset({f.strip() for f in reader.fieldnames}):
        raise ValidationError(f"{path}: header must contain {sorted(needed)} (priority optional).")
    for n, row in enumerate(reader, start=2):
        row = {k.strip(): (v or "").strip() for k, v in row.items() if k}
        if not row.get("pid"):
            raise ValidationError(f"{path} row {n}: missing pid.")
        procs.append(Process(
            pid=row["pid"],
            arrival=parse_int(row["arrival"], f"{row['pid']} arrival"),
            burst=parse_int(row["burst"], f"{row['pid']} burst"),
            priority=parse_int(row.get("priority") or 0, f"{row['pid']} priority"),
        ))
    return validate_processes(procs)


def validate_quantum(q) -> int:
    return parse_int(q, "Time quantum", minimum=1, maximum=1000)


# -------------------------------------------------------------------- memory
def parse_reference_string(text: str) -> List[int]:
    tokens = text.replace(",", " ").split()
    if not tokens:
        raise ValidationError("Reference string is empty.")
    return [parse_int(t, "page number", minimum=0, maximum=10**6) for t in tokens]


def load_reference_string(path: str) -> List[int]:
    _require_file(path)
    with open(path, encoding="utf-8") as fh:
        body = " ".join(ln for ln in fh if ln.strip() and not ln.lstrip().startswith("#"))
    return parse_reference_string(body)


def validate_frames(frames) -> int:
    return parse_int(frames, "Number of frames", minimum=1, maximum=1024)


def load_alloc_ops(path: str):
    """Text format:  'memory <size>' then lines 'alloc <name> <size>' / 'free <name>'."""
    _require_file(path)
    total, ops = None, []
    with open(path, encoding="utf-8") as fh:
        for n, line in enumerate(fh, start=1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            cmd = parts[0].lower()
            if cmd == "memory" and len(parts) == 2:
                total = parse_int(parts[1], "memory size", minimum=1)
            elif cmd == "alloc" and len(parts) == 3:
                ops.append(("alloc", parts[1], parse_int(parts[2], f"{parts[1]} size", minimum=1)))
            elif cmd == "free" and len(parts) == 2:
                ops.append(("free", parts[1], 0))
            else:
                raise ValidationError(f"{path} line {n}: cannot parse {line!r}.")
    if total is None:
        raise ValidationError(f"{path}: missing 'memory <size>' line.")
    if not ops:
        raise ValidationError(f"{path}: no alloc/free operations found.")
    return total, ops


# ----------------------------------------------------------------- deadlock
def _check_matrix(name, m, rows=None, cols=None):
    if not isinstance(m, list) or not m or not all(isinstance(r, list) and r for r in m):
        raise ValidationError(f"'{name}' must be a non-empty 2-D list.")
    width = len(m[0])
    for r in m:
        if len(r) != width:
            raise ValidationError(f"'{name}' rows have different lengths.")
        for v in r:
            if not isinstance(v, int) or isinstance(v, bool) or v < 0:
                raise ValidationError(f"'{name}' must contain non-negative integers.")
    if rows is not None and len(m) != rows:
        raise ValidationError(f"'{name}' must have {rows} rows, found {len(m)}.")
    if cols is not None and width != cols:
        raise ValidationError(f"'{name}' must have {cols} columns, found {width}.")


def validate_banker(data: dict) -> dict:
    for key in ("available", "max", "allocation"):
        if key not in data:
            raise ValidationError(f"Banker data missing '{key}'.")
    avail = data["available"]
    if (not isinstance(avail, list) or not avail or
            any((not isinstance(v, int)) or isinstance(v, bool) or v < 0 for v in avail)):
        raise ValidationError("'available' must be a non-empty list of non-negative integers.")
    m = len(avail)
    _check_matrix("max", data["max"], cols=m)
    n = len(data["max"])
    _check_matrix("allocation", data["allocation"], rows=n, cols=m)
    for i in range(n):
        for j in range(m):
            if data["allocation"][i][j] > data["max"][i][j]:
                raise ValidationError(f"P{i}: allocation exceeds declared max for resource {j}.")
    for req in data.get("requests", []):
        if "pid" not in req or "request" not in req:
            raise ValidationError("Each request needs 'pid' and 'request'.")
    return data


def validate_detection(data: dict) -> dict:
    for key in ("available", "allocation", "request"):
        if key not in data:
            raise ValidationError(f"Detection data missing '{key}'.")
    m = len(data["available"])
    _check_matrix("allocation", data["allocation"], cols=m)
    _check_matrix("request", data["request"], rows=len(data["allocation"]), cols=m)
    return data


def load_json(path: str) -> dict:
    _require_file(path)
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"{path} is not valid JSON: {exc}")


def validate_disk(data: dict) -> dict:
    for key in ("cylinders", "head", "requests"):
        if key not in data:
            raise ValidationError(f"Disk data missing '{key}'.")
    cyl = parse_int(data["cylinders"], "cylinders", minimum=2, maximum=10**7)
    parse_int(data["head"], "head position", minimum=0, maximum=cyl - 1)
    reqs = data["requests"]
    if not isinstance(reqs, list) or not reqs:
        raise ValidationError("'requests' must be a non-empty list.")
    for r in reqs:
        parse_int(r, "disk request", minimum=0, maximum=cyl - 1)
    if data.get("direction", "up") not in ("up", "down"):
        raise ValidationError("'direction' must be 'up' or 'down'.")
    return data
