# Zoom-Out Regression Fix — 1.1.0.dev3

## Symptom

After zooming in, using the zoom-out button could disrupt the displayed video frame. The A/D and left/right navigation shortcuts were working and are unchanged.

## Changes

1. Render every preview on a constant-size image canvas (letterbox and zoom are computed separately), preventing changing image dimensions from influencing widget geometry.
2. Use a direct Tk photo for the preview to avoid secondary scaling by `CTkImage` on high-DPI screens. Preserve Lanczos for preview resampling; measurement pixel data remain untouched.
3. Disable `center_stack` geometry propagation, preventing feedback between image size and window layout.
4. Make button zoom-out the exact inverse of zoom-in (`1 / 1.2`).
5. Return directly to full-frame fit when zooming out would saturate either image dimension, avoiding partial full-width or full-height crops.
6. Align integer letterbox offsets with the actual placement of source pixels.
7. Add deterministic regression tests for inverse zoom, repeated zoom-out and unfragmented rendering.

## Testing limitations

Automated rendering and geometry tests can verify that pixel crops stay valid and frames render without disjoint pieces. Final verification of the real CustomTkinter widget on the user's Windows installation remains necessary; the current environment does not include CustomTkinter.

## Manual verification

Run `python -m dropen3 gui` inside an editable install or ` .\.venv\Scripts\python.exe -m dropen3 gui` from the project root on Windows. Load an image/video, zoom in several times, zoom out via button and wheel, use Fit, and step frames with A/D and arrows. Confirm the image does not shift, stretch or split; repeat at Windows display scales of 100% and 125% if available.
