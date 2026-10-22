# Research Verification and Limitations

## Source traceability

Refactoring is based on the user-supplied 5,629-line `Dropen3 (1).py` and the manuscript *Dropen3 an open source graphical application for contact angle and droplet impact analysis* (dated 15 October 2026). The original source is preserved separately by the user; this project does not replace it. The manuscript describes demonstration data, **not** a completed quantitative benchmark.

## What is actually verified in this delivery

- Python modules parse and compile.
- Unit-tested reference calculations for Re, We, Oh and their mathematical relationship, timing of skipped frames, contact width, beta and user-supplied advancing/receding hysteresis.
- Contour helper behavior on small synthetic inputs.
- Bundled resource signatures and system doctor output.
- Basic structural separation of GUI methods into research workflows.

## Scientific and practical release blockers

1. **GUI workflow acceptance:** Exercise each static/advancing/receding/impact/spray menu, region/baseline selection, pause/reset, plots, numerical export and image saving with actual recordings. In the authoring environment CustomTkinter could not be installed, so a genuine GUI smoke test was not completed.
2. **Impact timing:** Review all existing `frame_id * dt` paths. Store original source frame indices, confirmed first-contact frame, and actual camera acquisition FPS. Playback FPS is not acquisition FPS.
3. **Contact width:** Several legacy methods use extreme points of the droplet's silhouette or convex hull. This is **not necessarily contact width on the substrate**, particularly during recoiling and overhangs. Do not label all such outputs as measured wetted diameter.
4. **Pre-impact parameters:** Diameter estimation depends on contour/ellipse selection and a valid spatial calibration. Check reference frames and camera perspective. Do not substitute a fabricated default diameter into physical quantities.
5. **Angle estimation:** Angle quadrant and near-vertical interfaces should be benchmarked on analytical circles, ellipses, noise and experimental standards, with both left and right independently checked. Weighted fits must report degree and window selection.
6. **Contact-angle hysteresis:** Identifying advancing and receding events requires contact-line motion and angle evolution under the specified protocol; maximum-minus-minimum angles on arbitrary videos can be misleading.
7. **Statistics and uncertainty:** Record expected-versus-predicted bias, absolute error, standard deviation, measurement repeatability, operator variation, frame failure rate and uncertainty from calibration, segmentation, background and timestamp choice.
8. **Reproducibility:** Exports currently focus on tables and images. Expand outputs to include complete calibration values, original frame IDs, segmentation/fit settings, camera and video codec metadata, scientific units, source file hashes and software version.
9. **Delivery:** Windows build, bundled DLLs, GUI fonts, native OpenCV HighGUI windows, supported codecs and clean-machine antivirus checks must be validated on real consumer PCs. The Doctor console persistence was unit-tested in Python but still requires a Windows Explorer double-click acceptance test on the final frozen build.
10. **Manuscript statements:** Do not imply that unimplemented recoil/contact-time outcome classifiers are validated. Document license, repository, data availability and external instruments before publication.

## Proposed acceptance criteria

- At least one independent synthetic reference and one experimental reference per contact-angle fitting method.
- Pre-impact diameter, velocity, time-of-first-contact, spreading diameter, height, projected area and dimensionless numbers checked against independently measured ground truth.
- Dataset grouped by independent droplets (not merely adjacent frames) and by surface and recording conditions.
- Automated integration smoke run on Windows with sample MP4 and AVI captures; compare exported results with approved reference tables within an explicit, scientifically justified tolerance.
- Code review by the scientific authors and a reproducible versioned archival release.

Until those conditions are met, designate the executable **research preview / not validated for quantitative publication**.

## Data provenance sidecar

Numerical CSV/XLSX/TXT exports now write a sibling file with suffix `.metadata.json` containing the method identifier, available calibration/settings, software version, export timestamp, row count, and input file metadata. For source videos up to 64 MiB, the file SHA-256 is included; for larger input files it is explicitly not computed in the GUI to avoid blocking high-speed video analysis. This improves traceability but does **not** replace a complete validated measurement protocol. Analysts should record all missing acquisition metadata independently.
