"""Regression tests for zooming back out without broken or shifted frames."""

import numpy as np
from PIL import Image

from dropen3.ui.rendering import render_viewport_image
from dropen3.ui.viewport import calculate_viewport, normalize_crop, scale_crop


def test_zoom_in_then_out_returns_to_full_frame():
    for width, height in ((1920, 1080), (3840, 2160), (641, 479), (100, 100)):
        cropped = scale_crop(width, height, None, 1.2)
        full = scale_crop(width, height, cropped, 1 / 1.2)
        assert full is None


def test_repeated_zoom_out_does_not_create_partial_full_axis_crop():
    width, height = 1600, 900
    cropped = (300, 100, 700, 600)
    for _ in range(30):
        cropped = scale_crop(width, height, cropped, 1 / 1.2)
        if cropped is None:
            break
        assert normalize_crop(width, height, cropped) == cropped
        x1, y1, x2, y2 = cropped
        assert x2 - x1 < width and y2 - y1 < height
    assert cropped is None


def test_render_size_is_fixed_at_all_zoom_levels():
    rng = np.random.default_rng(12345)
    rgb = Image.fromarray(rng.integers(0, 256, (120, 200, 3), dtype=np.uint8))
    cropped = None
    for factor in ([1.2] * 5 + [1 / 1.2] * 10):
        cropped = scale_crop(200, 120, cropped, factor, anchor=(100, 60))
        viewport = calculate_viewport(200, 120, 401, 301, cropped)
        output = render_viewport_image(rgb, viewport, 401, 301)
        assert output.size == (401, 301)
        assert viewport.to_image(
            viewport.offset_x + viewport.display_width / 2,
            viewport.offset_y + viewport.display_height / 2,
        ) is not None
    assert cropped is None


def test_full_frame_render_cannot_fragment_image():
    original = np.zeros((4, 8, 3), dtype=np.uint8)
    original[:, :4] = (255, 0, 0)
    original[:, 4:] = (0, 0, 255)
    frame = Image.fromarray(original)
    viewport = calculate_viewport(8, 4, 8, 8)
    result = render_viewport_image(frame, viewport, 8, 8)
    output = np.asarray(result)
    assert np.array_equal(output[2:6], original)
    assert (output[:2] == np.array((10, 10, 10))).all()
    assert (output[6:] == np.array((10, 10, 10))).all()


def test_half_pixel_letterbox_maps_to_actual_pasted_pixels():
    rgb = Image.new('RGB', (7, 3), (47, 129, 219))
    viewport = calculate_viewport(7, 3, 14, 11)
    preview = render_viewport_image(rgb, viewport, 14, 11)
    x, y = viewport.offset_x, viewport.offset_y
    assert preview.getpixel((x, y)) == (47, 129, 219)
    assert viewport.to_image(x, y) == (0, 0)
    assert preview.getpixel((x, max(0, y - 1))) == (10, 10, 10) if y > 0 else True


def test_viewer_roundtrip_restores_full_frame_and_preserves_source(monkeypatch):
    from dropen3.ui import viewer as viewer_module

    monkeypatch.setattr(viewer_module.ImageTk, 'PhotoImage', lambda image: image)

    class FakeLabel:
        def __init__(self):
            self.image = None
        def winfo_width(self):
            return 401
        def winfo_height(self):
            return 301
        def configure(self, **kwargs):
            self.image = kwargs['image']

    class Viewer(viewer_module.ViewerMixin):
        pass

    app = Viewer()
    app.canvas_view = FakeLabel()
    app.cap = None
    app.roi_zoom = None
    app.img_result_original = None
    app.current_frame_idx = 0
    original = np.random.default_rng(17).integers(0, 256, (120, 200, 3), dtype=np.uint8)
    app.display_frame(original)
    initial_preview = np.asarray(app.canvas_view.image).copy()
    app.apply_zoom(1.2)
    zoomed_preview = np.asarray(app.canvas_view.image).copy()
    assert initial_preview.shape == zoomed_preview.shape == (301, 401, 3)
    assert not np.array_equal(initial_preview, zoomed_preview)
    app.apply_zoom(1 / 1.2)
    assert app.roi_zoom is None
    assert np.array_equal(np.asarray(app.canvas_view.image), initial_preview)
    assert np.array_equal(app.img_result_original, original)


def test_viewer_repeated_zoom_out_leaves_full_frame_intact(monkeypatch):
    from dropen3.ui import viewer as viewer_module

    monkeypatch.setattr(viewer_module.ImageTk, 'PhotoImage', lambda image: image)

    class FakeLabel:
        image = None
        def winfo_width(self):
            return 400
        def winfo_height(self):
            return 300
        def configure(self, **kwargs):
            self.image = kwargs['image']

    class Viewer(viewer_module.ViewerMixin):
        pass

    app = Viewer()
    app.canvas_view = FakeLabel()
    app.cap = None
    app.roi_zoom = None
    app.img_result_original = None
    app.current_frame_idx = 0
    frame = np.zeros((90, 160, 3), dtype=np.uint8)
    frame[:, :80] = (255, 0, 0)
    frame[:, 80:] = (0, 0, 255)
    app.display_frame(frame)
    original_preview = np.asarray(app.canvas_view.image).copy()
    for _ in range(8):
        app.apply_zoom(1.2)
    for _ in range(20):
        app.apply_zoom(1 / 1.2)
        assert app.canvas_view.image.size == (400, 300)
    assert app.roi_zoom is None
    assert app.zoom_factor < 1.0
    # Zoom-out is now allowed below fit. Fit must reproduce the original preview.
    app.reset_zoom()
    assert np.array_equal(np.asarray(app.canvas_view.image), original_preview)
