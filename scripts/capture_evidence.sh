#!/usr/bin/env bash
# Re-capture the verbatim terminal outputs shown in Docs/MoE_Application_Documentation.html
# (test run with coverage, test-gate, project-audit, secret scan, git-hygiene) and rebuild the HTML.
# Usage: scripts/capture_evidence.sh [--no-build]
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
OUT="Docs/assets/data"
PY="${PYTHON:-.venv/bin/python}"
mkdir -p "$OUT"

# capture <file> <command...>: writes "$ <command>", the output, and the exit code.
capture() {
  local file="$1"; shift
  {
    echo "\$ $*"
    "$@" 2>&1
    echo "EXIT=$?"
  } > "$OUT/$file"
  echo "captured $file ($(tail -n1 "$OUT/$file"))"
}

# Placeholders first, so the docs build (run inside the test suite) never sees a missing capture.
for f in gate audit secrets git_hygiene; do [ -f "$OUT/$f.txt" ] || echo "(pending)" > "$OUT/$f.txt"; done

capture pytest_cov.txt "$PY" -m pytest -v -p no:cacheprovider \
  --cov=moe_demo --cov=app --cov=docs_tools --cov-report=term-missing
capture gate.txt bash .bob/skills/test-gate/scripts/run_tests.sh .
capture audit.txt bash .bob/skills/project-audit/scripts/audit.sh
capture secrets.txt bash .bob/skills/secure-config/scripts/scan_secrets.sh
capture git_hygiene.txt bash .bob/skills/git-hygiene/scripts/ensure_gitignore.sh --check

if [ "${1:-}" != "--no-build" ]; then "$PY" -m docs_tools.build_docs; fi
