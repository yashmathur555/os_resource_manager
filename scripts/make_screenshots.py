#!/usr/bin/env python3
"""Render real program output into terminal-style PNG captures (outputs/screenshots)."""
import os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"


def shell(cmd, stdin=None):
    r = subprocess.run(cmd, shell=True, cwd=ROOT, input=stdin, capture_output=True, text=True, executable="/bin/bash")
    return (r.stdout + r.stderr).rstrip("\n")


def render(title, text, path, max_lines=46):
    lines = text.splitlines()
    if len(lines) > max_lines:
        lines = lines[:max_lines] + [f"... ({len(text.splitlines()) - max_lines} more lines)"]
    font = ImageFont.truetype(FONT, 15)
    w = max(len(l) for l in lines + [title]) * 9 + 40
    h = len(lines) * 20 + 80
    img = Image.new("RGB", (max(w, 700), h), "#0f172a")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, img.width, 32], fill="#1e293b")
    for i, c in enumerate(("#ef4444", "#f59e0b", "#22c55e")):
        d.ellipse([12 + i * 20, 10, 24 + i * 20, 22], fill=c)
    d.text((90, 7), title, font=font, fill="#94a3b8")
    y = 48
    for l in lines:
        col = "#e2e8f0"
        if "FAULT" in l or "DENIED" in l or "[ERROR]" in l: col = "#fca5a5"
        elif "GRANTED" in l or l.startswith("OK") or " ok" in l[-4:]: col = "#86efac"
        elif l.startswith("==") or l.startswith("#####"): col = "#93c5fd"
        d.text((20, y), l, font=font, fill=col)
        y += 20
    img.save(path)
    print("saved", path)


S = os.path.join(ROOT, "outputs", "screenshots")
os.makedirs(S, exist_ok=True)
render("$ ./run.sh menu", shell("python3 main.py", "0\n"), f"{S}/01_main_menu.png")
render("Menu > 1 CPU scheduling (SRTF, textbook workload)", shell("python3 main.py", "1\n\nSRTF\n4\n0\n").split("Select an option:")[1], f"{S}/02_cpu_scheduling.png")
render("Menu > 2 Page replacement (LRU, 3 frames)", shell("python3 main.py", "2\nfile\n\n3\nLRU\n0\n").split("Select an option:")[1], f"{S}/03_page_replacement.png")
render("Menu > 4 Deadlock handling (Banker's requests)", shell("python3 main.py", "4\n1\n\nn\n0\n").split("Select an option:")[1], f"{S}/04_deadlock_banker.png")
render("Menu > 5 Disk scheduling (all algorithms)", shell("python3 main.py", "5\n\nALL\n0\n").split("Select an option:")[1], f"{S}/05_disk_scheduling.png", 60)
render("Menu > invalid input / missing file handling", shell("python3 main.py", "9\n1\ndata/missing.csv\n\n\n0\n").replace("\n\n", "\n"), f"{S}/06_error_handling.png", 60)
render("$ bash scripts/sysinfo.sh ; bash scripts/log_summary.sh", shell("bash scripts/sysinfo.sh; echo ---; bash scripts/log_summary.sh"), f"{S}/07_bash_integration.png")
render("$ ./run.sh tests", shell("python3 -m unittest discover -s tests 2>&1 | tail -8"), f"{S}/08_test_results.png")
