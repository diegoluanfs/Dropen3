"""Regression coverage for below-fit zoom and its interactive transitions."""

import math

import numpy as np
from PIL import Image

from dropen3.ui.viewport import MIN_DISPLAY_SCALE, calculate_viewport, step_zoom
from dropen3.ui.rendering import render_viewport_image


def test_zoom_out_from_fit_decreases_displayed_frame_size():
    crop, scale = step_zoom(1920, 1080, None, 1.0, 1 / 1.2)
    assert crop is None
    assert math.isclose(scale, 1 / 1.2)
    full = calculate_viewport(1920, 1080, 800, 600)
    smaller = calculate_viewport(1920, 1080, 800, 600, crop, display_scale=scale)
    assert smaller.display_width < full.display_width
    assert smaller.display_height < full.display_height
    assert smaller.offset_x > full.offset_x
    assert smaller.offset_y > full.offset_y


def test_further_zoom_out_stops_at_minimum_scale():
    crop, scale = None, 1.0
    for _ in range(30):
        crop, scale = step_zoom(1280, 720, crop, scale, 1 / 1.2)
    assert crop is None
    assert scale == MIN_DISPLAY_SCALE
    crop, scale = step_zoom(1280, 720, crop, scale, 1 / 1.2)
    assert crop is None and scale == MIN_DISPLAY_SCALE


def test_zoom_out_then_zoom_in_restores_fit_without_crop():
    crop, scale = step_zoom(1280, 720, None, 1.0, 1 / 1.2)
    crop, scale = step_zoom(1280, 720, crop, scale, 1.2)
    assert crop is None
    assert math.isclose(scale, 1.0)
    crop, scale = step_zoom(1280, 720, crop, scale, 1.2)
    assert crop is not None
    assert scale == 1.0


def test_pasted_frame_and_pointer_mapping_for_shrunken_frame():
    pixels = np.zeros((60, 120, 3), dtype=np.uint8)
    pixels[:, :60] = (0, 128, 250)
    pixels[:, 60:] = (220, 40, 80)
    image = Image.fromarray(pixels)
    viewport = calculate_viewport(120, 60, 500, 400, display_scale=0.5)
    preview = render_viewport_image(image, viewport, 500, 400)
    x, y = viewport.offset_x, viewport.offset_y
    assert viewport.to_image(x + viewport.display_width / 4, y + viewport.display_height / 2)[0] < 60
    assert viewport.to_image(x + viewport.display_width * 3 / 4, y + viewport.display_height / 2)[0] >= 60
    assert preview.getpixel((0, 0)) == (10, 10, 10)
    assert preview.getpixel((x + 5, y + viewport.display_height // 2))[0] == 0
    assert preview.size == (500, 400)
    assert np.array_equal(np.asarray(image), pixels)


def test_zoom_from_a_cropped_frame_restores_fit_then_shrinks():
    crop = None
    scale = 1.0
    for _ in range(3):
        crop, scale = step_zoom(640, 480, crop, scale, 1.2)
    assert crop is not None
    for _ in range(4):
        crop, scale = step_zoom(640, 480, crop, scale, 1 / 1.2)
    assert crop is None
    assert scale < 1.0


def test_display_dimension_rejects_invalid_scale():
    import pytest
    with pytest.raises(ValueError, match='Display scale'):
        calculate_viewport(100, 100, 200, 200, display_scale=0)
    with pytest.raises(ValueError, match='Display scale'):
        calculate_viewport(100, 100, 200, 200, display_scale=1.1)


def test_viewer_buttons_zoom_below_fit_and_fit_returns_original(monkeypatch):
    from dropen3.ui import viewer as module
    monkeypatch.setattr(module.ImageTk, 'PhotoImage', lambda image: image)

    class FakeLabel:
        def __init__(self):
            self.image = None
        def winfo_width(self):
            return 480
        def winfo_height(self):
            return 360
        def configure(self, **kwargs):
            self.image = kwargs['image']

    class Viewer(module.ViewerMixin):
        pass

    app = Viewer()
    app.canvas_view = FakeLabel()
    app.cap = None
    app.roi_zoom = None
    app.zoom_factor = 1.0
    app.img_result_original = None
    app.current_frame_idx = 0
    original = np.random.default_rng(83).integers(0, 256, (120, 240, 3), dtype=np.uint8)
    app.display_frame(original)
    before = np.asarray(app.canvas_view.image).copy()
    app.apply_zoom(1 / 1.2)
    after = np.asarray(app.canvas_view.image).copy()
    assert app.zoom_factor < 1
    assert app.roi_zoom is None
    assert not np.array_equal(before, after)
    assert after.shape == before.shape
    assert app.viewer_viewport.display_width < 480
    app.apply_zoom(1.2)
    assert app.roi_zoom is None
    assert math.isclose(app.zoom_factor, 1.0)
    assert np.array_equal(np.asarray(app.canvas_view.image), before)
    app.apply_zoom(1.2)
    assert app.roi_zoom is not None
    app.reset_zoom()
    assert app.roi_zoom is None
    assert app.zoom_factor == 1.0
    assert np.array_equal(np.asarray(app.canvas_view.image), before)
    assert np.array_equal(app.img_result_original, original)
