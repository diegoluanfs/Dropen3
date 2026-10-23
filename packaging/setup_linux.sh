#!/usr/bin/env bash
# Dropen3 source setup for an existing Linux desktop and supported Python runtime.
set -Eeuo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  printf 'ERROR: Python interpreter not found: %s\n' "$PYTHON_BIN" >&2
  exit 1
fi

"$PYTHON_BIN" - <<'PY'
import sys
if not ((3, 11) <= sys.version_info[:2] < (3, 14)):
    raise SystemExit('ERROR: Dropen3 requires Python 3.11, 3.12 or 3.13.')
print(f'Using Python {sys.version.split()[0]}')
PY

if ! "$PYTHON_BIN" -c 'import tkinter' >/dev/null 2>&1; then
  echo 'ERROR: Tkinter not available. Install your distribution Python/Tk package (e.g. python3-tk).' >&2
  exit 1
fi

"$PYTHON_BIN" -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[test]'
.venv/bin/python -m dropen3 doctor --no-pause
cat <<'MSG'

Setup complete. To run the tests and open Dropen3:
  ./.venv/bin/python -m pytest -q
  ./.venv/bin/python -m dropen3 gui
MSG
