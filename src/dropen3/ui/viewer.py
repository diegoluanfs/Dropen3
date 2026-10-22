from __future__ import annotations
import os
import cv2
import numpy as np
import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
from PIL import Image
from PIL import ImageTk
from dropen3.ui.viewport import calculate_viewport, step_zoom
from dropen3.ui.rendering import render_viewport_image


class ViewerMixin:

    def edge_detection(self):
        if self.img_result_original is None:
            messagebox.showwarning('Warning', 'Upload an image first!')
            return
        self.show_edges = not self.show_edges
        gray = cv2.cvtColor(self.img_result_original, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        v = np.median(blur)
        lower = int(max(0, (1.0 - 0.33) * v))
        upper = int(min(255, (1.0 + 0.33) * v))
        edged = cv2.Canny(blur, lower, upper)
        kernel = np.ones((3, 3), np.uint8)
        edged = cv2.dilate(edged, kernel, iterations=1)
        result_vis = self.img_result_original.copy()
        contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        if contours:
            c_max = max(contours, key=cv2.contourArea)
            cv2.drawContours(result_vis, [c_max], -1, (0, 255, 0), 2)
            self.current_contour = c_max
            self.display_frame(result_vis, update_original=False)
            self.lbl_status.configure(text='Edges successfully detected.')
        else:
            self.lbl_status.configure(text='No outline found.')
            self.display_frame(self.img_result_original, update_original=False)
            self.lbl_status.configure(text='Border Preview: DISABLED')

    def apply_zoom(self, factor, anchor=None):
        """Zoom the current image view without changing measurement coordinates."""
        if self.img_result_original is None:
            return
        image_height, image_width = self.img_result_original.shape[:2]
        self.roi_zoom, self.zoom_factor = step_zoom(
            image_width, image_height, self.roi_zoom,
            getattr(self, 'zoom_factor', 1.0), factor, anchor,
        )
        self.display_frame(getattr(self, 'display_source', self.img_result_original), update_original=False)

    def reset_zoom(self):
        self.roi_zoom = None
        self.zoom_factor = 1.0
        if self.img_result_original is not None:
            self.display_frame(getattr(self, 'display_source', self.img_result_original), update_original=False)

    def on_mouse_wheel(self, event):
        if self.img_result_original is None:
            return
        anchor = self.viewer_viewport.to_image(event.x, event.y) if self.viewer_viewport else None
        delta = getattr(event, 'delta', 0)
        if delta > 0 or getattr(event, 'num', 0) == 4:
            self.apply_zoom(1.2, anchor)
        elif delta < 0 or getattr(event, 'num', 0) == 5:
            self.apply_zoom(1 / 1.2, anchor)
        return 'break'

    def on_viewer_resize(self, event=None):
        """Debounce resize so fitted image and pointer mapping agree."""
        pending = getattr(self, '_viewer_resize_pending', None)
        if pending is not None:
            self.after_cancel(pending)
        self._viewer_resize_pending = self.after(80, self._refresh_viewer_size)

    def _refresh_viewer_size(self):
        self._viewer_resize_pending = None
        if self.img_result_original is not None:
            self.display_frame(getattr(self, 'display_source', self.img_result_original), update_original=False)

    def on_click_press(self, event):
        self.dragging = (self.img_result_original is not None and self.viewer_viewport is not None
                         and self.viewer_viewport.to_image(event.x, event.y) is not None)
        if self.dragging:
            self.start_x, self.start_y = event.x, event.y

    def on_mouse_drag(self, event):
        # The original-image coordinates are computed at release, not during drag.
        return None

    def on_click_release(self, event):
        if not getattr(self, 'dragging', False):
            return
        self.dragging = False
        if self.img_result_original is None or self.viewer_viewport is None:
            return
        if abs(event.x - self.start_x) < 10 or abs(event.y - self.start_y) < 10:
            return
        viewport = self.viewer_viewport
        p1 = viewport.to_image(self.start_x, self.start_y, clamp=True)
        p2 = viewport.to_image(event.x, event.y, clamp=True)
        if p1 is None or p2 is None:
            return
        image_height, image_width = self.img_result_original.shape[:2]
        x1, x2 = sorted((p1[0], p2[0]))
        y1, y2 = sorted((p1[1], p2[1]))
        if x2 - x1 < 2 or y2 - y1 < 2:
            return
        self.roi_zoom = (x1, y1, min(image_width, x2 + 1), min(image_height, y2 + 1))
        self.zoom_factor = 1.0
        self.update_zoom_view()

    def toggle_zoom_hover(self):
        self.zoom_hover_enabled = not self.zoom_hover_enabled
        if self.zoom_hover_enabled:
            self.btn_toggle_zoom.configure(text='🔍 Hover: ON', fg_color='#28a745')
            self.lbl_status.configure(text='Magnifier enabled. Hold the pointer over the frame.')
        else:
            self.btn_toggle_zoom.configure(text='🔍 Hover: OFF', fg_color='#444444')
            self.hide_zoom_window()
            self.lbl_status.configure(text='Magnifier disabled.')

    def update_zoom_view(self, is_roi=False):
        if self.img_result_original is not None:
            self.display_frame(getattr(self, 'display_source', self.img_result_original), update_original=False)

    def display_frame(self, frame, update_original=True):
        if frame is None:
            return
        if update_original:
            self.img_result_original = frame.copy()
        self.display_source = frame.copy()
        # Read-only display zoom: image processing always keeps original pixels.
        height, width = frame.shape[:2]
        canvas_width = self.canvas_view.winfo_width()
        canvas_height = self.canvas_view.winfo_height()
        if canvas_width <= 10 or canvas_height <= 10:
            canvas_width = max(400, self.winfo_width() - 320)
            canvas_height = max(300, self.winfo_height() - 280)
        viewport = calculate_viewport(
            width, height, canvas_width, canvas_height, self.roi_zoom,
            display_scale=(getattr(self, 'zoom_factor', 1.0) if self.roi_zoom is None else 1.0),
        )
        self.viewer_viewport = viewport
        x1, y1, x2, y2 = viewport.crop
        cropped = frame[y1:y2, x1:x2]
        self.current_vis_img = cropped.copy()
        # A fixed-size preview prevents CTkLabel from changing its requested
        # geometry between zoom levels. Direct Tk photos are also pixel-sized,
        # avoiding additional DPI scaling by CTkImage.
        rgb_frame = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        preview = render_viewport_image(rgb_frame, viewport, canvas_width, canvas_height)
        photo = ImageTk.PhotoImage(preview)
        self.canvas_view.configure(image=photo, text='')
        self.canvas_view.image = photo
        if self.cap is not None and hasattr(self, 'video_slider_var'):
            self.video_slider_var.set(self.current_frame_idx)

    def on_slider_move(self, value):
        if self.cap is None or not self.cap.isOpened():
            return
        self.stop_video()
        destination = max(0, min(int(float(value)), self.total_frames - 1))
        self.current_frame_idx = destination
        self.show_frame()

    def on_mouse_move(self, event):
        if not self.zoom_hover_enabled or self.img_result_original is None:
            return
        if self.viewer_viewport is None:
            return
        pixel = self.viewer_viewport.to_image(event.x, event.y)
        if pixel is None:
            self.hide_zoom_window()
            return
        raw_x, raw_y = pixel
        image = self.img_result_original
        original_height, original_width = image.shape[:2]
        patch_size = max(4, int(self.zoom_window_size / self.magnification))
        x1 = max(0, min(raw_x - patch_size // 2, original_width - patch_size))
        y1 = max(0, min(raw_y - patch_size // 2, original_height - patch_size))
        crop = image[y1:min(original_height, y1 + patch_size), x1:min(original_width, x1 + patch_size)]
        if crop.size == 0:
            return
        enlarged = cv2.resize(crop, (self.zoom_window_size, self.zoom_window_size),
                              interpolation=cv2.INTER_NEAREST)
        # Crosshair aligns with the mapped source pixel.
        cross_x = round((raw_x - x1 + .5) * self.zoom_window_size / crop.shape[1])
        cross_y = round((raw_y - y1 + .5) * self.zoom_window_size / crop.shape[0])
        cv2.line(enlarged, (cross_x, 0), (cross_x, self.zoom_window_size - 1), (0, 255, 255), 1)
        cv2.line(enlarged, (0, cross_y), (self.zoom_window_size - 1, cross_y), (0, 255, 255), 1)
        photo = ImageTk.PhotoImage(Image.fromarray(cv2.cvtColor(enlarged, cv2.COLOR_BGR2RGB)))
        if self.zoom_label is None:
            self.zoom_label = tk.Label(self.canvas_view, bd=1, relief='solid')
        self.zoom_label.configure(image=photo)
        self.zoom_label.image = photo
        # Keep the magnifier in a corner so it does not intercept pointing gestures.
        self.zoom_label.place(x=max(0, self.canvas_view.winfo_width() - self.zoom_window_size - 12), y=12)
        self.zoom_label.lift()

    def hide_zoom_window(self, event=None):
        if self.zoom_label is not None:
            self.zoom_label.destroy()
            self.zoom_label = None

    def load_media(self):
        path = filedialog.askopenfilename(title='Select Media', filetypes=[('Videos', '*.avi *.mp4 *.mkv *.mov'), ('Images', '*.jpg *.png *.jpeg *.bmp')])
        if not path:
            return
        self.stop_video()
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.img_result_original = None
        self.zoom_factor = 1.0
        self.roi_zoom = None
        self.viewer_viewport = None
        self.display_source = None
        self.total_frames = 0
        self.current_frame_idx = 0
        if path.lower().endswith(('.jpg', '.png', '.jpeg', '.bmp')):
            self.cap = None
            frame = cv2.imread(path)
            if frame is not None:
                self.display_frame(frame)
                self.lbl_status.configure(text=f'Image: {os.path.basename(path)}')
        else:
            self.cap = cv2.VideoCapture(path)
            if self.cap.isOpened():
                self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
                self.current_frame_idx = 0
                self.video_slider.configure(to=max(1, self.total_frames - 1))
                self.show_frame()
                self.lbl_status.configure(text=f'Video: {os.path.basename(path)}')
            else:
                messagebox.showerror('Error', 'Unable to open the video file.')

    def show_frame(self):
        if self.cap:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame_idx)
            ret, frame = self.cap.read()
            if ret:
                if self.analysis_active:
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    _, th = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY_INV)
                    cnts, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    if cnts:
                        cv2.drawContours(frame, [max(cnts, key=cv2.contourArea)], -1, (0, 255, 0), 2)
                self.display_frame(frame)
                if hasattr(self, 'lbl_frame_counter') and self.total_frames > 0:
                    self.lbl_frame_counter.configure(text=f'Frame: {self.current_frame_idx} / {self.total_frames - 1}')

    def toggle_video(self):
        if not self.cap:
            return
        if hasattr(self, 'video_slider_var'):
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, int(self.video_slider_var.get()))
        self.video_playing = not self.video_playing
        self.btn_play.configure(text='PAUSE' if self.video_playing else 'START')
        if self.video_playing:
            self.run_video_loop()

    def run_video_loop(self):
        if self.video_playing and self.cap:
            if self.current_frame_idx < self.total_frames - 1:
                self.current_frame_idx += 1
                self.show_frame()
                self.after_id = self.after(30, self.run_video_loop)
            else:
                self.video_playing = False
                self.btn_play.configure(text='START')

    def stop_video(self):
        self.video_playing = False
        if self.after_id is not None:
            self.after_cancel(self.after_id)
            self.after_id = None
        self.btn_play.configure(text='START')

    def prev_frame(self):
        self.stop_video()
        if self.cap is not None and self.current_frame_idx > 0:
            self.current_frame_idx -= 1
            self.show_frame()

    def next_frame(self):
        self.stop_video()
        if self.cap is not None and self.current_frame_idx < self.total_frames - 1:
            self.current_frame_idx += 1
            self.show_frame()
