"""Interactive console front end for the system doctor.

A frozen console executable started from Windows Explorer gets a console window
that would otherwise disappear when the Python process exits. Keep it visible
until the operator acknowledges the result. In redirected and JSON modes, keep
standard CLI behavior so scripts and automated tests cannot be blocked.
"""
from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path
from typing import TextIO


def should_pause(
    *,
    force_pause: bool = False,
    no_pause: bool = False,
    machine_mode: bool = False,
    frozen: bool | None = None,
    input_stream: TextIO | None = None,
) -> bool:
    """Pause by default for an interactive, frozen, human-readable Doctor run.

    Never wait for input without an interactive console; this is important for
    scheduled execution, CI systems, and processes with redirected I/O.
    """
    if no_pause or machine_mode:
        return False

    if input_stream is None:
        input_stream = sys.stdin
    if input_stream is None:
        return False
    try:
        interactive = input_stream.isatty()
    except (AttributeError, OSError, ValueError):
        return False
    if not interactive:
        return False

    if force_pause:
        return True
    if frozen is None:
        frozen = bool(getattr(sys, "frozen", False))
    return frozen


def wait_for_exit(*, input_stream: TextIO | None = None, output_stream: TextIO | None = None) -> None:
    """Wait for acknowledgement while handling closed input safely."""
    if input_stream is None:
        input_stream = sys.stdin
    if output_stream is None:
        output_stream = sys.stdout
    if input_stream is None or output_stream is None:
        return
    try:
        output_stream.write("\nDiagnostics complete. Press Enter to close this window... ")
        output_stream.flush()
        input_stream.readline()
    except (EOFError, KeyboardInterrupt, OSError, ValueError):
        # The console was closed or detached; there is no prompt to preserve.
        return


def run_doctor(
    *,
    as_json: bool = False,
    output_path: Path | None = None,
    force_pause: bool = False,
    no_pause: bool = False,
) -> int:
    """Run diagnostics and keep the frozen interactive console visible.

    Exit codes: 0 for no failed checks, 1 for failed checks, and 2 for a fatal
    diagnostic or report-writing exception.
    """
    pause = should_pause(
        force_pause=force_pause,
        no_pause=no_pause,
        machine_mode=as_json or output_path is not None,
    )
    try:
        from dropen3.system.doctor import collect_diagnostics, render_text

        if not as_json:
            print("Dropen3 System Doctor", flush=True)
            print("Checking system requirements. Please wait...\n", flush=True)
        report = collect_diagnostics()
        content = (
            json.dumps(report, indent=2, ensure_ascii=True)
            if as_json
            else render_text(report)
        )
        if output_path is not None:
            output_path.write_text(content + "\n", encoding="utf-8")
        print(content, flush=True)
        if output_path is not None and not as_json:
            print(f"\nReport saved to: {output_path}", flush=True)
        return 1 if report["summary"]["FAIL"] else 0
    except Exception:
        # Keep the traceback visible rather than immediately losing the console.
        print("\nFATAL ERROR: The system doctor could not finish.", file=sys.stderr, flush=True)
        traceback.print_exc(file=sys.stderr)
        return 2
    finally:
        if pause:
            wait_for_exit()
