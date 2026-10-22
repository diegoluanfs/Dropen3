"""Regression tests for zoom and source-pixel coordinate stability."""

import pytest
from dropen3.ui.viewport import calculate_viewport, scale_crop, normalize_crop


def test_letterbox_does_not_shift_pixel_coordinates():
    view = calculate_viewport(200, 100, 400, 400)
    assert view.display_width == 400
    assert view.display_height == 200
    assert view.offset_y == 100
    assert view.to_image(200, 200) == (100, 50)
    assert view.to_image(200, 99) is None
    assert view.to_image(200, 300) is None
    assert view.to_image(200, 300, clamp=True) == (100, 99)


def test_original_frame_mapping_is_stable_under_zoom():
    full = calculate_viewport(200, 100, 400, 300)
    original = full.to_image(200, 150)
    crop = scale_crop(200, 100, None, 2.0, original)
    zoomed = calculate_viewport(200, 100, 400, 300, crop)
    assert zoomed.to_image(200, 150) == original
    assert zoomed.crop == (50, 25, 150, 75)


def test_nested_roi_is_in_source_image_coordinates():
    selected = (40, 10, 140, 60)
    roi_view = calculate_viewport(200, 100, 400, 200, selected)
    assert roi_view.to_image(0, 0) == (40, 10)
    assert roi_view.to_image(399, 199) == (139, 59)
    inner = scale_crop(200, 100, selected, 2)
    assert inner == (65, 22, 115, 47)


def test_zoom_resets_to_full_frame_and_never_exceeds_bounds():
    assert scale_crop(200, 100, None, 0.5) is None
    assert scale_crop(200, 100, (10, 10, 190, 90), 0.1) is None
    crop = scale_crop(200, 100, None, 25, anchor=(199, 99))
    assert normalize_crop(200, 100, crop) == crop
    assert crop[2] == 200 and crop[3] == 100


def test_invalid_scale_and_outside_click():
    with pytest.raises(ValueError):
        scale_crop(100, 100, None, 0)
    assert calculate_viewport(100, 100, 400, 400).to_image(-1, 200) is None
