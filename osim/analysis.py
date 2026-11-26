"""Orchestrates all modules over the common datasets, writes traces / CSV /
charts / summary report. Used by the menu (option 6) and by `--demo`."""
import os
from typing import Dict

from . import bashbridge, deadlock, memory, reporting, scheduler, storage
from .errors import BashToolError
from .logger import get_logger
from .validators import (load_alloc_ops, load_json, load_processes, load_reference_string,
                         validate_disk)

log = get_logger("analysis")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "outputs")

WORKLOADS = ["workload_textbook", "workload_mixed", "workload_convoy"]
PAGE_SETS = ["pages_textbook", "pages_belady", "pages_locality"]
DISK_SETS = ["disk_textbook", "disk_heavy"]


def detect_belady(refs, algo="FIFO", max_frames=8):
    faults = [memory.simulate_pages(refs, f, algo).faults for f in range(1, max_frames + 1)]
    return any(b > a for a, b in zip(faults, faults[1:])), faults


def run_scheduling(quantum=4, out=OUT) -> dict:
    by_ds, text, csv_rows, obs = {}, [], [], []
    for ds in WORKLOADS:
        procs = load_processes(os.path.join(DATA, ds + ".csv"))
        results = scheduler.compare_all(procs, quantum)
        by_ds[ds] = results
        text.append(f"##### Dataset: {ds} ({len(procs)} processes) #####")
        for r in results.values():
            text.append(reporting.render_schedule(r))
            s = r.summary
            csv_rows.append([ds, s["algorithm"], s["avg_waiting"], s["avg_turnaround"], s["avg_response"],
                             s["cpu_utilization"], s["throughput"], s["context_switches"]])
        best = min(results.values(), key=lambda r: r.summary["avg_waiting"])
        quick = min(results.values(), key=lambda r: r.summary["avg_response"])
        obs.append(f"{ds}: lowest average waiting = {best.algorithm} ({best.summary['avg_waiting']}); "
                   f"best response = {quick.algorithm} ({quick.summary['avg_response']}); "
                   f"FCFS waiting = {results['FCFS'].summary['avg_waiting']}.")
    reporting.write_text(os.path.join(out, "traces", "scheduling_trace.txt"), "\n\n".join(text))
    reporting.write_csv(os.path.join(out, "results_scheduling.csv"),
                        ["dataset", "algorithm", "avg_waiting", "avg_turnaround", "avg_response",
                         "cpu_util_pct", "throughput", "context_switches"], csv_rows)
    reporting.chart_scheduling(by_ds, os.path.join(out, "charts", "scheduling_comparison.png"))
    reporting.chart_gantt(by_ds["workload_textbook"], "Gantt charts - textbook workload",
                          os.path.join(out, "charts", "gantt_textbook.png"))
    reporting.chart_gantt(by_ds["workload_mixed"], "Gantt charts - mixed workload (note idle gap)",
                          os.path.join(out, "charts", "gantt_mixed.png"))
    return {"results": by_ds, "observations": obs}


def run_memory(out=OUT) -> dict:
    text, csv_rows, obs = [], [], []
    for ds in PAGE_SETS:
        refs = load_reference_string(os.path.join(DATA, ds + ".txt"))
        nframes = 3
        text.append(f"##### Dataset: {ds} ({len(refs)} references) #####")
        results = {}
        for a in memory.PAGE_ALGOS:
            r = memory.simulate_pages(refs, nframes, a)
            results[a] = r
            text.append(reporting.render_pages(r))
            csv_rows.append([ds, a, nframes, r.faults, r.hits, round(r.hit_ratio, 4)])
        low = min(r.faults for r in results.values())
        best = [a for a, r in results.items() if r.faults == low]
        obs.append(f"{ds} @3 frames: " + ", ".join(f"{a}={r.faults}" for a, r in results.items()) +
                   f"; fewest faults = {' / '.join(best)}.")
        sweep = memory.sweep_frames(refs, 8)
        reporting.chart_page_faults(sweep, f"Page faults vs frames - {ds}",
                                    os.path.join(out, "charts", f"page_faults_{ds}.png"))
    belady_refs = load_reference_string(os.path.join(DATA, "pages_belady.txt"))
    anomaly, faults = detect_belady(belady_refs, "FIFO", 7)
    reporting.chart_belady(faults, os.path.join(out, "charts", "belady_anomaly.png"))
    obs.append(f"Belady's anomaly detected under FIFO = {anomaly}; faults for 1..7 frames = {faults}.")

    ops_total, ops = load_alloc_ops(os.path.join(DATA, "alloc_ops.txt"))
    alloc = {s: memory.run_allocation(ops_total, ops, s) for s in memory.Allocator.STRATEGIES}
    text.append("##### Contiguous allocation (data/alloc_ops.txt) #####")
    for s in alloc.values():
        text.append(reporting.render_allocation(s))
    for k, s in alloc.items():
        csv_rows.append(["alloc_ops", f"{k}-fit", ops_total, len(s["failed"]), s["holes"],
                         s["external_fragmentation_pct"]])
    obs.append("Allocation: " + "; ".join(
        f"{k}-fit failed={len(s['failed'])} frag={s['external_fragmentation_pct']}%" for k, s in alloc.items()))
    reporting.chart_allocation(alloc, os.path.join(out, "charts", "allocation_strategies.png"))
    reporting.write_text(os.path.join(out, "traces", "memory_trace.txt"), "\n\n".join(text))
    reporting.write_csv(os.path.join(out, "results_memory.csv"),
                        ["dataset", "algorithm", "frames_or_total", "faults_or_failed", "hits_or_holes",
                         "hit_ratio_or_frag_pct"], csv_rows)
    return {"alloc": alloc, "belady": (anomaly, faults), "observations": obs}


def run_deadlock(out=OUT) -> dict:
    text, obs = [], []
    data = load_json(os.path.join(DATA, "banker_safe.json"))
    state = deadlock.check_state(data)
    text.append("== Banker's safety check: banker_safe.json ==")
    text.append(reporting.table(["Step", "Process", "Need", "Work before"],
                                [[i + 1, t["process"], t["need"], t["work_before"]]
                                 for i, t in enumerate(state["trace"])]))
    text.append(f"Safe = {state['safe']}   Safe sequence = {' -> '.join(state['sequence'])}")
    text.append("Requests are processed in order; a granted request changes the system state.")
    for rq in data["requests"]:
        res = deadlock.request_resources(data, rq["pid"], rq["request"])
        line = f"P{rq['pid']} requests {rq['request']}: {'GRANTED' if res['granted'] else 'DENIED'} - {res['reason']}"
        if res["granted"]:
            data = dict(data, available=res["new_available"], allocation=res["new_allocation"])
            line += f" (safe sequence: {' -> '.join(res['sequence'])})"
        text.append(line)
        obs.append(line)
    unsafe = deadlock.check_state(load_json(os.path.join(DATA, "banker_unsafe.json")))
    text.append(f"\n== banker_unsafe.json ==\nSafe = {unsafe['safe']}")
    obs.append(f"banker_unsafe.json safe = {unsafe['safe']}")
    for ds in ("deadlock_none", "deadlock_present"):
        d = deadlock.detect_deadlock(load_json(os.path.join(DATA, ds + ".json")))
        msg = (f"Detection {ds}: deadlocked = {d['deadlocked'] or 'none'}; "
               f"completion order = {' -> '.join(d['completion_order']) or 'n/a'}")
        text.append(msg)
        obs.append(msg)
    reporting.write_text(os.path.join(out, "traces", "deadlock_trace.txt"), "\n".join(text))
    return {"state": state, "observations": obs}


def run_storage(out=OUT) -> dict:
    by_ds, text, csv_rows, obs = {}, [], [], []
    for ds in DISK_SETS:
        d = validate_disk(load_json(os.path.join(DATA, ds + ".json")))
        res = storage.compare_all(d["head"], d["requests"], d["cylinders"], d.get("direction", "up"))
        by_ds[ds] = res
        text.append(f"##### Dataset: {ds} (head={d['head']}, cylinders={d['cylinders']}, "
                    f"direction={d.get('direction', 'up')}) #####")
        for r in res.values():
            text.append(reporting.render_disk(r, d["head"]))
            csv_rows.append([ds, r.algorithm, r.movement, r.avg_seek])
        low = min(r.movement for r in res.values())
        best = [a for a, r in res.items() if r.movement == low]
        obs.append(f"{ds}: " + ", ".join(f"{a}={r.movement}" for a, r in res.items()) +
                   f"; lowest movement = {' / '.join(best)}.")
    reporting.write_text(os.path.join(out, "traces", "storage_trace.txt"), "\n\n".join(text))
    reporting.write_csv(os.path.join(out, "results_storage.csv"),
                        ["dataset", "algorithm", "total_movement", "avg_seek"], csv_rows)
    reporting.chart_disk(by_ds, os.path.join(out, "charts", "disk_head_movement.png"))
    return {"results": by_ds, "observations": obs}


def host_context() -> Dict[str, str]:
    try:
        snap = bashbridge.system_snapshot()
    except BashToolError as exc:
        log.warning("System snapshot unavailable: %s", exc)
        snap = {"note": f"unavailable ({exc})"}
    try:
        logs = bashbridge.log_summary()
    except BashToolError as exc:
        logs = {"note": f"unavailable ({exc})"}
    return {"snapshot": snap, "logs": logs}


def run_everything(quantum=4, out=OUT) -> dict:
    log.info("Full analysis started (quantum=%s)", quantum)
    sched, mem = run_scheduling(quantum, out), run_memory(out)
    dead, disk = run_deadlock(out), run_storage(out)
    ctx = host_context()
    lines = ["OS Resource Manager - summary of observations", "=" * 48, "", "[CPU scheduling]"]
    lines += sched["observations"] + ["", "[Memory]"] + mem["observations"]
    lines += ["", "[Deadlock]"] + dead["observations"] + ["", "[Storage]"] + disk["observations"]
    lines += ["", "[Host snapshot collected by Bash (sysinfo.sh)]"]
    lines += [f"{k} = {v}" for k, v in ctx["snapshot"].items()]
    lines += ["", "[Activity-log summary computed by Bash (log_summary.sh)]"]
    lines += [f"{k} = {v}" for k, v in ctx["logs"].items()]
    reporting.write_text(os.path.join(out, "traces", "summary_observations.txt"), "\n".join(lines))
    log.info("Full analysis finished")
    return {"scheduling": sched, "memory": mem, "deadlock": dead, "storage": disk, "context": ctx,
            "summary_text": "\n".join(lines)}
