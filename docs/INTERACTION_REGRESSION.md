# Keyboard Navigation and Zoom Regression Verification

## Scope

This development change restores frame navigation in the main application,
replaces inconsistent widget-to-image zoom arithmetic with an explicit viewport
transform, and adds zoomable original-pixel point selection for contact-angle,
hysteresis, droplet-impact, and spray baseline dialogs.

It intentionally does not change segmentation, contact-angle fitting,
calibration, dimensionless groups, or other scientific equations.

## Main viewer manual verification

1. Load a known multi-frame video. Verify the initial frame label is `Frame: 0 / N-1`.
2. Press `D` or `Right`. Verify one frame is advanced and the slider follows.
3. Press `A` or `Left`. Verify one frame is reversed.
4. Start playback, then press an arrow key. Verify playback pauses and one step is applied.
5. Check boundaries: no step below frame zero or beyond frame N-1.
6. Zoom with the mouse wheel. Verify the image region under the pointer remains under the pointer as closely as pixel quantization allows.
7. Drag on the displayed image to zoom into an area. Repeat the selection while zoomed.
8. Press `Fit` to return to the whole image; zoom should not discard annotations.
9. Move between frames while zoomed; verify the same original-pixel crop is applied to each frame.
10. Verify that a focused text input still accepts letters and editing keys without navigation.

## Point selection manual verification

1. Open an analysis requiring a baseline or contact point selection.
2. Zoom using the mouse wheel or `+` / `-` in the point-selection window.
3. Click the original image's known positions and verify the annotations appear exactly at the clicked region.
4. Use right-click or Backspace to undo, `0` to fit, `Escape` to cancel.
5. For video baseline selection, navigate frames with A/D or Left/Right. Confirm that existing points are cleared when moving to a new frame, so no mixed-frame baseline is stored.
6. Click both baseline points and press Enter to confirm the video selection.
7. Run identical measurements with zoom off and on and compare exported original-pixel coordinates and result values.

**Note:** In the main viewer, dragging selects a *view crop*, not a scientific ROI. Scientific marker selection occurs in the zoomable analysis dialogs. For static images, the initial `cv2.selectROI` window remains an original-resolution ROI selector; its selected region is subsequently passed to the zoomable baseline/three-point dialog.

## Automated verification

From the project directory:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m dropen3 gui
```

`tests/test_viewport.py` checks letterboxing, pixel mapping, nested crop scaling,
and bounds. `tests/test_point_selection.py` checks zoomed OpenCV click mapping
and video frame-change point resetting without opening a physical display.
`tests/test_keyboard_navigation.py` checks shortcut registration, direction,
pausing before navigation, and text-input focus exclusions.

## Qualification

Passing unit tests does not establish scientific measurement accuracy, codec
compatibility, or successful integration on a particular Windows desktop. These
checks require a Windows GUI acceptance run using actual experimental files.
Record test data versions, program version, baseline coordinates, calibration,
expected measurements, measured error, and operator identity where appropriate.
