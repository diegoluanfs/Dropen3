# Dropen3 on Linux

This guide describes a **source installation** of Dropen3 1.1.0.dev5. It is not a prebuilt Linux release. The graphical interface and OpenCV point-selection windows require a working desktop display.

## Requirements

- 64-bit Linux desktop with X11 or a compatible Wayland/XWayland environment.
- Python 3.11, 3.12, or 3.13, with `venv`, `pip`, and Tkinter.
- Working OpenGL/X11 runtime libraries used by the `opencv-python` wheel.
- Git for collaboration, internet access for initial Python package installation.
- Sufficient storage and memory for the actual video dataset; there is no validated minimum for large high-speed recordings.

### Ubuntu / Debian (apt)

Open a terminal and run:

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip python3-tk libgl1 libglib2.0-0 libx11-6 libxext6 libxrender1 libsm6 libice6
```

Use an available supported interpreter (3.11 through 3.13). If your distro's default `python3` is outside that range, install a supported version using your distribution's supported instructions; do not replace its system Python. Package names and availability vary by distro and release.

### Fedora

For Fedora, start with `sudo dnf install git python3 python3-pip python3-tkinter python3-devel mesa-libGL glib2`. If Python's version is outside the declared supported range, select a supported interpreter. Additional GUI library packages may be needed depending on the Fedora release.

## Clone, install, and run

In a terminal, choose a project directory and substitute the real repository URL:

```bash
git clone https://github.com/diegoluanfs/Dropen3.git
cd REPOSITORY
python3 --version
python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -e '.[test]'
./.venv/bin/python -m pytest -q
./.venv/bin/python -m dropen3 doctor --no-pause
./.venv/bin/python -m dropen3 gui
```

Do not type the example URL literally: replace `ORGANIZATION/REPOSITORY` with the actual GitHub path. Run commands from the directory containing `pyproject.toml`.

Alternatively, from that directory run `bash packaging/setup_linux.sh`. This creates/reuses `.venv`, installs development dependencies and runs the Doctor. It does **not** install system dependencies or launch the GUI.

## Diagnostics

```bash
./.venv/bin/python -m dropen3 doctor --no-pause
./.venv/bin/python -m dropen3 doctor --json --output linux-doctor.json
```

A Doctor pass does not guarantee compatibility with a specific video codec, camera acquisition format, Linux compositor, or scientific dataset. Test with representative input media and verify numerical outputs against known reference data.

## Troubleshooting

| Symptom | Suggested check |
| --- | --- |
| `No module named tkinter` | Install the Tk package matching the Python interpreter, e.g. `python3-tk` on Ubuntu/Debian. |
| `libGL.so.1` or related shared-library error | Install the distribution's GL runtime, e.g. `libgl1` on Ubuntu/Debian. |
| `no display name and no $DISPLAY` or Tk cannot initialize | Use a local graphical desktop or configure X11/XWayland display forwarding. Headless SSH sessions cannot open the GUI without a display server. |
| Video opens but frames are missing or corrupt | Verify the file, video codec, OpenCV backend and calibration. Re-encode a **copy** for a compatibility test without overwriting experimental originals. |
| A different Python version is used | Create the venv using a supported version, such as `python3.12 -m venv .venv`. |
| Permission denied on script | Run `bash packaging/setup_linux.sh` rather than assuming executable permissions. |

Do not use `sudo pip install` for this application. Keep experimental source images/videos immutable, retain original frame indices and acquisition FPS, and archive calibration and processing parameters with exports.

## Packaging and compatibility

The Windows `.exe` files cannot run natively on Linux. PyInstaller must build on the target operating system, and portability across different distributions and `glibc` versions is **not guaranteed**. At present the supported Linux workflow is installation from source in a virtual environment. A future Linux binary must be built and tested on supported Linux targets; a Windows-built `.exe` is not a Linux package.

## Scientific release status

Linux unit tests in GitHub Actions are useful but do not certify Linux GUI behavior or experimental accuracy. Before reporting scientific results, perform interactive testing of baseline selection, keyboard navigation, maximum zoom recovery, contact angle, hysteresis, impact, video import/export and numerical comparisons with reference data on the actual Linux workstation.
