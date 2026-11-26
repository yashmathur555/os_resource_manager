#!/usr/bin/env python3
"""OS Resource Manager Simulator - interactive menu and demo runner.

Usage:
    python3 main.py          interactive menu
    python3 main.py --demo   run every module on the bundled datasets (no input needed)
"""
import argparse
import os
import sys

from osim import (analysis, bashbridge, deadlock, memory, reporting, scheduler, storage)
from osim.errors import OSSimError
from osim.logger import get_logger
from osim.validators import (load_alloc_ops, load_json, load_processes, load_reference_string,
                             parse_int, parse_reference_string, validate_banker, validate_disk,
                             validate_frames, validate_quantum)

log = get_logger("main")
ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")

BANNER = """
============================================================
        OS RESOURCE MANAGER SIMULATOR  (Python + Bash)
============================================================
 1. CPU scheduling         (FCFS / SJF / SRTF / Priority / RR)
 2. Page replacement       (FIFO / LRU / OPT / Clock)
 3. Memory allocation      (first / best / worst fit)
 4. Deadlock handling      (Banker's + detection)
 5. Disk scheduling        (FCFS / SSTF / SCAN / C-SCAN / LOOK / C-LOOK)
 6. Run FULL analysis      (tables, charts, CSV, traces)
 7. Bash tools             (system snapshot / log summary / generate workload)
 0. Exit
"""


def ask(prompt, default=None):
    text = input(f"{prompt}" + (f" [{default}]" if default is not None else "") + ": ").strip()
    return text if text else (default if default is not None else "")


def pick_file(prompt, default_name):
    path = ask(prompt, os.path.join("data", default_name))
    return path if os.path.isabs(path) else os.path.join(ROOT, path)


# ------------------------------------------------------------------ menus
def menu_scheduling():
    procs = load_processes(pick_file("Workload CSV", "workload_textbook.csv"))
    choice = ask("Algorithm (FCFS/SJF/SRTF/PRIORITY/RR/ALL)", "ALL").upper()
    quantum = validate_quantum(ask("Time quantum (for RR)", 4))
    names = scheduler.ALGORITHMS if choice == "ALL" else [choice]
    for n in names:
        print("\n" + reporting.render_schedule(scheduler.run(procs, n, quantum)))


def menu_paging():
    src = ask("Reference string (numbers) or 'file'", "file")
    refs = (load_reference_string(pick_file("Reference file", "pages_textbook.txt"))
            if src.lower() == "file" else parse_reference_string(src))
    frames = validate_frames(ask("Number of frames", 3))
    algo = ask("Algorithm (FIFO/LRU/OPT/CLOCK/ALL)", "ALL").upper()
    for a in (memory.PAGE_ALGOS if algo == "ALL" else [algo]):
        print("\n" + reporting.render_pages(memory.simulate_pages(refs, frames, a)))


def menu_allocation():
    total, ops = load_alloc_ops(pick_file("Allocation ops file", "alloc_ops.txt"))
    strat = ask("Strategy (first/best/worst/all)", "all").lower()
    for s in (memory.Allocator.STRATEGIES if strat == "all" else [strat]):
        print("\n" + reporting.render_allocation(memory.run_allocation(total, ops, s)))


def menu_deadlock():
    mode = ask("1) Banker safety + requests  2) Deadlock detection", "1")
    if mode == "2":
        d = deadlock.detect_deadlock(load_json(pick_file("Detection JSON", "deadlock_present.json")))
        print("Deadlocked processes:", d["deadlocked"] or "none")
        print("Completion order:", " -> ".join(d["completion_order"]) or "n/a")
        return
    data = validate_banker(load_json(pick_file("Banker JSON", "banker_safe.json")))
    st = deadlock.check_state(data)
    print(f"Safe state: {st['safe']}   Sequence: {' -> '.join(st['sequence']) or 'none'}")
    if ask("Make a custom request? (y/n)", "n").lower() == "y":
        pid = parse_int(ask("Process number"), "Process number")
        req = [parse_int(x, "request value", minimum=0) for x in ask("Request vector, e.g. 1 0 2").split()]
        res = deadlock.request_resources(data, pid, req)
        print(("GRANTED: " if res["granted"] else "DENIED: ") + res["reason"])
    else:
        for rq in data.get("requests", []):
            res = deadlock.request_resources(data, rq["pid"], rq["request"])
            print(f"P{rq['pid']} {rq['request']}: {'GRANTED' if res['granted'] else 'DENIED'} - {res['reason']}")


def menu_disk():
    d = validate_disk(load_json(pick_file("Disk JSON", "disk_textbook.json")))
    algo = ask("Algorithm (FCFS/SSTF/SCAN/C-SCAN/LOOK/C-LOOK/ALL)", "ALL").upper()
    for a in (storage.DISK_ALGOS if algo == "ALL" else [algo]):
        r = storage.run(a, d["head"], d["requests"], d["cylinders"], d.get("direction", "up"))
        print("\n" + reporting.render_disk(r, d["head"]))


def menu_full():
    quantum = validate_quantum(ask("Round-robin quantum", 4))
    result = analysis.run_everything(quantum)
    print(result["summary_text"])
    print("\nCharts  -> outputs/charts/\nTraces  -> outputs/traces/\nCSV     -> outputs/results_*.csv")


def menu_bash():
    c = ask("1) System snapshot  2) Log summary  3) Generate workload", "1")
    if c == "1":
        for k, v in bashbridge.system_snapshot().items():
            print(f"{k:20s} {v}")
    elif c == "2":
        for k, v in bashbridge.log_summary().items():
            print(f"{k:20s} {v}")
    elif c == "3":
        n = parse_int(ask("Number of processes", 8), "Number of processes", 1, 500)
        seed = parse_int(ask("Seed", 42), "Seed", 0)
        out = bashbridge.generate_workload(n, seed, os.path.join(DATA, "workload_generated.csv"))
        print("Generated:", out)
        print(reporting.render_schedule(scheduler.run(load_processes(out), "SRTF")))
    else:
        print("Invalid choice.")


ACTIONS = {"1": menu_scheduling, "2": menu_paging, "3": menu_allocation, "4": menu_deadlock,
           "5": menu_disk, "6": menu_full, "7": menu_bash}


def interactive():
    log.info("Interactive session started")
    while True:
        print(BANNER)
        try:
            choice = ask("Select an option").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nInput closed - exiting.")
            break
        if choice == "0":
            print("Goodbye.")
            break
        action = ACTIONS.get(choice)
        if action is None:
            print(f"Invalid option {choice!r}. Please enter 0-7.")
            log.warning("Invalid menu option %r", choice)
            continue
        try:
            action()
            log.info("Menu option %s completed", choice)
        except OSSimError as exc:                  # expected, user-fixable errors
            print(f"\n[ERROR] {exc}")
            log.error("Menu option %s: %s", choice, exc)
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            break
        except Exception as exc:                   # unexpected: log, keep the app alive
            print(f"\n[UNEXPECTED ERROR] {type(exc).__name__}: {exc}")
            log.exception("Unexpected failure in option %s", choice)
    log.info("Interactive session ended")


def main(argv=None):
    ap = argparse.ArgumentParser(description="OS Resource Manager Simulator")
    ap.add_argument("--demo", action="store_true", help="run all modules on bundled datasets")
    ap.add_argument("--quantum", type=int, default=4, help="round-robin quantum for --demo")
    args = ap.parse_args(argv)
    if args.demo:
        try:
            print(analysis.run_everything(validate_quantum(args.quantum))["summary_text"])
            return 0
        except OSSimError as exc:
            print(f"[ERROR] {exc}", file=sys.stderr)
            return 1
    interactive()
    return 0


if __name__ == "__main__":
    sys.exit(main())
