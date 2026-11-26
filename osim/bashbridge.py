"""Python <-> Bash integration. Python calls the helper scripts in scripts/ with
subprocess, validates their output, and converts it into dictionaries."""
import os
import shutil
import subprocess
from typing import Dict

from .errors import BashToolError
from .logger import get_logger

log = get_logger("bashbridge")
SCRIPT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")


def run_script(name: str, args=(), timeout: int = 15) -> str:
    if shutil.which("bash") is None:
        raise BashToolError("bash is not available on this system.")
    path = os.path.join(SCRIPT_DIR, name)
    if not os.path.isfile(path):
        raise BashToolError(f"Helper script not found: {name}")
    try:
        proc = subprocess.run(["bash", path, *map(str, args)], capture_output=True,
                              text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        log.error("Bash script %s timed out", name)
        raise BashToolError(f"{name} timed out after {timeout}s.")
    if proc.returncode != 0:
        msg = (proc.stderr or proc.stdout).strip() or f"exit code {proc.returncode}"
        log.error("Bash script %s failed: %s", name, msg)
        raise BashToolError(f"{name} failed: {msg}")
    log.info("Bash script %s ok", name)
    return proc.stdout


def parse_kv(text: str) -> Dict[str, str]:
    out = {}
    for line in text.splitlines():
        if "=" in line:
            key, _, val = line.partition("=")
            out[key.strip()] = val.strip()
    return out


def system_snapshot() -> Dict[str, str]:
    return parse_kv(run_script("sysinfo.sh"))


def log_summary(path: str = None) -> Dict[str, str]:
    return parse_kv(run_script("log_summary.sh", [path] if path else []))


def generate_workload(n: int, seed: int, out_path: str) -> str:
    run_script("generate_workload.sh", [n, seed, out_path])
    return out_path
