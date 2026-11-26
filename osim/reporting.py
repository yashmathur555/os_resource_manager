"""Module 5 - Reporting: text tables, Gantt strips, CSV export and charts."""
import csv
import os
from typing import Dict, List

import matplotlib
matplotlib.use("Agg")                      # headless: never needs a display
import matplotlib.pyplot as plt            # noqa: E402

from .logger import get_logger

log = get_logger("reporting")
PALETTE = ["#2563eb", "#16a34a", "#dc2626", "#d97706", "#7c3aed", "#0891b2"]


# ---------------------------------------------------------------- text output
def table(headers: List[str], rows: List[list], title: str = "") -> str:
    cells = [[str(c) for c in r] for r in rows]
    widths = [max(len(str(h)), *(len(r[i]) for r in cells)) if cells else len(str(h))
              for i, h in enumerate(headers)]
    line = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    fmt = lambda r: "| " + " | ".join(str(c).ljust(w) for c, w in zip(r, widths)) + " |"
    out = ([title] if title else []) + [line, fmt(headers), line] + [fmt(r) for r in cells] + [line]
    return "\n".join(out)


def gantt_text(gantt) -> str:
    top, marks = "|", [(0, str(gantt[0][1]))]
    for pid, s, e in gantt:
        label = pid if pid else "idle"
        width = max(len(label) + 2, len(str(e)) + 1)
        top += label.center(width) + "|"
        marks.append((len(top) - 1, str(e)))
    bottom = [" "] * (len(top) + 6)
    for pos, text in marks:
        for k, ch in enumerate(text):
            bottom[pos + k] = ch
    return top + "\n" + "".join(bottom).rstrip()


def render_schedule(res) -> str:
    rows = [[r["pid"], r["arrival"], r["burst"], r["priority"], r["start"], r["completion"],
             r["waiting"], r["turnaround"], r["response"]] for r in res.rows]
    s = res.summary
    parts = [table(["PID", "Arr", "Burst", "Prio", "Start", "Done", "Wait", "TAT", "Resp"], rows,
                   f"== {res.algorithm} =="),
             "Gantt: " + gantt_text(res.gantt).replace("\n", "\n       "),
             f"Avg waiting={s['avg_waiting']}  Avg turnaround={s['avg_turnaround']}  "
             f"Avg response={s['avg_response']}  CPU util={s['cpu_utilization']}%  "
             f"Throughput={s['throughput']}/unit  Context switches={s['context_switches']}"]
    return "\n".join(parts)


def render_pages(res, show_steps: bool = True) -> str:
    out = [f"== Page replacement: {res.algorithm}, {res.frames} frames =="]
    if show_steps:
        rows = [[s["ref"], " ".join(map(str, s["frames"])) or "-", "FAULT" if s["fault"] else "hit",
                 "" if s["evicted"] is None else s["evicted"]] for s in res.steps]
        out.append(table(["Ref", "Frames", "Result", "Evicted"], rows))
    out.append(f"Faults={res.faults}  Hits={res.hits}  Hit ratio={res.hit_ratio:.2%}")
    return "\n".join(out)


def render_allocation(stats: dict) -> str:
    return (f"== {stats['strategy']}-fit ==\n"
            f"Used={stats['used']}  Free={stats['free']}  Utilization={stats['utilization_pct']}%  "
            f"Holes={stats['holes']}  Largest hole={stats['largest_hole']}  "
            f"External fragmentation={stats['external_fragmentation_pct']}%\n"
            f"Failed allocations: {', '.join(stats['failed']) or 'none'}\n"
            f"Layout (start,size,name): {stats['layout']}\n"
            f"Free holes (start,size): {stats['holes_list']}")


def render_disk(res, head) -> str:
    path = " -> ".join(map(str, [head] + res.order))
    return f"== {res.algorithm} ==\nPath: {path}\nTotal head movement={res.movement}  Avg seek per request={res.avg_seek}"


# ------------------------------------------------------------------- exports
def write_csv(path: str, headers: List[str], rows: List[list]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(headers)
        w.writerows(rows)
    log.info("Wrote %s", path)


def write_text(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text if text.endswith("\n") else text + "\n")
    log.info("Wrote %s", path)


# -------------------------------------------------------------------- charts
def _save(fig, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    log.info("Chart saved %s", path)
    return path


def chart_scheduling(by_dataset: Dict[str, dict], path: str):
    """by_dataset: {dataset: {algo_key: ScheduleResult}} -> grouped bars per dataset."""
    n = len(by_dataset)
    fig, axes = plt.subplots(1, n, figsize=(5.6 * n, 4.4), squeeze=False)
    for ax, (name, results) in zip(axes[0], by_dataset.items()):
        labels = [r.algorithm for r in results.values()]
        x = range(len(labels))
        for k, (metric, label) in enumerate([("avg_waiting", "Waiting"), ("avg_turnaround", "Turnaround"),
                                             ("avg_response", "Response")]):
            ax.bar([i + (k - 1) * 0.27 for i in x], [r.summary[metric] for r in results.values()],
                   0.27, label=label, color=PALETTE[k])
        ax.set_xticks(list(x))
        ax.set_xticklabels(labels, rotation=20, fontsize=8)
        ax.set_title(name, fontsize=10)
        ax.set_ylabel("Time units")
        ax.grid(axis="y", alpha=0.3)
        ax.legend(fontsize=8)
    fig.suptitle("CPU scheduling - average waiting / turnaround / response time", fontweight="bold")
    return _save(fig, path)


def chart_gantt(results: dict, title: str, path: str):
    fig, axes = plt.subplots(len(results), 1, figsize=(10, 1.25 * len(results) + 1), sharex=True)
    axes = axes if len(results) > 1 else [axes]
    pids = sorted({g[0] for r in results.values() for g in r.gantt if g[0]})
    colors = {p: PALETTE[i % len(PALETTE)] for i, p in enumerate(pids)}
    for ax, res in zip(axes, results.values()):
        for pid, s, e in res.gantt:
            ax.broken_barh([(s, e - s)], (0, 1), facecolors="#e5e7eb" if pid is None else colors[pid],
                           edgecolor="white")
            if pid:
                ax.text((s + e) / 2, 0.5, pid, ha="center", va="center", color="white", fontsize=7)
        ax.set_yticks([])
        ax.set_ylabel(res.algorithm, rotation=0, ha="right", va="center", fontsize=8)
    axes[-1].set_xlabel("Time")
    fig.suptitle(title, fontweight="bold")
    return _save(fig, path)


def chart_page_faults(sweep: Dict[str, List[int]], title: str, path: str):
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    for i, (algo, faults) in enumerate(sweep.items()):
        ax.plot(range(1, len(faults) + 1), faults, marker="o", label=algo, color=PALETTE[i])
    ax.set_xlabel("Number of frames")
    ax.set_ylabel("Page faults")
    ax.set_title(title, fontweight="bold", fontsize=10)
    ax.grid(alpha=0.3)
    ax.legend()
    return _save(fig, path)


def chart_belady(faults: List[int], path: str):
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    x = list(range(1, len(faults) + 1))
    ax.plot(x, faults, marker="o", color=PALETTE[2])
    for i in range(1, len(faults)):
        if faults[i] > faults[i - 1]:
            ax.annotate(f"anomaly: {faults[i-1]}->{faults[i]}", (x[i], faults[i]),
                        textcoords="offset points", xytext=(10, 8), fontsize=8, color=PALETTE[2])
    ax.set_xlabel("Number of frames")
    ax.set_ylabel("FIFO page faults")
    ax.set_title("Belady's anomaly under FIFO", fontweight="bold", fontsize=10)
    ax.grid(alpha=0.3)
    return _save(fig, path)


def chart_disk(by_dataset: Dict[str, dict], path: str):
    n = len(by_dataset)
    fig, axes = plt.subplots(1, n, figsize=(5.6 * n, 4.2), squeeze=False)
    for ax, (name, results) in zip(axes[0], by_dataset.items()):
        algos, vals = list(results), [r.movement for r in results.values()]
        bars = ax.bar(algos, vals, color=PALETTE[:len(algos)])
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v, str(v), ha="center", va="bottom", fontsize=8)
        ax.set_title(name, fontsize=10)
        ax.set_ylabel("Total head movement (cylinders)")
        ax.tick_params(axis="x", labelsize=8)
        ax.grid(axis="y", alpha=0.3)
    fig.suptitle("Disk scheduling - total head movement", fontweight="bold")
    return _save(fig, path)


def chart_allocation(stats: Dict[str, dict], path: str):
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9, 4))
    names = [f"{k}-fit" for k in stats]
    a1.bar(names, [s["external_fragmentation_pct"] for s in stats.values()], color=PALETTE[:3])
    a1.set_title("External fragmentation (%)", fontsize=10)
    a2.bar(names, [len(s["failed"]) for s in stats.values()], color=PALETTE[:3])
    a2.set_title("Failed allocations", fontsize=10)
    a2.set_yticks(range(0, max(max(len(s["failed"]) for s in stats.values()), 1) + 2))
    for a in (a1, a2):
        a.grid(axis="y", alpha=0.3)
    fig.suptitle("Contiguous allocation strategies", fontweight="bold")
    return _save(fig, path)
