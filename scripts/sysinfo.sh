#!/usr/bin/env bash
# Prints a host snapshot as key=value lines. Parsed by osim/bashbridge.py.
# Uses only /proc and POSIX tools; degrades gracefully if something is missing.
set -u

cpus=$(nproc 2>/dev/null || grep -c '^processor' /proc/cpuinfo 2>/dev/null || echo 0)
mem_total_kb=$(awk '/^MemTotal:/ {print $2}' /proc/meminfo 2>/dev/null || echo 0)
mem_avail_kb=$(awk '/^MemAvailable:/ {print $2}' /proc/meminfo 2>/dev/null || echo 0)
page_size=$(getconf PAGESIZE 2>/dev/null || echo 4096)
load1=$(awk '{print $1}' /proc/loadavg 2>/dev/null || echo 0)
procs=$(ps -e --no-headers 2>/dev/null | wc -l | tr -d ' ')
disk_line=$(df -Pk . 2>/dev/null | awk 'NR==2 {print $2" "$3" "$5}')
disk_total_kb=$(echo "${disk_line:-0 0 0%}" | awk '{print $1}')
disk_used_kb=$(echo "${disk_line:-0 0 0%}" | awk '{print $2}')
disk_use_pct=$(echo "${disk_line:-0 0 0%}" | awk '{gsub("%","",$3); print $3}')
kernel=$(uname -sr 2>/dev/null || echo unknown)

echo "cpus=${cpus}"
echo "mem_total_kb=${mem_total_kb}"
echo "mem_available_kb=${mem_avail_kb}"
echo "page_size_bytes=${page_size}"
echo "load_1min=${load1}"
echo "running_processes=${procs}"
echo "disk_total_kb=${disk_total_kb}"
echo "disk_used_kb=${disk_used_kb}"
echo "disk_use_pct=${disk_use_pct}"
echo "kernel=${kernel}"
