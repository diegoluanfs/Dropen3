# Dropen3 Refactoring Delivery Report

## Source materials

- Original single-file Python program: `Dropen3 (1).py` (5,629 physical lines).
- Manuscript: *Dropen3 an open source graphical application for contact angle and droplet impact analysis* (15 October 2026).
- Brand asset: `logo-1.png`.

## Delivered implementation

- The original monolithic `Dropen3App` class was separated into feature-oriented user-interface and analysis modules.
- Portuguese workflow names, labels, comments, and many internal identifiers were translated to English.
- Source scientific contour routines are preserved as individually importable functions.
- Added independent, type-checked SI-unit reference equations for impact quantities and frame timing.
- Added system doctor with human-readable and JSON reports, plus a graphical diagnostic window.
- Embedded PNG and multi-resolution ICO artwork as packaged application assets.
- Added PyInstaller Windows build automation for a graphical application and a dedicated console doctor.
- Added settings and input-media provenance sidecars for numerical exports.
- Added automated tests and GitHub Actions test configuration.

## Doctor console persistence update (19 October 2026)

- Fixed the original console lifetime: the interactive Windows executable now waits for Enter after printing diagnostics, including when the diagnostics routine raises an exception.
- Added `--no-pause` for automation and `--pause` for explicit interactive use of the Python source command.
- JSON and file-output modes remain nonblocking by default.
- Added `Dropen3Doctor.cmd`, a Windows launcher that holds the console open even if the executable fails before Python initializes. The Windows build script copies it to `dist`.
- Added tests for pause selection, prompt behavior, fatal errors, JSON output, and no-pause reporting.

## Test evidence (authoring environment)

- Python module parse/compile: passed.
- Automated unit tests: 25 passed after the Doctor console update (14 in the initial delivery).
- Approximate Tk shell construction using a **temporary CustomTkinter substitute** in an X virtual display: passed. This is only a structural smoke test; it does not establish genuine CustomTkinter compatibility.
- System doctor executed successfully and flagged missing CustomTkinter and the unavailable graphical desktop in this environment. This is an expected diagnostic finding, not a Windows compatibility result.
- Windows PyInstaller build: **not performed**. It must be produced on Windows and verified on an independent clean PC.
- End-to-end validation on scientific video data: **not performed**. No experimental reference dataset or calibrated ground truth was supplied.

## Required scientific acceptance

The manuscript itself describes outstanding quantitative validation. The existing contour-based measurement approaches require evidence of accuracy, repeatability, contact-width definition, frame timing and fitting stability. See `VALIDATION.md` for an explicit release gate checklist.

## Important distribution notes

- This delivery is a **source-code project**, not a prebuilt Windows `.exe`.
- A Windows `Dropen3.exe` and `Dropen3Doctor.exe` can be generated using `packaging/build_windows.ps1` after obtaining Python and online/offline dependency packages.
- The target user does not need a separately installed Python runtime when using a correctly built one-file executable.
- No license was assigned because the research authors have not yet approved the release terms.
