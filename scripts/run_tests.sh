#!/usr/bin/env bash
# Run the full unit-test suite and save the evidence to outputs/traces/test_results.txt
cd "$(dirname "$0")/.." || exit 1
mkdir -p outputs/traces
python3 -m unittest discover -s tests -v 2>&1 | tee outputs/traces/test_results.txt
exit "${PIPESTATUS[0]}"
