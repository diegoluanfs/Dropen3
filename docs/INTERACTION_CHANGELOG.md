# Interaction Fixes — 1.1.0.dev2

## Changed

- Restored A/D and Left/Right frame navigation in the main Tk interface.
- Paused automatic playback when stepping frames manually.
- Synced frame slider with original frame indices (rather than post-read OpenCV indices).
- Removed duplicate mouse-wheel event binding.
- Added explicit source-pixel-to-widget mapping for centered, aspect-ratio-preserving image display.
- Added nested drag-to-zoom, wheel zoom anchored near the cursor, zoom fit/reset, and a magnifier.
- Reused original-frame pixel coordinates when displaying cropped/zoomed images.
- Added zoomable baseline and three-point picking for static contact-angle and hysteresis workflows.
- Added zoomable, frame-navigable baseline point picking for impact and spray workflows.
- Preserved existing scientific analysis equations; only interaction, preview rendering, and point collection changed.
- Added regression tests and a Windows-specific manual test checklist.

## Not independently verified

- Actual interaction with CustomTkinter on Windows (GUI dependency unavailable in the build workspace).
- Compatibility of specific experimental video codecs and camera drivers.
- Numerical agreement with approved benchmark datasets and instruments.
- The optional legacy impact manual-line selector, currently not referenced by the provided workflows.

## Rollback

Keep the original `Dropen3_Research_DoctorFix.zip` archive. For targeted code review,
compare this release with that source archive. This development release is not a
peer-reviewed or experimentally validated scientific release.
