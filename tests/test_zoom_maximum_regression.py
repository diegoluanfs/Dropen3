"""Regression tests for zoom-out recovery after hitting maximum magnification."""

import numpy as np
import cv2

from dropen3.ui.point_selection import ZoomablePointPicker
from dropen3.ui.viewport import (
    MAX_CROP_MAGNIFICATION,
    calculate_viewport,
    normalize_crop,
    scale_crop,
    step_zoom,
)


def dimensions(crop):
    return crop[2] - crop[0], crop[3] - crop[1]


def test_reaches_maximum_magnification_and_first_zoom_out_expands():
    """Previously the 2 x 2 crop was stuck indefinitely due to rounding."""
    for width, height in [(1920, 1080), (640, 480), (160, 90), (32, 32)]:
        crop = None
        for _ in range(150):
            next_crop = scale_crop(width, height, crop, 1.2)
            if next_crop == crop:
                break
            crop = next_crop
        else:
            raise AssertionError('Zoom-in failed to reach the configured maximum.')
        assert crop is not None
        cw, ch = dimensions(crop)
        assert cw >= min(width, max(2, np.ceil(width / MAX_CROP_MAGNIFICATION)))
        assert ch >= min(height, max(2, np.ceil(height / MAX_CROP_MAGNIFICATION)))
        zoomed_out = scale_crop(width, height, crop, 1 / 1.2)
        assert zoomed_out is None or all(a > b for a, b in zip(dimensions(zoomed_out), (cw, ch)))


def test_many_out_steps_recover_full_frame_even_from_tiny_manual_roi():
    for width, height in [(1920, 1080), (300, 200), (6, 4), (3, 3)]:
        for anchor in [(width // 2, height // 2), (width - 1, height - 1), (0, 0)]:
            crop = scale_crop(width, height, None, 64, anchor)
            if crop is None:
                continue
            for _ in range(250):
                previous = crop
                crop = scale_crop(width, height, crop, 1 / 1.2, anchor)
                if crop is None:
                    break
                assert crop != previous
                assert dimensions(crop)[0] > dimensions(previous)[0]
                assert dimensions(crop)[1] > dimensions(previous)[1]
                assert normalize_crop(width, height, crop) == crop
            assert crop is None


def test_main_viewer_zoom_state_recovers_from_limit_and_minimum():
    crop, scale = None, 1.0
    for _ in range(100):
        crop, scale = step_zoom(640, 480, crop, scale, 1.2, (320, 240))
    assert crop is not None and scale == 1.0
    previous = crop
    crop, scale = step_zoom(640, 480, crop, scale, 1 / 1.2, (320, 240))
    assert crop != previous
    for _ in range(150):
        crop, scale = step_zoom(640, 480, crop, scale, 1 / 1.2, (320, 240))
    assert crop is None
    assert scale == 0.25
    crop, scale = step_zoom(640, 480, crop, scale, 1.2)
    assert crop is None and scale > 0.25


def test_opencv_point_picker_unsticks_at_max_and_keeps_source_coordinates():
    frame = np.zeros((90, 160, 3), dtype=np.uint8)
    picker = ZoomablePointPicker(frame, 2, 'Point picker')
    anchor = (80, 45)
    for _ in range(80):
        picker.zoom(1.25, anchor)
    maximum = picker.crop
    assert maximum is not None
    picker.zoom(1 / 1.25, anchor)
    assert picker.crop != maximum
    for _ in range(100):
        picker.zoom(1 / 1.25, anchor)
    assert picker.crop is None
    picker.draw()
    v = picker.viewport
    assert v.to_image(v.offset_x + v.display_width / 2, v.offset_y + v.display_height / 2) == anchor
    # Keep the original frame unchanged even when rendering a magnified region.
    assert np.array_equal(picker.frame, frame)


def test_small_manual_roi_zoom_in_cannot_enlarge_crop():
    crop = (50, 50, 52, 52)
    # This manually selected crop is smaller than the standard maximum zoom.
    assert scale_crop(640, 480, crop, 1.2) == crop
    assert dimensions(scale_crop(640, 480, crop, 1 / 1.2)) == (3, 3)


def test_zoomed_crop_preserves_pixel_mapping_near_edges():
    for anchor in [(0, 0), (639, 479)]:
        crop = None
        for _ in range(100):
            crop = scale_crop(640, 480, crop, 1.2, anchor)
        view = calculate_viewport(640, 480, 600, 400, crop)
        # The focal pixel stays inside the crop, including near image edges.
        assert crop[0] <= anchor[0] < crop[2]
        assert crop[1] <= anchor[1] < crop[3]
        sx = view.offset_x + (anchor[0] - crop[0] + 0.5) / (crop[2] - crop[0]) * view.display_width
        sy = view.offset_y + (anchor[1] - crop[1] + 0.5) / (crop[3] - crop[1]) * view.display_height
        assert view.to_image(sx, sy) == anchor
