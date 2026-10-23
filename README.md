# Dropen3 — Research Software

Dropen3 is an open-source graphical Python application for **static contact angle**, **advancing/receding behavior**, and **droplet impact** analysis. This is a research-oriented refactoring of the supplied original single-file application, organized by workflow and supplemented with an independent scientific-metrics module, a system doctor, unit tests, and Windows build instructions.

> **Research integrity notice:** This is a development release, not a scientifically validated measurement instrument. Its scientific routines were carried over from the supplied application except for explicitly documented safety changes. The project needs independent numerical and experimental verification, especially for segmentation, baseline selection, droplet shape, impact timing, uncertainty propagation, and angle quadrant handling. Avoid presenting results as validated without a documented verification protocol.

## Supported workflows

| Workflow | Code location |
| --- | --- |
| Main UI, navigation, settings, output | `src/dropen3/ui/` |
| Contact angle algorithms | `src/dropen3/science/contact_angles.py` |
| Reference SI-unit equations | `src/dropen3/science/metrics.py` |
| Static contact angle | `src/dropen3/analysis/static.py` |
| Advancing/receding analysis | `src/dropen3/analysis/hysteresis.py` |
| Droplet impact | `src/dropen3/analysis/impact.py` |
| Spray and breakup | `src/dropen3/analysis/spray.py` |
| Video sequencing | `src/dropen3/analysis/video_tools.py` |
| Graph generation | `src/dropen3/analysis/plotting.py` |
| Environment diagnostic | `src/dropen3/system/doctor.py` |
| Doctor console and interactive exit handling | `src/dropen3/system/doctor_cli.py` |

## Linux researchers and contributors

For Linux installation, Tkinter/OpenCV system dependencies, Doctor commands, and platform caveats, see **[docs/LINUX.md](docs/LINUX.md)**. For GitHub invitations, feature branches, pull requests, and scientific review requirements, see **[CONTRIBUTING.md](CONTRIBUTING.md)**. The Linux workflow currently runs from Python source; the Windows `.exe` is not a Linux executable.

## Install for scientific development

Windows PowerShell using Python **3.12**:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e '.[test]'
python -m pytest -q
python -m dropen3 doctor
python -m dropen3 gui
```

When using the source command, add `--pause` to wait for Enter in an interactive terminal. The system doctor does not need a graphical display to print most checks; `python -m dropen3 doctor --json --output report.json` writes a machine-readable report. The regular GUI also has a **System Doctor** button. Diagnosis checks the Python runtime (or bundled runtime), packages, Tk, temporary disk space, packaged logo, OpenCV and basic image decoding. It reports video backend support but **cannot guarantee every research camera codec** will decode. Test an actual source video.

## Deliver the Windows executable

Run from Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\packaging\build_windows.ps1
.\dist\Dropen3Doctor.exe
.\dist\Dropen3Doctor.exe --json --output doctor-report.json
.\dist\Dropen3.exe
```

The script builds two self-contained **Windows executables**: the graphical `Dropen3.exe` and a terminal-friendly `Dropen3Doctor.exe`. It also copies `Dropen3Doctor.cmd` to the `dist` directory. **Double-clicking `Dropen3Doctor.exe` will print the checks and wait for Enter before closing** when it has an interactive console. The optional `Dropen3Doctor.cmd` launcher also waits for a keypress, including when the `.exe` fails before Python can start. Keep the `.cmd` file next to the executable when using it.

For unattended execution, use `Dropen3Doctor.exe --no-pause`. The `--json` and `--output` report modes automatically avoid interactive waiting, enabling command-line automation. From the source environment, use `python -m dropen3 doctor --pause` when you want to inspect results before returning to the prompt. When launching inside an existing PowerShell window, only the process completes; the PowerShell window remains open as usual. The logo is packaged as an application resource and does not need a PNG file alongside the installed executable. A user's computer should not require a separate Python installation. The first launch of a one-file build may be slower due to unpacking and antivirus inspection. Ensure sufficient temporary space and test on a clean Windows 10/11 64-bit machine with the scientific camera's real footage.

**Do not attempt to create a Windows executable by building on Linux.** Build and smoke-test on Windows. There is no claim of a completed Windows build or GUI acceptance test in this delivery.

## Interactive navigation and pixel-accurate zoom (development update)

The main viewer supports **A / Left Arrow** (previous frame) and **D / Right Arrow**
(next frame). A manual frame step pauses playback. The frame counter and slider
track the original video frame index. Frame selection shortcuts do not operate
while typing in text inputs.

Mouse-wheel zoom, drag-to-zoom and the **Fit** button operate on the displayed
image region while retaining the original image coordinates. The optional
magnifier also uses this mapping. Dragging in the main viewer is *view zoom*;
it does not replace the analytical ROI and baseline dialogs.

Manual point-selection windows for static contact-angle, hysteresis, impact,
and spray baseline workflows support wheel or `+` / `-` zoom, `0` to fit,
Backspace or right-click to undo, and Escape to cancel. Points are returned in
original source-image pixels, even if the displayed region is cropped or scaled.
Video point-selection windows also support A/D and directional arrows to
change the frame; they clear points after a frame change and require **Enter**
to confirm two points on the same frame.

See [docs/INTERACTION_REGRESSION.md](docs/INTERACTION_REGRESSION.md) for the
Windows acceptance checklist and limitations.

To run this source release in PowerShell, **open a terminal in the directory that
contains `pyproject.toml`** and run:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m dropen3 gui
```

Do not rebuild the Windows executable until the relevant workflows have been
visually checked on a Windows machine.

## Scientific reference definitions

The new module `science.metrics` includes individually tested formulas, following the submitted manuscript:

- `Re = density * speed * diameter / dynamic_viscosity`
- `We = density * speed**2 * diameter / surface_tension`
- `Oh = dynamic_viscosity / sqrt(density * surface_tension * diameter)`
- `time = (original_frame_index - first_contact_frame_index) / acquisition_fps`
- `contact_width = (right_contact_x - left_contact_x) * scale`
- `beta = contact_width / preimpact_diameter`
- `hysteresis = advancing_angle - receding_angle` (only when a defined experimental protocol supplies both angles)

These functions are **reference and validation infrastructure**; retaining the existing GUI workflows does not imply all legacy impact paths use them yet. The legacy workflows still require detailed scientific verification. Do not equate the maximum projected silhouette width with wetted contact diameter. The area from a side-view contour is a projected area, not automatically a wetted footprint.

## Limitations and release gates

See `docs/VALIDATION.md` and `docs/DELIVERY_REPORT.md` for known deficiencies and the test plan. A clean compile, static checks, and numerical tests are necessary but not sufficient for scientific reliability. Freeze dependency versions and archive release artifacts for a journal submission. The supplied draft does not specify a finalized repository, license, or archived release: these must be approved by the research authors before publication. This project intentionally does not invent a software license or institution approval.


## Zoom-out display regression (1.1.0.dev3)

The main viewer now renders onto a fixed-size preview, which keeps the display
geometry stable when zooming out. The `-` button and mouse-wheel-out use the
exact inverse of the `+` magnification step. Affected files: `ui/viewer.py`,
`ui/viewport.py`, `ui/rendering.py`, and `ui/core.py`. Frame navigation by
A/D and arrow keys is unchanged.

From the root of the extracted project, run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m dropen3 gui
```

Import a video and zoom in repeatedly, then out repeatedly; verify full-frame
recovery, use Fit, and navigate frames. Repeat with zoom anchored near image
edges. Desktop and experimental-video validation remains necessary.

## Continuous zoom-out below fitted size (1.1.0.dev4)

The previous crop-only implementation did not support zooming out beyond the
full-frame fitted view. The main viewer now has two independent controls:

- `roi_zoom` stores a region in **original frame coordinates** for magnification.
- `zoom_factor` (0.25 to 1.0) scales the **display-only** full-frame preview when
  zoomed out below the fitted size.

`-` decreases the preview size even from the initial fitted view. `+` reverses
that reduction, restores the fitted size, and then magnifies the image. `Fit`
restores the whole frame at its standard fitted size. Mouse-wheel zoom uses the
same routine. Source images, annotation coordinates, and A/D or arrow-key frame
navigation remain unchanged.

The new regression tests are in `tests/test_zoom_below_fit.py`. Tkinter smoke
checks and numerical regression tests have passed in the development environment;
final inspection with CustomTkinter on Windows remains a separate requirement.


## Maximum-zoom recovery (1.1.0.dev5)

A 2 x 2-pixel image crop could previously become stuck: 2 pixels divided by
(1 / 1.2) rounded back to 2, so Zoom Out never increased the viewing area.
Zoom-in now stops at a maximum **32x relative to the original image** for
normal frames. Zoom-out always expands the original-image crop by at least one
pixel in each axis until the fitted view is reached. Zoom-out below Fit remains
available down to 25% of fitted display size.

The same correction applies to the OpenCV point-selection windows, which share
the crop function. Neither scientific source data nor pixel annotations are
resampled or modified by the zoom controls. The A/D and arrow-key navigation
was not changed. See `tests/test_zoom_maximum_regression.py` for the boundary
and recovery test cases. Windows GUI acceptance testing remains necessary.
