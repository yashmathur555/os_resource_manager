# OS Resource Manager Simulator (Python + Bash)

One integrated application that simulates the major resource-management functions of an
operating system and compares the algorithms with tables, charts and logs.

| Module | File | What it simulates |
|---|---|---|
| Process scheduling | `osim/scheduler.py` | FCFS, SJF, SRTF, Priority, Round Robin |
| Memory management | `osim/memory.py` | Page replacement (FIFO, LRU, OPT, Clock) and contiguous allocation (first/best/worst fit) |
| Deadlock handling | `osim/deadlock.py` | Banker's algorithm (safety + requests) and deadlock detection |
| Storage | `osim/storage.py` | Disk scheduling (FCFS, SSTF, SCAN, C-SCAN, LOOK, C-LOOK) |
| Reporting | `osim/reporting.py`, `osim/analysis.py` | Tables, Gantt strips, CSV, 9 charts, summary |
| Bash integration | `scripts/*.sh`, `osim/bashbridge.py` | host snapshot, log analysis, workload generator, test runner |

All modules share one input layer (`validators.py`), one logger (`logs/activity.log`) and one
error hierarchy (`errors.py`), and are driven from a single menu (`main.py`).

## Requirements
Python 3.9+, Bash, `matplotlib` (`pip install matplotlib`). Pillow is only needed for
`scripts/make_screenshots.py`. Works on Linux/macOS; on Windows use WSL or Git Bash.

## Execution steps
```bash
cd os_resource_manager
pip install matplotlib
./run.sh menu     # interactive menu (default)
./run.sh demo     # run everything on the bundled datasets, no input needed
./run.sh tests    # 63 unit tests -> outputs/traces/test_results.txt
./run.sh clean    # delete generated logs/outputs
```
Menu: `1` CPU scheduling, `2` page replacement, `3` memory allocation, `4` deadlock,
`5` disk scheduling, `6` full analysis (writes charts/CSV/traces), `7` Bash tools, `0` exit.
Every prompt shows a default in `[brackets]`; press Enter to accept it.

## Sample input (`data/`)
| File | Format | Used by |
|---|---|---|
| `workload_*.csv` | `pid,arrival,burst,priority` | scheduling |
| `pages_*.txt` | space/comma separated page numbers | paging |
| `alloc_ops.txt` | `memory N`, `alloc NAME SIZE`, `free NAME` | allocation |
| `banker_*.json`, `deadlock_*.json` | available / max / allocation / request matrices | deadlock |
| `disk_*.json` | cylinders, head, direction, requests | disk |
Lines starting with `#` are comments. Generate a random workload with
`bash scripts/generate_workload.sh 10 42 data/workload_generated.csv`.

## Output evidence (`outputs/`)
* `traces/` - `demo_run_output.txt`, per-module traces, `test_results.txt`, `error_handling_session.txt`
* `charts/` - scheduling comparison, Gantt charts, page-fault curves, Belady's anomaly, disk head movement, allocation
* `results_*.csv` - metrics tables
* `screenshots/` - terminal captures rendered from real program output by `scripts/make_screenshots.py`
  (replace with your own screen grabs if your course requires literal screenshots)

## Design notes
* **Metrics**: waiting = turnaround - burst; response = first CPU time - arrival; CPU utilisation counts idle gaps.
* **Ties** are broken by arrival time then PID for reproducibility. Priority: lower number = higher priority.
* **Disk**: head movement includes the return jump of C-SCAN/C-LOOK; SCAN/C-SCAN go to the physical disk edge.
* **Banker demo**: requests in `banker_safe.json` are processed in order; a granted request updates the state.
* **Error handling**: expected problems raise `ValidationError`/`SimulationError`, are shown as `[ERROR] ...`
  and logged; unexpected exceptions are logged with a traceback and never crash the menu.

## Project layout
```
main.py  run.sh  README.md  REPORT.md  REPORT.docx
osim/      scheduler.py memory.py deadlock.py storage.py reporting.py analysis.py
           validators.py bashbridge.py logger.py errors.py models.py
scripts/   sysinfo.sh log_summary.sh generate_workload.sh run_tests.sh make_screenshots.py
data/ tests/ outputs/ logs/
```
