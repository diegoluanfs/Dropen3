"""Executable entry point: GUI by default, System Doctor on demand."""
from __future__ import annotations
import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="dropen3", description="Dropen3 scientific wetting analysis")
    parser.add_argument("command", nargs="?", choices=["gui", "doctor"], default="gui")
    parser.add_argument("--doctor", action="store_true", help="Run the system doctor without opening the analysis GUI")
    parser.add_argument("--json", action="store_true", help="Print a JSON doctor report")
    pause_options = parser.add_mutually_exclusive_group()
    pause_options.add_argument("--pause", action="store_true", help="Keep the interactive console open until Enter is pressed")
    pause_options.add_argument("--no-pause", action="store_true", help="Return immediately after diagnostics (for automation)")
    parser.add_argument("--output", type=Path, help="Save the doctor report to a file")
    options = parser.parse_args(argv)
    if options.command == "doctor" or options.doctor:
        from dropen3.system.doctor_cli import run_doctor
        return run_doctor(
            as_json=options.json,
            output_path=options.output,
            force_pause=options.pause,
            no_pause=options.no_pause,
        )
    from dropen3.ui.application import Dropen3App
    app = Dropen3App()
    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
