"""Source-pixel marking tests; no physical GUI is opened."""
from types import SimpleNamespace

import cv2
import numpy as np

from dropen3.ui.point_selection import ZoomablePointPicker, select_video_points


def test_opencv_pointer_mapping_before_and_after_magnification():
    picker = ZoomablePointPicker(np.zeros((100, 200, 3), dtype=np.uint8), 2, 'Test')
    picker.draw()
    picker.on_mouse(cv2.EVENT_LBUTTONDOWN, 320, 240, 0)
    assert picker.points == [(100, 50)]
    picker.on_mouse(cv2.EVENT_MOUSEWHEEL, 320, 240, 120 << 16)
    picker.draw()
    picker.on_mouse(cv2.EVENT_LBUTTONDOWN, 320, 240, 0)
    assert picker.points == [(100, 50), (100, 50)]
    picker.on_mouse(cv2.EVENT_RBUTTONDOWN, 320, 240, 0)
    assert len(picker.points) == 1


def test_video_selector_clears_points_on_frame_change(monkeypatch):
    class FakeCapture:
        def __init__(self):
            self.index = 0
        def isOpened(self):
            return True
        def get(self, key):
            return 3
        def set(self, key, value):
            self.index = int(value)
        def read(self):
            return True, np.full((100, 200, 3), self.index, dtype=np.uint8)

    state = SimpleNamespace(callback=None, index=0)
    monkeypatch.setattr(cv2, 'namedWindow', lambda *args: None)
    monkeypatch.setattr(cv2, 'setMouseCallback', lambda name, callback: setattr(state, 'callback', callback))
    monkeypatch.setattr(cv2, 'imshow', lambda *args: None)
    monkeypatch.setattr(cv2, 'destroyWindow', lambda *args: None)
    monkeypatch.setattr(cv2, 'getWindowProperty', lambda *args: 1)
    def fake_key(delay):
        state.index += 1
        if state.index == 1:
            state.callback(cv2.EVENT_LBUTTONDOWN, 320, 240, 0, None)
            return ord('d')
        if state.index == 2:
            state.callback(cv2.EVENT_LBUTTONDOWN, 320, 240, 0, None)
            return -1
        if state.index == 3:
            state.callback(cv2.EVENT_LBUTTONDOWN, 340, 240, 0, None)
            return 13
        raise AssertionError('Point selection did not terminate.')
    monkeypatch.setattr(cv2, 'waitKeyEx', fake_key)
    index, points = select_video_points(FakeCapture(), 0, 2, 'Test video')
    assert index == 1
    assert points == [(100, 50), (106, 50)]
