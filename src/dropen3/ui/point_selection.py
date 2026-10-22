"""Zoomable, pixel-accurate manual point selection in OpenCV windows.

The displayed image can be scaled and cropped, but all returned coordinates
refer to the *unaltered* input image. In particular, image resampling is never
used for the scientific calculations.
"""
from __future__ import annotations

import cv2
import numpy as np

from dropen3.ui.viewport import Viewport, calculate_viewport, scale_crop


def _wheel_delta(flags: int) -> int:
    """OpenCV encodes the signed Windows mouse-wheel delta in the upper word."""
    upper = (flags >> 16) & 0xFFFF
    return upper - 65536 if upper >= 32768 else upper


class ZoomablePointPicker:
    def __init__(self, frame: np.ndarray, number_of_points: int, title: str):
        if frame is None or frame.ndim not in (2, 3):
            raise ValueError('A valid image is required for point selection.')
        if number_of_points < 1:
            raise ValueError('At least one point must be requested.')
        self.frame = frame.copy()
        self.height, self.width = self.frame.shape[:2]
        self.window_width = min(1200, max(640, self.width))
        self.window_height = min(840, max(480, self.height))
        self.number_of_points = number_of_points
        self.title = title
        self.points: list[tuple[int, int]] = []
        self.crop: tuple[int, int, int, int] | None = None
        self.viewport: Viewport | None = None
        self.cursor: tuple[int, int] | None = None

    def on_mouse(self, event: int, x: int, y: int, flags: int, param=None):
        if self.viewport is None:
            return
        point = self.viewport.to_image(x, y)
        if event == cv2.EVENT_MOUSEWHEEL:
            delta = _wheel_delta(flags)
            if delta:
                self.zoom(1.25 if delta > 0 else 1 / 1.25, point)
        elif event == cv2.EVENT_MOUSEMOVE:
            self.cursor = point
        elif event == cv2.EVENT_LBUTTONDOWN and point is not None:
            if len(self.points) < self.number_of_points:
                self.points.append(point)
        elif event == cv2.EVENT_RBUTTONDOWN and self.points:
            self.points.pop()

    def zoom(self, factor: float, anchor: tuple[int, int] | None = None):
        self.crop = scale_crop(self.width, self.height, self.crop, factor, anchor)

    def draw(self) -> np.ndarray:
        """Render a preview with unchanged original-pixel point locations."""
        self.viewport = calculate_viewport(
            self.width, self.height, self.window_width, self.window_height, self.crop
        )
        base = cv2.cvtColor(self.frame, cv2.COLOR_GRAY2BGR) if self.frame.ndim == 2 else self.frame.copy()
        for i, point in enumerate(self.points):
            cv2.circle(base, point, 3, (0, 0, 255), -1)
            if i > 0:
                cv2.line(base, self.points[i - 1], point, (0, 255, 255), 1)
        x1, y1, x2, y2 = self.viewport.crop
        region = base[y1:y2, x1:x2]
        interpolation = cv2.INTER_NEAREST if self.viewport.display_width > x2 - x1 else cv2.INTER_AREA
        resized = cv2.resize(region, (self.viewport.display_width, self.viewport.display_height),
                             interpolation=interpolation)
        canvas = np.zeros((self.window_height, self.window_width, 3), dtype=np.uint8)
        off_x, off_y = round(self.viewport.offset_x), round(self.viewport.offset_y)
        canvas[off_y:off_y + self.viewport.display_height,
               off_x:off_x + self.viewport.display_width] = resized
        cv2.putText(canvas, 'Wheel/+/-: Zoom   0: Fit   Backspace/Right-click: Undo   Esc: Cancel',
                    (8, self.window_height - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                    (130, 210, 255), 1, cv2.LINE_AA)
        return canvas

    def select(self) -> list[tuple[int, int]] | None:
        cv2.namedWindow(self.title, cv2.WINDOW_AUTOSIZE)
        cv2.setMouseCallback(self.title, self.on_mouse)
        try:
            while True:
                cv2.imshow(self.title, self.draw())
                key = cv2.waitKeyEx(30)
                if len(self.points) >= self.number_of_points:
                    return self.points.copy()
                if key in (27,):
                    return None
                if key in (ord('+'), ord('=')):
                    self.zoom(1.25, self.cursor)
                elif key in (ord('-'), ord('_')):
                    self.zoom(1 / 1.25, self.cursor)
                elif key == ord('0'):
                    self.crop = None
                elif key in (8, 127, ord('r'), ord('R')) and self.points:
                    self.points.pop()
                # A window closed using its X button cancels point selection.
                if cv2.getWindowProperty(self.title, cv2.WND_PROP_VISIBLE) < 1:
                    return None
        finally:
            try:
                cv2.destroyWindow(self.title)
            except cv2.error:
                pass


def select_image_points(frame: np.ndarray, count: int, title: str) -> list[tuple[int, int]] | None:
    return ZoomablePointPicker(frame, count, title).select()


def select_video_points(
    capture: cv2.VideoCapture,
    initial_frame: int,
    count: int,
    title: str,
) -> tuple[int, list[tuple[int, int]]] | None:
    """Select original-pixel points with A/D frame navigation and zoom.

    Changing frames clears selected points so coordinates cannot silently mix
    measurements made on different images.
    """
    total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    if not capture.isOpened() or total < 1:
        return None

    def read_frame(index: int):
        capture.set(cv2.CAP_PROP_POS_FRAMES, index)
        success, frame = capture.read()
        return frame if success else None

    index = min(max(0, initial_frame), total - 1)
    frame = read_frame(index)
    if frame is None:
        return None
    picker = ZoomablePointPicker(frame, count, title)
    cv2.namedWindow(title, cv2.WINDOW_AUTOSIZE)
    cv2.setMouseCallback(title, picker.on_mouse)
    try:
        while True:
            preview = picker.draw()
            cv2.putText(preview, f'Frame: {index}/{total - 1} | A/D or arrows: navigate | Enter: confirm',
                        (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.50,
                        (130, 210, 255), 1, cv2.LINE_AA)
            cv2.imshow(title, preview)
            key = cv2.waitKeyEx(30)
            if key == 27:
                return None
            if key in (13, 10) and len(picker.points) == count:
                return index, picker.points.copy()
            increment = 0
            if key in (ord('a'), ord('A'), 2424832, 65361):
                increment = -1
            elif key in (ord('d'), ord('D'), 2555904, 65363):
                increment = 1
            if increment:
                destination = min(max(0, index + increment), total - 1)
                if destination != index:
                    next_frame = read_frame(destination)
                    if next_frame is not None:
                        index = destination
                        picker.frame = next_frame.copy()
                        picker.points.clear()
                        picker.cursor = None
                        picker.crop = None if next_frame.shape[:2] != frame.shape[:2] else picker.crop
                        frame = next_frame
            elif key in (ord('+'), ord('=')):
                picker.zoom(1.25, picker.cursor)
            elif key in (ord('-'), ord('_')):
                picker.zoom(1 / 1.25, picker.cursor)
            elif key == ord('0'):
                picker.crop = None
            elif key in (8, 127, ord('r'), ord('R')):
                picker.points.clear()
            if cv2.getWindowProperty(title, cv2.WND_PROP_VISIBLE) < 1:
                return None
    finally:
        try:
            cv2.destroyWindow(title)
        except cv2.error:
            pass
