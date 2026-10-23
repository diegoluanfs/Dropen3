# Dropen3 1.2.0.dev0 — Collaborator Integration Preview

## Included changes

- New optional **Combined Spray and Impact** mode alongside all legacy analysis modes.
- Two segmentation masks, original-frame reference and zoomable substrate-baseline selection.
- Exploratory image-based secondary-droplet tracking, per-object observations,
  main-droplet geometry, contact-relative timing and derived physical groups.
- Ten scientifically labeled plots, named table columns and CSV/XLSX/TXT exports.
- Additional individual-observation CSV and impact-summary JSON provenance files.
- Progress, pause, resume, restart and cancellation behavior.
- Automated tests for scientific equations, synthetic video frames, rendering,
  exports, configuration, mode switching and GUI-controller state.
- The `System Doctor` and `Fit` buttons remain removed from the main window;
  the standalone Doctor program remains available.

## Scientific limitations

This release is **exploratory**, not experimentally validated. The inferred first
contact frame, ellipse diameter proxy, contact width, projected area and 2D spray
envelope are image estimators; their accuracy depends on camera geometry,
segmentation, calibration and recording quality. Image track IDs must not be
reported as confirmed counts of unique physical droplets. No reference laboratory
video or independently annotated ground truth was provided for this delivery.

The pre-impact velocity uses displacement **normal to the selected baseline**,
not total 2D translation speed; the sample-frame indices are exported for review.
Keep the original acquisition FPS and unmodified source video with every result.

## Testing and coverage

- Full suite: **111 passed** with the available test environment.
- Targeted combined tests: **52 passed**.
- Combined scientific module coverage: **95.97% line coverage** (three modules
  only; NOT whole-application coverage).
- Python compilation verified. Actual CustomTkinter/OpenCV desktop acceptance on
  the research machines (Windows and Linux) remains outstanding.

## Integration

Base snapshot: `Dropen3_Research_Linux_Dev5.zip`; the live GitHub branch
was not fetched. Review changes against your working tree and commit to a
feature branch before merging into `main`.

On Windows (PowerShell, project root):

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m dropen3 gui
```

On Debian/Ubuntu Linux (project root):

```bash
bash packaging/setup_linux.sh
./.venv/bin/python -m pytest -q
./.venv/bin/python -m dropen3 gui
```

See `docs/COMBINED_IMPLEMENTATION.md` for the integration checklist and
scientific approval requirements.
