from __future__ import annotations
import math
import cv2
import numpy as np
import tkinter as tk
from tkinter import filedialog
from dropen3.ui.point_selection import select_image_points
from dropen3.science.contact_angles import baseline_internal_angle, calculate_diameter, draw_tangents, points_near_baseline, weighted_baseline_angle


class HysteresisAnalysisMixin:

    def run_polynomial_hysteresis(self):
        method_current = 'HIS_POLYNOMIAL'
        if self.last_method_selected != method_current:
            for item in self.tree.get_children():
                self.tree.delete(item)
            self.last_method_selected = method_current
        path = filedialog.askopenfilename(filetypes=[('Videos', '*.avi *.mp4'), ('All', '*.*')])
        if not path:
            return
        self.video_path = path
        self.current_mode = 'HIS'
        self.cap = cv2.VideoCapture(path)
        self.hysteresis_points_baseline = []
        self.hysteresis_frame_baseline = None
        idx = 0
        total = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        win_frame = 'Config: Frame'
        cv2.namedWindow(win_frame, cv2.WINDOW_NORMAL)
        while True:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = self.cap.read()
            if not ret:
                break
            vis = frame.copy()
            cv2.putText(vis, f'Frame: {idx}/{total - 1} - A/D to navigate, ENTER to select.', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.imshow(win_frame, vis)
            k = cv2.waitKey(0) & 255
            if k == ord('d'):
                idx = min(idx + 1, total - 1)
            elif k == ord('a'):
                idx = max(idx - 1, 0)
            elif k == 13:
                self.hysteresis_frame_baseline = frame.copy()
                break
            elif k == 27:
                cv2.destroyWindow(win_frame)
                return
        cv2.destroyWindow(win_frame)

        selected_points = select_image_points(self.hysteresis_frame_baseline, 2, 'Config: Base')
        if selected_points is None:
            return
        self.hysteresis_points_baseline = selected_points
        self.hysteresis_y_baseline = max(self.hysteresis_points_baseline[0][1], self.hysteresis_points_baseline[1][1])
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        ret_bg, frame_bg = self.cap.read()
        if ret_bg:
            bg_gray = cv2.cvtColor(frame_bg, cv2.COLOR_BGR2GRAY)
            self.background_gray = cv2.GaussianBlur(bg_gray, (5, 5), 0)
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        self.analysis_active = True
        self.lbl_status.configure(text='Processing Polynomial Hysteresis...')
        cv2.namedWindow('Analysis: Binary Video', cv2.WINDOW_NORMAL)
        self.analysis_active = True
        if hasattr(self, 'lbl_status'):
            self.lbl_status.configure(text='WLS analysis in progress.')
        self.process_polynomial_hysteresis_frame()

    def process_polynomial_hysteresis_frame(self):
        if not self.analysis_active or self.cap is None:
            cv2.destroyWindow('Analysis: Binary Video')
            return
        if not getattr(self, 'analysis_active', False):
            return
        ret, frame = self.cap.read()
        if not ret:
            self.analysis_active = False
            self.lbl_status.configure(text='Analysis completed.')
            cv2.destroyWindow('Analysis: Binary Video')
            return
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        diff = cv2.absdiff(self.background_gray, gray)
        _, thresh = cv2.threshold(diff, self.threshold_hysteresis, 255, cv2.THRESH_BINARY)
        kernel = np.ones((3, 3), np.uint8)
        thresh = cv2.dilate(thresh, kernel, iterations=1)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        cv2.imshow('Analysis: Binary Video', thresh)
        cv2.waitKey(1)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        if contours:
            cnt = max(contours, key=cv2.contourArea).reshape(-1, 2)
            points_near_baseline = np.array([p for p in cnt if abs(p[1] - self.hysteresis_y_baseline) < self.tangent_static_pol])
            if len(points_near_baseline) > self.tangent_static_baseline_points:
                x_mean = np.mean(points_near_baseline[:, 0])
                left_points = points_near_baseline[points_near_baseline[:, 0] < x_mean]
                right_points = points_near_baseline[points_near_baseline[:, 0] >= x_mean]

                def calc_poly(points, side):
                    if len(points) < 5:
                        return (0.0, 0.0, (0, 0), None, None)
                    sort_idx = np.argsort(points[:, 1])
                    points_fitting = points[sort_idx][:30]
                    px, py = (points_fitting[:, 0], points_fitting[:, 1])
                    coef = np.polyfit(py, px, 2)
                    y_contato = np.max(py)
                    x_contato = np.polyval(coef, y_contato)
                    dx_dy = 2 * coef[0] * y_contato + coef[1]
                    slope = 1 / abs(dx_dy) if dx_dy != 0 else 999
                    angle = np.degrees(np.arctan(slope))
                    if side == 'left':
                        angle = 180 - angle if dx_dy > 0 else angle
                    else:
                        angle = 180 - angle if dx_dy < 0 else angle
                    return (angle, dx_dy, (int(x_contato), int(y_contato)), coef, py)
                a_left, s_left, p_left, c_left, y_range_e = calc_poly(left_points, 'left')
                a_right, s_right, p_right, c_right, y_range_d = calc_poly(right_points, 'right')
                if c_left is not None:
                    self.draw_fitted_curve(frame, c_left, y_range_e, 0, 0, (255, 255, 0))
                    self.draw_tangent(frame, p_left, s_left, 'left')
                if c_right is not None:
                    self.draw_fitted_curve(frame, c_right, y_range_d, 0, 0, (255, 255, 0))
                    self.draw_tangent(frame, p_right, s_right, 'right')
                f_id = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
                fps = self.cap.get(cv2.CAP_PROP_FPS)
                time = f_id / fps if fps > 0 else 0
                diameter = abs(p_right[0] - p_left[0])
                area = cv2.contourArea(cnt)
                self.tree.insert('', 'end', values=(f_id, f'{time:.2f}', f'{diameter:.1f}', f'{a_left:.2f}', f'{a_right:.2f}', f'{abs(a_left - a_right):.2f}', f'{area:.0f}'))
        self.display_frame(frame)
        self.after(100, self.process_polynomial_hysteresis_frame)

    def run_weighted_hysteresis(self):
        method_current = 'WCA_WLS_DYNAMIC'
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.last_method_selected = method_current
        path = filedialog.askopenfilename(filetypes=[('Videos', '*.avi *.mp4'), ('All', '*.*')])
        if not path:
            return
        self.video_path = path
        self.current_mode = 'HIS'
        self.cap_hysteresis = cv2.VideoCapture(path)
        self.hysteresis_points_baseline = []
        self.hysteresis_frame_baseline = None
        self.hysteresis_background = None
        self.p_left_initial = None
        self.p_right_initial = None
        idx = 0
        total = int(self.cap_hysteresis.get(cv2.CAP_PROP_FRAME_COUNT))
        cv2.namedWindow('Config WLS: Frame')
        while True:
            self.cap_hysteresis.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = self.cap_hysteresis.read()
            if not ret:
                break
            vis = frame.copy()
            cv2.putText(vis, f'WLS Frame: {idx}/{total - 1} - A/D to navigate, ENTER to select.', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.imshow('Config WLS: Frame', vis)
            k = cv2.waitKey(0) & 255
            if k == ord('d'):
                idx = min(idx + 1, total - 1)
            elif k == ord('a'):
                idx = max(idx - 1, 0)
            elif k == 13:
                self.hysteresis_frame_baseline = frame.copy()
                break
        cv2.destroyWindow('Config WLS: Frame')

        selected_points = select_image_points(self.hysteresis_frame_baseline, 2, 'Config WLS: Base')
        if selected_points is None:
            return
        self.hysteresis_points_baseline = selected_points
        self.hysteresis_y_baseline = max(self.hysteresis_points_baseline[0][1], self.hysteresis_points_baseline[1][1])
        self.cap_hysteresis.set(cv2.CAP_PROP_POS_FRAMES, 0)
        self.show_hysteresis_settings()
        self.analysis_active = True
        if hasattr(self, 'lbl_status'):
            self.lbl_status.configure(text='Weighted analysis in progress...')
        self.process_next_weighted_frame()

    def process_next_weighted_frame(self):
        if not getattr(self, 'analysis_active', False):
            return
        ret, frame = self.cap_hysteresis.read()
        if not ret:
            self.cap_hysteresis.release()
            self.lbl_status.configure(text='WLS Hysteresis Analysis Completed.')
            return
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        fps = self.cap_hysteresis.get(cv2.CAP_PROP_FPS) or 30
        if self.hysteresis_background is None:
            self.hysteresis_background = gray.copy()
        else:
            y_b = self.hysteresis_y_baseline
            gray[y_b:, :] = 255
            diff = cv2.absdiff(gray, self.hysteresis_background)
            blur = cv2.GaussianBlur(diff[:y_b, :], (5, 5), 0)
            thresh_val = getattr(self, 'threshold_hysteresis', 45)
            _, bin_img = cv2.threshold(blur, thresh_val, 255, cv2.THRESH_BINARY)
            cnts, _ = cv2.findContours(bin_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if cnts:
                cnt = max(cnts, key=cv2.contourArea)
                if cv2.contourArea(cnt) > 500:
                    n_tangent = getattr(self, 'n_points_tangent_val', 30)
                    min_points = getattr(self, 'min_points_fit', 5)
                    res = weighted_baseline_angle(cnt, y_b, margin_baseline=15, n_tangent_points=n_tangent, min_points=min_points)
                    angle_left, angle_right, p_left, p_right, viz_left, viz_right = res
                    diameter_px, p1_d, p2_d = calculate_diameter(cnt, frame)
                    radius = diameter_px / 2
                    area_baseline = math.pi * radius ** 2
                    frame_idx = int(self.cap_hysteresis.get(cv2.CAP_PROP_POS_FRAMES))
                    time_seconds = frame_idx / fps
                    if p_left is not None and self.p_left_initial is None:
                        self.p_left_initial = p_left[0]
                    if p_right is not None and self.p_right_initial is None:
                        self.p_right_initial = p_right[0]
                    if p_left is not None and p_right is not None:
                        diameter_baseline_px = abs(p_right[0] - p_left[0])
                    else:
                        diameter_baseline_px = 0.0
                    advance_left = abs(p_left[0] - self.p_left_initial) if p_left is not None and self.p_left_initial is not None else 0.0
                    advance_right = abs(p_right[0] - self.p_right_initial) if p_right is not None and self.p_right_initial is not None else 0.0
                    cv2.drawContours(frame, [cnt], -1, (0, 255, 0), 1)
                    cv2.line(frame, (0, int(y_b)), (frame.shape[1], int(y_b)), (255, 0, 0), 2)
                    if p_left is not None and p_right is not None:
                        cv2.line(frame, (p_left[0], int(y_b)), (p_right[0], int(y_b)), (0, 255, 255), 2)
                        cv2.putText(frame, f'Diam: {diameter_baseline_px:.1f}px', (min(p_left[0], p_right[0]), int(y_b) - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
                    if p_left is not None and (not np.isnan(angle_left)):
                        cv2.circle(frame, p_left, 4, (0, 255, 0), -1)
                        rad_left = math.radians(angle_left)
                        cv2.line(frame, p_left, (p_left[0] + int(50 * math.cos(rad_left)), p_left[1] - int(50 * math.sin(rad_left))), (0, 0, 255), 2)
                    if p_right is not None and (not np.isnan(angle_right)):
                        cv2.circle(frame, p_right, 4, (0, 255, 0), -1)
                        rad_right = math.radians(angle_right)
                        cv2.line(frame, p_right, (p_right[0] - int(50 * math.cos(rad_right)), p_right[1] - int(50 * math.sin(rad_right))), (0, 0, 255), 2)
                    hysteresis_inst = abs(angle_left - angle_right) if not np.isnan(angle_left) and (not np.isnan(angle_right)) else 0.0
                    columns_wls = ('frame', 'time', 'diameter', 'diametro_base', 'advance_left', 'advance_right', 'left', 'right', 'hysteresis', 'area')
                    if self.tree['columns'] != columns_wls:
                        self.tree.configure(columns=columns_wls)
                        self.tree.heading('#0', text='', anchor='center')
                        self.tree.heading('frame', text='Frame')
                        self.tree.heading('time', text='Time (s)')
                        self.tree.heading('diameter', text='Diameter (px)')
                        self.tree.heading('diametro_base', text='Base Diameter (px)')
                        self.tree.heading('advance_left', text='Left Advance (px)')
                        self.tree.heading('advance_right', text='Right Advance (px)')
                        self.tree.heading('left', text='Left Angle (°)')
                        self.tree.heading('right', text='Right Angle (°)')
                        self.tree.heading('hysteresis', text='Hysteresis (°)')
                        self.tree.heading('area', text='Projected Base Area (px²)')
                        self.tree.column('#0', width=0, stretch=tk.NO)
                        for col in columns_wls:
                            self.tree.column(col, width=90, anchor='center')
                    self.tree.insert('', 'end', values=(frame_idx, f'{time_seconds:.3f}', f'{diameter_px:.2f}', f'{diameter_baseline_px:.2f}', f'{advance_left:.2f}', f'{advance_right:.2f}', f'{angle_left:.2f}' if not np.isnan(angle_left) else 'N/A', f'{angle_right:.2f}' if not np.isnan(angle_right) else 'N/A', f'{hysteresis_inst:.2f}', f'{area_baseline:.2f}'))
        self.display_frame(frame)
        self.after(10, self.process_next_weighted_frame)

    def run_advancing_hysteresis(self):
        method_current = 'HIS_AVANCANTE'
        if self.last_method_selected != method_current:
            for item in self.tree.get_children():
                self.tree.delete(item)
            self.last_method_selected = method_current
        path = filedialog.askopenfilename(filetypes=[('Videos', '*.avi *.mp4'), ('All', '*.*')])
        if not path:
            return
        self.video_path = path
        self.current_mode = 'HIS'
        self.cap_hysteresis = cv2.VideoCapture(path)
        self.hysteresis_points_baseline = []
        self.hysteresis_frame_baseline = None
        self.hysteresis_background = None
        idx = 0
        total = int(self.cap_hysteresis.get(cv2.CAP_PROP_FRAME_COUNT))
        cv2.namedWindow('Config: Frame')
        while True:
            self.cap_hysteresis.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = self.cap_hysteresis.read()
            if not ret:
                break
            vis = frame.copy()
            cv2.putText(vis, f'Frame: {idx}/{total - 1} - A/D to navigate, ENTER to select.', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.imshow('Config: Frame', vis)
            k = cv2.waitKey(0) & 255
            if k == ord('d'):
                idx = min(idx + 1, total - 1)
            elif k == ord('a'):
                idx = max(idx - 1, 0)
            elif k == 13:
                self.hysteresis_frame_baseline = frame.copy()
                break
        cv2.destroyWindow('Config: Frame')

        selected_points = select_image_points(self.hysteresis_frame_baseline, 2, 'Config: Base')
        if selected_points is None:
            return
        self.hysteresis_points_baseline = selected_points
        self.hysteresis_y_baseline = max(self.hysteresis_points_baseline[0][1], self.hysteresis_points_baseline[1][1])
        self.hysteresis_points_baseline = sorted(self.hysteresis_points_baseline, key=lambda p: p[0])
        self.cap_hysteresis.set(cv2.CAP_PROP_POS_FRAMES, 0)
        self.analysis_active = True
        if hasattr(self, 'lbl_status'):
            self.lbl_status.configure(text='Weighted analysis in progress...')
        self.process_next_hysteresis_frame()

    def process_next_hysteresis_frame(self):
        if not getattr(self, 'analysis_active', False):
            return
        ret, frame = self.cap_hysteresis.read()
        if not ret:
            self.cap_hysteresis.release()
            self.lbl_status.configure(text='Hysteresis Analysis Completed.')
            return
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        fps = self.cap_hysteresis.get(cv2.CAP_PROP_FPS) or 30
        if self.hysteresis_background is None:
            self.hysteresis_background = gray.copy()
        else:
            y_b = self.hysteresis_y_baseline
            gray[y_b:, :] = 255
            diff = cv2.absdiff(gray, self.hysteresis_background)
            blur = cv2.GaussianBlur(diff[:y_b, :], (5, 5), 0)
            _, bin_img = cv2.threshold(blur, self.threshold_hysteresis, 255, cv2.THRESH_BINARY)
            cnts, _ = cv2.findContours(bin_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if cnts:
                cnt = max(cnts, key=cv2.contourArea)
                if cv2.contourArea(cnt) > 500:
                    res = baseline_internal_angle(cnt, y_b, n_tangent_points=self.n_points_tangent_val, min_points=self.min_points_fit)
                    angle_left, angle_right, p_left, p_right, viz_left, viz_right = res
                    diameter_px, p1_d, p2_d = calculate_diameter(cnt, frame)
                    radius = diameter_px / 2
                    area_baseline = math.pi * radius ** 2
                    frame_idx = int(self.cap_hysteresis.get(cv2.CAP_PROP_POS_FRAMES))
                    time_seconds = frame_idx / fps
                    x_baseline_left = self.hysteresis_points_baseline[0][0]
                    x_baseline_right = self.hysteresis_points_baseline[1][0]
                    if p_left is not None:
                        advance_left = x_baseline_left - p_left[0]
                    else:
                        advance_left = 0.0
                    if p_right is not None:
                        advance_right = p_right[0] - x_baseline_right
                    else:
                        advance_right = 0.0
                    if p_left is not None and p_right is not None:
                        diameter_baseline_px = abs(p_right[0] - p_left[0])
                    else:
                        diameter_baseline_px = abs(x_baseline_right - x_baseline_left)
                    cv2.drawContours(frame, [cnt], -1, (0, 255, 0), 1)
                    if p_left and p_right:
                        frame = draw_tangents(frame, p_left, p_right, viz_left, viz_right)
                    if not np.isnan(angle_left) and (not np.isnan(angle_right)):
                        hysteresis_inst = abs(angle_left - angle_right)
                        frame_idx = int(self.cap_hysteresis.get(cv2.CAP_PROP_POS_FRAMES))
                        self.tree.insert('', 'end', values=(frame_idx, f'{time_seconds:.3f}', f'{diameter_px:.2f}', f'{diameter_baseline_px:.2f}', f'{advance_left:.2f}', f'{advance_right:.2f}', f'{angle_left:.2f}', f'{angle_right:.2f}', f'{hysteresis_inst:.2f}', f'{area_baseline:.2f}'))
        self.display_frame(frame)
        self.after(10, self.process_next_hysteresis_frame)

    def run_first_frame_weighted_hysteresis(self):
        method_current = 'WCA_WLS_FIRST_FRAME'
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.last_method_selected = method_current
        path = filedialog.askopenfilename(filetypes=[('Videos', '*.avi *.mp4'), ('All', '*.*')])
        if not path:
            return
        self.video_path = path
        self.current_mode = 'HIS'
        self.cap_hysteresis = cv2.VideoCapture(path)
        self.hysteresis_points_baseline = []
        self.hysteresis_frame_baseline = None
        self.hysteresis_background = None
        self.usar_first_frame_como_droplet = True
        self.p_left_initial = None
        self.p_right_initial = None
        idx = 0
        total = int(self.cap_hysteresis.get(cv2.CAP_PROP_FRAME_COUNT))
        cv2.namedWindow('Config WLS: Frame')
        while True:
            self.cap_hysteresis.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = self.cap_hysteresis.read()
            if not ret:
                break
            vis = frame.copy()
            cv2.putText(vis, f'WLS Frame: {idx}/{total - 1} - A/D to navigate, ENTER to select.', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.imshow('Config WLS: Frame', vis)
            k = cv2.waitKey(0) & 255
            if k == ord('d'):
                idx = min(idx + 1, total - 1)
            elif k == ord('a'):
                idx = max(idx - 1, 0)
            elif k == 13:
                self.hysteresis_frame_baseline = frame.copy()
                break
        cv2.destroyWindow('Config WLS: Frame')
        if self.hysteresis_frame_baseline is None:
            return

        selected_points = select_image_points(self.hysteresis_frame_baseline, 2, 'Config WLS: Base')
        if selected_points is None:
            return
        self.hysteresis_points_baseline = selected_points
        self.hysteresis_y_baseline = max(self.hysteresis_points_baseline[0][1], self.hysteresis_points_baseline[1][1])
        self.cap_hysteresis.set(cv2.CAP_PROP_POS_FRAMES, 0)
        self.show_hysteresis_settings()
        self.analysis_active = True
        if hasattr(self, 'lbl_status'):
            self.lbl_status.configure(text='Weighted first-frame analysis in progress...')
        self.process_next_first_frame_weighted()

    def process_next_first_frame_weighted(self):
        if not getattr(self, 'analysis_active', False):
            return
        ret, frame = self.cap_hysteresis.read()
        if not ret:
            self.cap_hysteresis.release()
            if hasattr(self, 'lbl_status'):
                self.lbl_status.configure(text='WLS Hysteresis Analysis Completed.')
            return
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        fps = self.cap_hysteresis.get(cv2.CAP_PROP_FPS) or 30
        y_b = self.hysteresis_y_baseline
        if getattr(self, 'usar_first_frame_como_droplet', False):
            roi = gray[:y_b, :]
            blur = cv2.GaussianBlur(roi, (5, 5), 0)
            _, bin_img = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        elif self.hysteresis_background is None:
            self.hysteresis_background = gray.copy()
            bin_img = None
        else:
            gray[y_b:, :] = 255
            diff = cv2.absdiff(gray, self.hysteresis_background)
            blur = cv2.GaussianBlur(diff[:y_b, :], (5, 5), 0)
            thresh_val = getattr(self, 'threshold_hysteresis', 45)
            _, bin_img = cv2.threshold(blur, thresh_val, 255, cv2.THRESH_BINARY)
        if bin_img is not None:
            cnts, _ = cv2.findContours(bin_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if cnts:
                cnt = max(cnts, key=cv2.contourArea)
                if cv2.contourArea(cnt) > 500:
                    n_tangent = getattr(self, 'n_points_tangent_val', 30)
                    min_points = getattr(self, 'min_points_fit', 5)
                    res = weighted_baseline_angle(cnt, y_b, margin_baseline=15, n_tangent_points=n_tangent, min_points=min_points)
                    angle_left, angle_right, p_left, p_right, viz_left, viz_right = res
                    diameter_px, p1_d, p2_d = calculate_diameter(cnt, frame)
                    radius = diameter_px / 2
                    area_baseline = math.pi * radius ** 2
                    frame_idx = int(self.cap_hysteresis.get(cv2.CAP_PROP_POS_FRAMES))
                    time_seconds = frame_idx / fps
                    if p_left is not None and self.p_left_initial is None:
                        self.p_left_initial = p_left[0]
                    if p_right is not None and self.p_right_initial is None:
                        self.p_right_initial = p_right[0]
                    if p_left is not None and p_right is not None:
                        diameter_baseline_px = abs(p_right[0] - p_left[0])
                    else:
                        diameter_baseline_px = 0.0
                    advance_left = abs(p_left[0] - self.p_left_initial) if p_left is not None and self.p_left_initial is not None else 0.0
                    advance_right = abs(p_right[0] - self.p_right_initial) if p_right is not None and self.p_right_initial is not None else 0.0
                    cv2.drawContours(frame, [cnt], -1, (0, 255, 0), 1)
                    cv2.line(frame, (0, int(y_b)), (frame.shape[1], int(y_b)), (255, 0, 0), 2)
                    if p_left is not None and (not np.isnan(angle_left)):
                        cv2.circle(frame, p_left, 4, (0, 255, 0), -1)
                        rad_left = math.radians(angle_left)
                        cv2.line(frame, p_left, (p_left[0] + int(50 * math.cos(rad_left)), p_left[1] - int(50 * math.sin(rad_left))), (0, 0, 255), 2)
                    if p_right is not None and (not np.isnan(angle_right)):
                        cv2.circle(frame, p_right, 4, (0, 255, 0), -1)
                        rad_right = math.radians(angle_right)
                        cv2.line(frame, p_right, (p_right[0] - int(50 * math.cos(rad_right)), p_right[1] - int(50 * math.sin(rad_right))), (0, 0, 255), 2)
                    hysteresis_inst = abs(angle_left - angle_right) if not np.isnan(angle_left) and (not np.isnan(angle_right)) else 0.0
                    columns_wls = ('frame', 'time', 'diameter', 'diametro_base', 'advance_left', 'advance_right', 'left', 'right', 'hysteresis', 'area')
                    if self.tree['columns'] != columns_wls:
                        self.tree.configure(columns=columns_wls)
                        self.tree.heading('#0', text='', anchor='center')
                        self.tree.heading('frame', text='Frame')
                        self.tree.heading('time', text='Time (s)')
                        self.tree.heading('diameter', text='Diameter (px)')
                        self.tree.heading('diametro_base', text='Base Diameter (px)')
                        self.tree.heading('advance_left', text='Left Advance (px)')
                        self.tree.heading('advance_right', text='Right Advance (px)')
                        self.tree.heading('left', text='Left Angle (°)')
                        self.tree.heading('right', text='Right Angle (°)')
                        self.tree.heading('hysteresis', text='Hysteresis (°)')
                        self.tree.heading('area', text='Projected Base Area (px²)')
                        self.tree.column('#0', width=0, stretch=tk.NO)
                        for col in columns_wls:
                            self.tree.column(col, width=90, anchor='center')
                    self.tree.insert('', 'end', values=(frame_idx, f'{time_seconds:.3f}', f'{diameter_px:.2f}', f'{diameter_baseline_px:.2f}', f'{advance_left:.2f}', f'{advance_right:.2f}', f'{angle_left:.2f}' if not np.isnan(angle_left) else 'N/A', f'{angle_right:.2f}' if not np.isnan(angle_right) else 'N/A', f'{hysteresis_inst:.2f}', f'{area_baseline:.2f}'))
        self.display_frame(frame)
        self.after(10, self.process_next_first_frame_weighted)

    def calculate_quadratic_angle(self, points, side):
        if len(points) < 15:
            return 0.0
        try:
            x = points[:, 0].astype(float)
            y = points[:, 1].astype(float)
            coef = np.polyfit(x, y, 2)
            polinomio = np.poly1d(coef)
            derivative = np.polyder(polinomio)
            x_contato = np.min(x) if side == 'left' else np.max(x)
            m = derivative(x_contato)
            angle_rad = math.atan(abs(m))
            angle_deg = math.degrees(angle_rad)
            if side == 'left':
                return 180 - angle_deg if m > 0 else angle_deg
            else:
                return 180 - angle_deg if m < 0 else angle_deg
        except Exception as e:
            print(f'Calculation error: {e}')
            return 0.0
