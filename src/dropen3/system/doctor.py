"""Standalone dependency and runtime checks, including frozen executable checks.

The system doctor is intentionally written using only the Python standard library.
Running it never imports the graphical analysis application.
"""
from __future__ import annotations
import importlib
import importlib.util
import json
import os
import platform
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Packages are installed in the build environment and bundled with the executable.
# End users of a frozen executable do not need a separate Python installation.
REQUIRED_MODULES = {
    "numpy": "Numerical computations",
    "cv2": "Image and video processing",
    "scipy": "Scientific fitting and filtering",
    "pandas": "Tabular results",
    "matplotlib": "Scientific graphs",
    "PIL": "Image rendering",
    "customtkinter": "Graphical interface",
    "openpyxl": "Excel export",
}


def _add(checks: list[dict[str, str]], name: str, status: str, detail: str, action: str = ""):
    checks.append({"check": name, "status": status, "detail": detail, "action": action})


def collect_diagnostics(*, check_display: bool = True) -> dict[str, Any]:
    checks: list[dict[str, str]] = []
    frozen = bool(getattr(sys, "frozen", False))
    system = platform.system()
    _add(checks, "Operating system", "PASS" if system in {"Windows", "Linux", "Darwin"} else "WARN",
         f"{platform.platform()} ({platform.machine()})", "Windows 10/11 64-bit is the primary release target.")
    _add(checks, "Distribution mode", "PASS", "Bundled application" if frozen else "Python source environment")
    _add(checks, "Python runtime", "PASS" if sys.version_info >= (3, 11) else "FAIL",
         platform.python_version(), "Build with Python 3.11 or newer" if sys.version_info < (3, 11) else "")
    for module, purpose in REQUIRED_MODULES.items():
        try:
            spec = importlib.util.find_spec(module)
            if spec is None:
                _add(checks, module, "FAIL", f"Not available: {purpose}",
                     "Rebuild the executable with its complete requirements" if frozen else "Install using pip install -e .")
                continue
            # Spec discovery alone is insufficient: a native library can be present
            # but fail to load because DLLs/shared libraries are missing.
            imported = importlib.import_module(module)
            version = getattr(imported, "__version__", "version not reported")
            _add(checks, module, "PASS", f"{purpose}; import successful ({version})")
        except Exception as error:
            _add(checks, module, "FAIL", f"Import failed: {type(error).__name__}: {error}",
                 "Reinstall compatible native dependencies or rebuild on the target platform")
    try:
        import tkinter
        _add(checks, "Tkinter", "PASS", f"Tk {tkinter.TkVersion} is available")
        if check_display:
            try:
                root = tkinter.Tk()
                root.withdraw()
                root.update_idletasks()
                root.destroy()
                _add(checks, "Graphical desktop", "PASS", "Graphical window initialized")
            except Exception as error:
                _add(checks, "Graphical desktop", "FAIL", str(error), "Use a desktop session with an available display")
    except ImportError as error:
        _add(checks, "Tkinter", "FAIL", str(error), "Install Python with Tk support or rebuild the package")
    try:
        from importlib.resources import files
        resource = files("dropen3.assets").joinpath("logo.png")
        with resource.open("rb") as stream:
            signature = stream.read(8)
        if signature != b"\x89PNG\r\n\x1a\n":
            raise ValueError("Invalid bundled PNG signature")
        _add(checks, "Bundled logo", "PASS", "Application logo is included in package resources")
    except (OSError, ModuleNotFoundError, ValueError) as error:
        _add(checks, "Bundled logo", "FAIL", str(error), "Check PyInstaller data collection")
    try:
        disk = shutil.disk_usage(tempfile.gettempdir())
        free_mb = disk.free // (1024 * 1024)
        status = "PASS" if free_mb >= 1024 else "WARN"
        _add(checks, "Temporary disk space", status, f"{free_mb} MiB available",
             "Free at least 1 GiB for large video processing sessions" if status == "WARN" else "")
    except OSError as error:
        _add(checks, "Temporary disk space", "WARN", str(error))
    try:
        import cv2
        version = cv2.__version__
        build = cv2.getBuildInformation()
        decoder = next((line.strip() for line in build.splitlines() if line.strip().startswith("FFMPEG:")), "FFMPEG support unreported")
        decoder_ready = "YES" in decoder
        _add(checks, "OpenCV video backend", "PASS" if decoder_ready else "WARN", f"OpenCV {version}; {decoder}",
             "Test the exact experimental recording and codec on this computer")
        import numpy as np
        image = np.zeros((8, 8, 3), dtype=np.uint8)
        ok, encoded = cv2.imencode(".png", image)
        if not ok or cv2.imdecode(encoded, cv2.IMREAD_COLOR) is None:
            raise RuntimeError("Image encode/decode failed")
        _add(checks, "Image processing self-test", "PASS", "8x8 pixel PNG encode/decode completed")
    except Exception as error:
        _add(checks, "OpenCV processing", "FAIL", f"{type(error).__name__}: {error}",
             "Install a compatible OpenCV build and required system libraries")
    return {"application": "Dropen3", "generated_utc": datetime.now(timezone.utc).isoformat(),
            "platform": system, "frozen": frozen,
            "checks": checks, "summary": {key: sum(x["status"] == key for x in checks) for key in ("PASS", "WARN", "FAIL")}}


def render_text(report: dict[str, Any]) -> str:
    lines = ["Dropen3 System Doctor", "====================", ""]
    for item in report["checks"]:
        lines.append(f"[{item['status']:<4}] {item['check']}: {item['detail']}")
        if item["action"] and item["status"] != "PASS":
            lines.append(f"       Action: {item['action']}")
    summary = report["summary"]
    lines.extend(["", f"Summary: {summary['PASS']} passed, {summary['WARN']} warnings, {summary['FAIL']} failures."])
    return "\n".join(lines)
