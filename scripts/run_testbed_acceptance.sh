#!/usr/bin/env bash
# Sprint 2 testbed-acceptance runner — Item 23 prerequisite #1.
# Runs the canonical dual-session invocation against the running testbed
# and captures terminal stream + HTML/TXT/JSON sinks for inspection.
#
# Self-contained: starts testbed, waits for health, runs three scans,
# kills testbed, returns the captured artifacts in screenshots/sprint-2/.

set -euo pipefail

cd "$(dirname "$0")/.."

# Start testbed
python3 -m webprobe.testbed > /tmp/webprobe-testbed.log 2>&1 &
TESTBED_PID=$!
trap "kill $TESTBED_PID 2>/dev/null || true" EXIT
sleep 2

# Verify testbed health
curl -sf http://localhost:9999/__webprobe_testbed__/health >/dev/null \
    || { echo "[-] testbed health check failed"; exit 1; }

# Canonical acceptance invocation (matches scope.md acceptance image)
URL_LIST=$(mktemp)
printf "/idor/1\n/vulnerable?q=test\n/reflect-xss?q=test\n" > "$URL_LIST"

OUT_DIR="screenshots/sprint-2"
mkdir -p "$OUT_DIR"

# Run 1: default grouping (all 12 modules, dual-session, terminal+HTML+TXT+JSON)
python3 -m webprobe http://localhost:9999 \
    --auth-form http://localhost:9999/login --auth-user admin --auth-pass any \
    --idor-baseline-form http://localhost:9999/login --idor-baseline-user alice --idor-baseline-pass any \
    --url-list "$URL_LIST" \
    > "$OUT_DIR/terminal-acceptance.txt" 2>&1

# Move the auto-named output files into the screenshots dir
mv webprobe_localhost_9999_*.html "$OUT_DIR/default-grouping.html" 2>/dev/null || true
mv webprobe_localhost_9999_*.txt  "$OUT_DIR/default-grouping.txt"  2>/dev/null || true
mv webprobe_localhost_9999_*.json "$OUT_DIR/default-grouping.json" 2>/dev/null || true

# Run 2: --fit3048 grouping (HTML report shows 7-category structure)
python3 -m webprobe http://localhost:9999 \
    --auth-form http://localhost:9999/login --auth-user admin --auth-pass any \
    --idor-baseline-form http://localhost:9999/login --idor-baseline-user alice --idor-baseline-pass any \
    --url-list "$URL_LIST" \
    --fit3048 \
    > /dev/null 2>&1

mv webprobe_localhost_9999_*.html "$OUT_DIR/fit3048-grouping.html" 2>/dev/null || true
rm -f webprobe_localhost_9999_*.txt webprobe_localhost_9999_*.json 2>/dev/null || true

# Run 3: testbed-as-target (no auth, demonstrates risk-gate banner suppression)
python3 -m webprobe http://localhost:9999 > "$OUT_DIR/testbed-unauth.txt" 2>&1

mv webprobe_localhost_9999_*.html "$OUT_DIR/testbed-unauth.html" 2>/dev/null || true
rm -f webprobe_localhost_9999_*.txt webprobe_localhost_9999_*.json 2>/dev/null || true

rm -f "$URL_LIST"

# Acceptance check: JSON sink must contain canonical finding_type markers
echo
echo "=== Acceptance markers (finding_type from JSON envelope) ==="
grep -oE '"finding_type": "[^"]+"' "$OUT_DIR/default-grouping.json" \
    | sort -u | head -20
echo
echo "=== Coverage (terminal stream) ==="
grep -A5 "SCAN COVERAGE" "$OUT_DIR/terminal-acceptance.txt" | head -15
echo
echo "Artifacts written to $OUT_DIR/"
ls -la "$OUT_DIR/"
