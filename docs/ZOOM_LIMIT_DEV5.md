# Maximum Zoom Limit and Zoom-Out Recovery — 1.1.0.dev5

## Root cause

The prior `scale_crop()` could reduce the region to 2 x 2 source pixels. At
that size, a 1 / 1.2 zoom-out factor rounded both dimensions to 2. This
repeatedly returned an identical crop, appearing as an unresponsive Zoom Out
button after reaching maximum Zoom In.

## Changes

- The normal zoom-in limit is now 32x relative to the image size (instead of
  allowing a 2 x 2 region for ordinary frames).
- Zooming out guarantees that each cropped dimension grows by at least one
  original-image pixel, even on very small or manually chosen ROIs.
- The OpenCV point picker shares the corrected zoom-crop calculation.
- The Fit and below-fit display reduction from dev4 remain unchanged.
- Navigation, measurement routines, frame pixel values, and calibration inputs
  are unchanged.

## Windows acceptance procedure

1. Open a real experimental video and advance to a frame with a visible drop.
2. Repeatedly click Zoom In until the view stops increasing in magnification.
3. Click Zoom Out once: the image must immediately show a larger area.
4. Continue Zoom Out: reach Fit, then a smaller-than-fit preview.
5. Click Fit, then zoom in using the mouse wheel with the cursor near each
   corner, and zoom out again.
6. Repeat inside a manual point-selection window using the wheel and `+`/`-`.
7. Check A/D and Left/Right Arrow frame navigation at the zoom limit.
8. Confirm saved measurement points still refer to the source frame pixels.

All source code, comments, messages, and document updates are in English.
Automated boundary testing does not replace a GUI check on Windows or
scientific verification using validated experimental reference material.
