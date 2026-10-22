# Dropen3 1.1.0.dev4 — Continuous Viewer Zoom

## Confirmed limitation addressed

In 1.1.0.dev3, `scale_crop` returned `None` whenever the zoomed view reached
full-frame dimensions. A `None` crop means a fitted image, so further zoom-out
commands could never make the image smaller. This behavior was mistaken for a
nonfunctional zoom-out button.

## Code changes

- `ui/viewport.py`: `calculate_viewport(..., display_scale=...)` supports a
  stable, centered image smaller than the fitted dimensions while maintaining
  correct pointer-to-source coordinate mapping. `step_zoom` models zoom states.
- `ui/viewer.py`: viewer uses `step_zoom` and retains its output as the original
  `roi_zoom` and display-only `zoom_factor`. Drag-selection returns to a fitted
  region and does not alter the source image.
- No changes to navigation key bindings or scientific analysis algorithms.

The viewer still uses a fixed-size preview to prevent GUI geometry feedback.

## Manual acceptance protocol

1. Import an image or video in the main Dropen3 viewer.
2. Press `-` without first pressing `+`. The entire frame should shrink while
   remaining centered in its preview. Further presses shrink to the minimum
   display scale (25% of fitted dimensions).
3. Press `+` to restore the size and continue pressing to magnify the frame.
4. Press `-` repeatedly from a magnified frame. The crop should grow, the full
   frame should return, and subsequent presses should shrink it further.
5. Press `Fit`. The preview should return to the default fitted frame.
6. Change frames with A/D and arrow keys at each zoom level. The zoom state
   should remain stable between frames.
7. Inspect the baseline/point-selection workflow and confirm saved point
   coordinates refer to source pixels, not rendered pixels.

## Verification performed

- Unit and regression suite: 52 passing tests.
- Native Tkinter photo widget smoke test under virtual display:
  initial width 480, first zoom-out width 400, zoom-in return width 480.
- CustomTkinter Windows GUI testing and real experimental data verification:
  **not performed in this environment**.
