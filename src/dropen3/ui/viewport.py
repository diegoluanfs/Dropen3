"""Pixel-exact mapping between a fitted viewer widget and the source image.

All rectangle coordinates use half-open original-image pixel bounds. Display
coordinates are allowed to be fractional because letterboxing creates offsets.
No scientific measurement should consume widget coordinates directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil


@dataclass(frozen=True)
class Viewport:
    """The displayed source crop and its fitted location within a widget."""

    crop: tuple[int, int, int, int]
    offset_x: float
    offset_y: float
    display_width: int
    display_height: int

    def to_image(self, x: float, y: float, *, clamp: bool = False) -> tuple[int, int] | None:
        left, top, right, bottom = self.crop
        fx = (x - self.offset_x) / self.display_width
        fy = (y - self.offset_y) / self.display_height
        if not clamp and not (0 <= fx < 1 and 0 <= fy < 1):
            return None
        fx = min(max(fx, 0.0), 1.0 - 1e-12)
        fy = min(max(fy, 0.0), 1.0 - 1e-12)
        return (
            min(right - 1, left + int(fx * (right - left))),
            min(bottom - 1, top + int(fy * (bottom - top))),
        )


def normalize_crop(
    image_width: int,
    image_height: int,
    crop: tuple[int, int, int, int] | None = None,
) -> tuple[int, int, int, int]:
    if image_width <= 0 or image_height <= 0:
        raise ValueError('Image dimensions must be positive.')
    if crop is None:
        return (0, 0, image_width, image_height)
    x1, y1, x2, y2 = crop
    x1 = max(0, min(image_width - 1, int(x1)))
    y1 = max(0, min(image_height - 1, int(y1)))
    x2 = min(image_width, max(x1 + 1, int(x2)))
    y2 = min(image_height, max(y1 + 1, int(y2)))
    return (x1, y1, x2, y2)


def calculate_viewport(
    image_width: int,
    image_height: int,
    widget_width: int,
    widget_height: int,
    crop: tuple[int, int, int, int] | None = None,
    *,
    display_scale: float = 1.0,
) -> Viewport:
    if widget_width <= 0 or widget_height <= 0:
        raise ValueError('Viewer dimensions must be positive.')
    if not (0 < display_scale <= 1):
        raise ValueError('Display scale must be in (0, 1].')
    bounds = normalize_crop(image_width, image_height, crop)
    x1, y1, x2, y2 = bounds
    ratio = min(widget_width / (x2 - x1), widget_height / (y2 - y1))
    display_width = max(1, min(widget_width, round((x2 - x1) * ratio * display_scale)))
    display_height = max(1, min(widget_height, round((y2 - y1) * ratio * display_scale)))
    return Viewport(
        crop=bounds,
        offset_x=(widget_width - display_width) // 2,
        offset_y=(widget_height - display_height) // 2,
        display_width=display_width,
        display_height=display_height,
    )


# Bounds prevent subpixel-sized crops at extreme magnification. The limit
# applies to the source image, never to scientific measurement coordinates.
MAX_CROP_MAGNIFICATION = 32.0

def scale_crop(
    image_width: int,
    image_height: int,
    crop: tuple[int, int, int, int] | None,
    factor: float,
    anchor: tuple[int, int] | None = None,
) -> tuple[int, int, int, int] | None:
    """Zoom around a source-image point, using half-open pixel bounds.

    The crop has a maximum magnification to keep the inspected region usable.
    Every zoom-out step strictly expands a cropped axis; rounding must never
    trap the viewer at a minimum-size rectangle.
    """
    if factor <= 0:
        raise ValueError('Zoom factor must be positive.')
    x1, y1, x2, y2 = normalize_crop(image_width, image_height, crop)
    old_width, old_height = x2 - x1, y2 - y1
    if factor > 1.0:
        minimum_width = min(image_width, max(2, ceil(image_width / MAX_CROP_MAGNIFICATION)))
        minimum_height = min(image_height, max(2, ceil(image_height / MAX_CROP_MAGNIFICATION)))
        # Do not enlarge an ROI drawn by hand that is smaller than this limit.
        new_width = min(old_width, max(minimum_width, round(old_width / factor)))
        new_height = min(old_height, max(minimum_height, round(old_height / factor)))
    elif factor < 1.0:
        # Integer rounding previously caused a 2 x 2 crop to remain 2 x 2
        # indefinitely, even when the user repeatedly pressed Zoom Out.
        new_width = min(image_width, max(old_width + 1, round(old_width / factor)))
        new_height = min(image_height, max(old_height + 1, round(old_height / factor)))
    else:
        return crop
    if new_width >= image_width and new_height >= image_height:
        return None
    if factor < 1.0 and (new_width >= image_width or new_height >= image_height):
        # Avoid partial-width/partial-height crops while returning to fit mode.
        return None
    anchor_x, anchor_y = anchor if anchor else ((x1 + x2) // 2, (y1 + y2) // 2)
    anchor_x = min(max(x1, int(anchor_x)), x2 - 1)
    anchor_y = min(max(y1, int(anchor_y)), y2 - 1)
    relative_x = (anchor_x - x1) / old_width
    relative_y = (anchor_y - y1) / old_height
    new_left = min(max(0, round(anchor_x - relative_x * new_width)), image_width - new_width)
    new_top = min(max(0, round(anchor_y - relative_y * new_height)), image_height - new_height)
    # Guarantee that the focal pixel remains *inside* half-open crop bounds.
    new_left = min(max(new_left, anchor_x - new_width + 1), anchor_x)
    new_top = min(max(new_top, anchor_y - new_height + 1), anchor_y)
    return (new_left, new_top, new_left + new_width, new_top + new_height)


MIN_DISPLAY_SCALE = 0.25


def step_zoom(
    image_width: int,
    image_height: int,
    crop: tuple[int, int, int, int] | None,
    display_scale: float,
    factor: float,
    anchor: tuple[int, int] | None = None,
) -> tuple[tuple[int, int, int, int] | None, float]:
    """Change zoom without conflating an image crop with display-only shrinkage.

    A full frame can be displayed smaller than its fit-to-window size. Zooming
    back in restores fit *before* beginning to crop the source image.
    All crop bounds remain in original-image coordinates.
    """
    if image_width <= 0 or image_height <= 0:
        raise ValueError('Image dimensions must be positive.')
    if not (0 < display_scale <= 1):
        raise ValueError('Display scale must be in (0, 1].')
    if factor <= 0:
        raise ValueError('Zoom factor must be positive.')
    if factor == 1.0:
        return crop, display_scale

    if crop is not None:
        # Existing zoomed selections always fill the viewer. Zooming out
        # towards fit does not shrink the preview until full-frame is reached.
        return scale_crop(image_width, image_height, crop, factor, anchor), 1.0

    candidate = display_scale * factor
    if candidate < 1.0:
        return None, max(MIN_DISPLAY_SCALE, candidate)
    if candidate <= 1.0 + 1e-9:
        return None, 1.0
    # If a zoom-in step crosses 100%, consume only the excess magnification.
    return scale_crop(image_width, image_height, None, candidate, anchor), 1.0
