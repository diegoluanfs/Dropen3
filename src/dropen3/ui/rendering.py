"""Deterministic, geometry-stable preview rendering.

The image is always drawn onto a canvas of the same dimensions as the viewer.
Letterbox offsets are shared with :mod:`dropen3.ui.viewport`, preserving
source-pixel coordinate mapping after any number of zoom operations.
"""

from __future__ import annotations

from PIL import Image

from dropen3.ui.viewport import Viewport


def render_viewport_image(
    source: Image.Image,
    viewport: Viewport,
    canvas_width: int,
    canvas_height: int,
    background: tuple[int, int, int] = (10, 10, 10),
) -> Image.Image:
    """Return a fixed-size RGB preview; never mutate scientific source pixels."""
    if canvas_width <= 0 or canvas_height <= 0:
        raise ValueError("Canvas dimensions must be positive.")
    if viewport.display_width > canvas_width or viewport.display_height > canvas_height:
        raise ValueError("Viewport exceeds the target canvas.")
    if source.mode != "RGB":
        source = source.convert("RGB")
    region = source.crop(viewport.crop)
    target_size = (viewport.display_width, viewport.display_height)
    if region.size != target_size:
        # This resampling is display-only; analysis uses original source pixels.
        # Retain the previous CTkImage preview's Lanczos interpolation style.
        region = region.resize(target_size, resample=Image.Resampling.LANCZOS)
    output = Image.new("RGB", (canvas_width, canvas_height), background)
    output.paste(region, (int(viewport.offset_x), int(viewport.offset_y)))
    return output
