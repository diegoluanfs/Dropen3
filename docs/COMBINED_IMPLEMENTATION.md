# Combined Spray and Impact — Engineering Delivery and Scientific Review

**Release:** 1.2.0.dev0 (research preview)  
**Status:** Code integrated; automated synthetic tests pass. Laboratory accuracy and Windows/Linux GUI acceptance remain outstanding.  
**Language:** All introduced modules, fields, messages and documentation use English. An automated English-source convention test is included.

## 1. Modules added or changed

| Function | Location |
|---|---|
| Scientific types, calibration and frame metrics | `science/combined.py` |
| Segmentation, preliminary tracking and image-based measurements | `analysis/combined_core.py` |
| GUI workflow, session controls and observation export | `analysis/combined.py` |
| Named, unit-labeled plots | `analysis/combined_plotting.py` |
| Sidebar, table and existing plotting dispatch | `ui/home.py`, `ui/export.py`, `analysis/plotting.py` |
| Tests (science, frame processing, plots, exports, state transitions) | `tests/test_combined_*.py` |

The original Static Angle, Hysteresis, Drop Impact and legacy Spray methods remain available. The System Doctor and Fit buttons are **not** reintroduced in the main GUI.

## 2. Measurement contract (provisional; scientist review required)

- Coordinates are taken from the **original unmodified video frame**. Image `y` increases downward. The baseline is two nonvertical original-image pixel locations; signed distance is negative above and positive below the substrate.
- `acquisition_time_s = original_frame_index / acquisition_fps`; contact-relative time is `(original_frame_index - first_contact_frame_index) / acquisition_fps`. Both use the *camera acquisition frame rate*, not video playback speed.
- `initial_diameter_mm` is an exploratory median of the pre-contact ellipse-axis-mean diameter estimators. Validate this convention against a physically appropriate diameter definition and independently measured pre-impact images.
- `preimpact_velocity_m_s` is the magnitude of the regression slope of the pre-contact centroid's **normal distance from the selected baseline** versus acquisition time, converted from pixel/s to m/s. This applies to inclined baselines too; it is not the full 2D trajectory speed. All pre-contact detections currently contribute to the regression; the frame indices are exported and the selected fit interval must be reviewed by the scientist. The sign is not retained.
- `contact_width_mm` is computed from resolved contour points within a configured tolerance of the substrate baseline. It is a **side-view estimator**; its agreement with the actual wetted contact line has not been benchmarked.
- `height_mm` is the maximum normal distance above the substrate; `projected_area_mm2` is the projected side-view contour area, **not** the wetted footprint.
- `spreading_factor = contact_width_mm / initial_diameter_mm` only when both quantities are measured. `contact_width_rate_mm_s` uses differences between consecutive valid contact widths and their original frame indices.
- `Re = rho * U * D / mu`, `We = rho * U**2 * D / gamma`, `Oh = mu / sqrt(rho * gamma * D)` with SI quantities. Missing diameter or velocity yields missing dimensionless numbers rather than a substituted physical default.
- `equivalent_diameter_px = 2 * sqrt(projected_contour_area_px2 / pi)` for each secondary image object. Each result is retained individually with original frame index and assigned track ID.
- `visible_secondary_count` counts detected secondary contours in **one frame**. `cumulative_track_count` counts image identities assigned by a distance-based tracker; it is **not** a verified cumulative count of unique physical droplets, nor a droplet creation rate.
- `spray_envelope_angle_deg` is a preliminary **2D image envelope** below the selected baseline, not a calibrated 3D cone angle. It is absent when fewer than two usable detections exist.
- A frame where segmentation, contact position or calibration information is missing reports a status and missing values. Failure to resolve a measurement must not become a physical zero.

## 3. Migration backlog status

| Audit ID | Engineering status | Approval / limitation |
|---|---|---|
| D3-01 | **Provisional measurement contract documented** | Scientist must approve diameter, contact, spray geometry definitions |
| D3-02 | **Implemented** | Immutable per-frame results and data model |
| D3-03 | **Implemented, exploratory** | Background-difference masks with primary/secondary thresholds; real-video benchmark needed |
| D3-04 | **Implemented, provisional** | Select reference background and baseline; camera-plane calibration remains operator supplied |
| D3-05 | **Implemented, approximate** | Deterministic association/track IDs; not validated unique physical droplet count |
| D3-06 | **Implemented, exploratory** | Ellipse-proxy diameter and pre-impact centroid regression; measure against reference data |
| D3-07 | **Implemented, exploratory** | Side-view contact width, normal height and projected silhouette area |
| D3-08 | **Implemented** | SI dimensionless equations; input measurement uncertainties remain unvalidated |
| D3-09 | **Implemented** | Individual secondary observations retained for distributions and CSV export |
| D3-10 | **Provisional estimator only** | 2D envelope; calibrated cone-angle method still needs scientific approval |
| D3-11 | **Implemented** | Separate `SPRAY_IMPACT` menu; legacy modes retained |
| D3-12 | **Implemented** | Unified table, CSV/XLSX/TXT, observation CSV, summary JSON, provenance sidecar |
| D3-13 | **Implemented** | Seven descriptive combined geometry plots; raw measurements preserved |
| D3-14 | **Implemented** | Secondary diameter distribution, envelope-angle series, visible/count-ID series |
| D3-15 | **Implemented; tests added** | Pause, resume, restart, callback cleanup; desktop acceptance pending |
| D3-16 | **Implemented in new code** | New paths use English; targeted legacy identifier/label cleanup applied |
| D3-17 | **Prepared, not platform-certified** | A/D and extended-arrow navigation; test on Windows and Linux OpenCV backends |
| D3-18 | **Synthetic regression tests added** | Experimental golden datasets, tolerances and uncertainties are outstanding |
| D3-19 | **Implemented; desktop check pending** | Progress indicator and cancellation via reset/stop paths |
| D3-20 | **Implemented** | Horizontally scrollable named measurement table |

## 4. Automated verification results

At delivery, the development environment ran:

- **108 tests passed** for the full source tree (`python -m pytest -q`).
- **52 dedicated tests passed** for combined scientific core, processing, plots, exports and GUI-controller state.
- The measured **line coverage is 95.72%** across the three new scientific modules `science/combined.py`, `analysis/combined_core.py`, and `analysis/combined_plotting.py` (**not** across the full application). This exceeds a 90% dedicated CI gate.
- GUI-state tests cover callback duplication, pause/resume, cancellation, frame iteration and completion in headless fakes. These tests **do not verify live CustomTkinter/OpenCV interaction**.

Tests cannot prove laboratory accuracy. They exercise analytical identities, synthetic contour behavior, original frame indexing, immutability, absent measurements, tracker state, reproducible exports, graph validity, GUI controller state and English-language conventions.

## 5. Real-world acceptance checklist before publishing numbers

1. On **Windows and Linux**, import a laboratory MP4/AVI that includes clean pre-impact frames and representative impact/splash behavior. Confirm selection dialogs, scaling and keyboard navigation.
2. Select a clean reference frame and baseline; verify overlays stay aligned with the raw frame after zoom and navigation.
3. Independently measure first-contact frame, D0, U0, contact width, height, area and βmax for at least three distinct droplet events; compare the exported values and document tolerances.
4. Verify detection counts, matched identities, fragmented/merged contours and false objects in at least three reflective or low-contrast scenes.
5. Compare side-view 2D envelope descriptors with an agreed spray-geometry reference or rename to a nonphysical descriptor; never claim calibrated 3D cone angle without independent measurement.
6. Run pause → resume, cancel → restart, and repeated use of the analysis controls; verify no callbacks remain from an old session.
7. Export a table and verify all accompanying CSV/JSON files, units and metadata; confirm identical results when rerunning the same source video and configuration.
8. Record camera FPS, exposure, calibration uncertainty, pixel scale, compression/codec, and source-video hash; explicitly document operator and camera-plane limitations.

**Publication gate:** independent laboratory truth sets, bias and repeatability reports, confidence/uncertainty reporting, experimental scientist sign-off, and final Windows/Linux desktop acceptance remain mandatory. This is a **research preview**, not a certified measuring instrument.

## 6. Merge instructions for an existing modular checkout

The delivery is based on the supplied modular `Dropen3_Research_Linux_Dev5` snapshot.
The author's live `main` branch was not fetched, so recent unshared changes must be
reviewed before replacing files. In particular, the latest main-window design
excludes the `System Doctor` and `Fit` buttons, and this delivery preserves those
removals.

1. Create a feature branch and make a clean working-tree backup.
2. Apply the source-file patch over the project root (the directory containing
   `pyproject.toml`) after reviewing file differences.
3. Run `python -m pip install -e ".[test]"`, `python -m pytest -q`, and the
   dedicated coverage command in the README.
4. On Windows and Linux, run the actual desktop GUI and validate one reference
   video before merging into `main`.
5. Do not publish the new estimates as scientifically validated before the
   experimental acceptance criteria in section 5 are satisfied.

No changes have been pushed to the remote repository automatically.
