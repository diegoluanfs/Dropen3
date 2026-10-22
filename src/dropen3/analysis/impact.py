from __future__ import annotations
import cv2
import numpy as np
import tkinter as tk
import math
from dropen3.ui.point_selection import select_video_points
from dropen3.science.metrics import LiquidProperties, dimensionless_numbers
import customtkinter as ctk
from tkinter import filedialog
from tkinter import messagebox


class ImpactAnalysisMixin:

    def robust_segmentation(self, frame_gray, background):
        diff = cv2.absdiff(background, frame_gray)
        blurred = cv2.medianBlur(diff, 5)
        _, mask = cv2.threshold(blurred, 30, 255, cv2.THRESH_BINARY)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
        return mask

    def run_impact_method_three(self):
        method_current = 'DROP_THIRD'
        if self.last_method_selected != method_current:
            for item in self.tree.get_children():
                self.tree.delete(item)
            self.last_method_selected = method_current
        path = filedialog.askopenfilename(filetypes=[('Videos', '*.avi *.mp4'), ('All files', '*.*')])
        if not path:
            return
        self.video_path = path
        self.params = self.configure_physical_parameters()
        if self.params is None:
            return
        cap_config = cv2.VideoCapture(path)
        total = int(cap_config.get(cv2.CAP_PROP_FRAME_COUNT))
        idx = 0
        win_frame = 'Config: Select Background'
        cv2.namedWindow(win_frame, cv2.WINDOW_NORMAL)
        while True:
            cap_config.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame_ref = cap_config.read()
            if not ret:
                break
            vis = frame_ref.copy()
            cv2.putText(vis, f'Frame: {idx}/{total - 1} - A/D navigate, ENTER select.', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.imshow(win_frame, vis)
            k = cv2.waitKey(0) & 255
            if k == ord('d'):
                idx = min(idx + 1, total - 1)
            elif k == ord('a'):
                idx = max(idx - 1, 0)
            elif k == 13:
                self.background_gray = cv2.cvtColor(frame_ref, cv2.COLOR_BGR2GRAY)
                break
            elif k == 27:
                cv2.destroyWindow(win_frame)
                cap_config.release()
                return
        cv2.destroyWindow(win_frame)
        selected = select_video_points(cap_config, idx, 2, 'Config: Define Baseline')
        if selected is None:
            cap_config.release()
            return
        idx, self.points_baseline = selected
        self.limit_y_baseline = (self.points_baseline[0][1] + self.points_baseline[1][1]) / 2
        cv2.destroyAllWindows()
        cap_config.release()
        self.cap_vel = cv2.VideoCapture(path)
        self.current_mode = 'DROP'
        self.params.update({'min_area': 300, 'fps_real': self.params.get('fps_real', 10000)})
        self.data = {'history_pos': [], 'preimpact_diameter': float('nan'), 'times': [], 'positions': [], 'falling_areas': [], 'last_diam_val': None, 'max_w_px': 0}
        self.frame_id = 0
        self.impact_detected = False
        self.vel_active = True
        self.analysis_active = True
        if hasattr(self, 'lbl_status'):
            self.lbl_status.configure(text='Baseline defined. Starting Third Method analysis...')
            if not hasattr(self, 'progress_bar'):
                parent_frame = self.lbl_status.master
                self.progress_bar = ctk.CTkProgressBar(parent_frame)
                self.progress_bar.pack(side='top', fill='x', padx=10, pady=10)
        if hasattr(self, 'progress_bar'):
            self.progress_bar.set(0)
        self.update_idletasks()
        self.process_impact_frame_three()

    def process_impact_frame_three(self):
        if not getattr(self, 'analysis_active', False) or not getattr(self, 'vel_active', False) or self.cap_vel is None:
            return
        if hasattr(self, 'lbl_status'):
            self.lbl_status.configure(text='Impact analysis in progress...')
            if not hasattr(self, 'progress_bar'):
                parent_frame = self.lbl_status.master
                self.progress_bar = ctk.CTkProgressBar(parent_frame)
                self.progress_bar.pack(side='top', fill='x', padx=10, pady=5)
        p, d = (self.params, self.data)
        ret, frame = self.cap_vel.read()
        if not ret:
            if hasattr(self, 'progress_bar'):
                self.progress_bar.set(1.0)
            if hasattr(self, 'lbl_status'):
                self.lbl_status.configure(text='Impact analysis completed!')
            if len(d['positions']) > 2:
                times = np.array(d['times'])
                pos_m = np.array(d['positions']) * p['scale'] / 1000.0
                n_frames_impact = min(8, len(pos_m))
                times_end = times[-n_frames_impact:]
                pos_m_end = pos_m[-n_frames_impact:]
                v_impact, _ = np.polyfit(times_end, pos_m_end, 1)
                v_abs = abs(v_impact)
                d_mean_mm = d['preimpact_diameter']
                if not np.isfinite(d_mean_mm) or d_mean_mm <= 0:
                    messagebox.showwarning('Insufficient measurements', 'No valid pre-impact diameter was measured; dimensionless numbers cannot be calculated.')
                    self.cap_vel.release()
                    self.vel_active = False
                    return
                d_m = d_mean_mm / 1000.0
                numbers = dimensionless_numbers(v_abs, d_m, LiquidProperties(p['density'], p['viscosity'], p['tension']))
                re, we, oh = numbers.reynolds, numbers.weber, numbers.ohnesorge
                mean_area_px2 = sum(d['falling_areas']) / len(d['falling_areas']) if d['falling_areas'] else 0
                self.show_dimensionless_results(v_abs, d_mean_mm, re, we, oh, mean_area_px2)
            self.cap_vel.release()
            self.vel_active = False
            return
        total_frames = int(self.cap_vel.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames > 0 and hasattr(self, 'progress_bar'):
            progresso = self.frame_id / total_frames
            self.progress_bar.set(progresso)
            if hasattr(self, 'lbl_status'):
                self.lbl_status.configure(text=f'Impact analysis in progress... {int(progresso * 100)}%')
            if self.frame_id % 5 == 0 or self.frame_id == total_frames:
                self.update_idletasks()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        mask = self.robust_segmentation(gray, self.background_gray)
        mask[int(self.limit_y_baseline):, :] = 0
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if cnts:
            w_img = frame.shape[1]
            c = min(cnts, key=lambda ct: abs(cv2.moments(ct)['m10'] / (cv2.moments(ct)['m00'] + 1e-05) - w_img / 2))
            area_current_px = cv2.contourArea(c)
            if area_current_px > p['min_area']:
                M = cv2.moments(c)
                if M['m00'] > 0:
                    yc = M['m01'] / M['m00']
                    xc = M['m10'] / M['m00']
                else:
                    x_box, y_box, w_box, h_box = cv2.boundingRect(c)
                    yc = y_box + h_box / 2.0
                    xc = x_box + w_box / 2.0
                _, box_top_y, _, h_box = cv2.boundingRect(c)
                y_baseline_droplet_box = box_top_y + h_box
                thick_cnt = getattr(self, 'thick_impact_contour', 2)
                thick_baseline = getattr(self, 'thick_impact_baseline', 2)
                thick_hgt = getattr(self, 'thick_impact_height', 2)
                cv2.line(frame, (0, int(self.limit_y_baseline)), (w_img, int(self.limit_y_baseline)), (0, 255, 255), thick_baseline)
                if not self.impact_detected:
                    d['falling_areas'].append(area_current_px)
                    d['times'].append(self.frame_id * p['dt'])
                    d['positions'].append(yc)
                    if len(c) >= 5:
                        ellipse = cv2.fitEllipse(c)
                        d['preimpact_diameter'] = (ellipse[1][0] + ellipse[1][1]) / 2 * p['scale']
                        cv2.ellipse(frame, ellipse, (255, 0, 0), 2)
                    cv2.circle(frame, (int(xc), int(yc)), 3, (0, 255, 0), -1)
                    if abs(y_baseline_droplet_box - self.limit_y_baseline) < 5:
                        self.impact_detected = True
                else:
                    hull = cv2.convexHull(c)
                    p_left = tuple(hull[hull[:, :, 0].argmin()][0])
                    p_right = tuple(hull[hull[:, :, 0].argmax()][0])
                    diameter_pixel = p_right[0] - p_left[0]
                    diameter_mm = diameter_pixel * p['scale']
                    beta = diameter_mm / d['preimpact_diameter'] if np.isfinite(d['preimpact_diameter']) and d['preimpact_diameter'] > 0 else float('nan')
                    area_mm2 = area_current_px * p['scale'] ** 2
                    time_current = self.frame_id * p['dt']
                    top_point = tuple(hull[hull[:, :, 1].argmin()][0])
                    p_baseline = tuple(hull[hull[:, :, 1].argmax()][0])
                    height_pixel = p_baseline[1] - top_point[1]
                    height_mm = height_pixel * p['scale']
                    last_d = d.get('last_diam_val')
                    dd_dt = (diameter_mm - last_d) / p['dt'] if last_d is not None else 0.0
                    d['last_diam_val'] = diameter_mm
                    cv2.drawContours(frame, [hull], -1, (0, 255, 0), thick_cnt)
                    cv2.line(frame, p_left, p_right, (0, 0, 255), thick_baseline)
                    p1_alt = (top_point[0], top_point[1])
                    p2_alt = (top_point[0], p_baseline[1])
                    cv2.line(frame, p1_alt, p2_alt, (255, 0, 255), thick_hgt)
                    self.tree.insert('', 'end', values=(f'{time_current:.5f}', '-', f'{diameter_mm:.3f}', f'{beta:.3f}', f'{height_mm:.3f}', f'{area_mm2:.3f}', f'{dd_dt:.3f}'))
        self.display_frame(frame)
        self.frame_id += 1
        self.after(1, self.process_impact_frame_three)

    def run_drop_impact_analysis(self):
        method_current = 'DROP_FOURTH'
        if self.last_method_selected != method_current:
            for item in self.tree.get_children():
                self.tree.delete(item)
            self.last_method_selected = method_current
        path = filedialog.askopenfilename(filetypes=[('Videos', '*.avi *.mp4 *.tif'), ('All files', '*.*')])
        if not path:
            return
        self.video_path = path
        self.params = self.configure_physical_parameters()
        if self.params is None:
            return
        cap_config = cv2.VideoCapture(path)
        total = int(cap_config.get(cv2.CAP_PROP_FRAME_COUNT))
        if total <= 0:
            return
        idx = 0
        win_frame = 'Config: Select Background'
        cv2.namedWindow(win_frame, cv2.WINDOW_NORMAL)
        while True:
            cap_config.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame_ref = cap_config.read()
            if not ret:
                break
            vis = frame_ref.copy()
            cv2.putText(vis, f'Frame: {idx}/{total - 1} - Use (<- / ->) to navigate, ENTER select.', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.imshow(win_frame, vis)
            k = cv2.waitKey(0) & 255
            if k in (2555904, 83, 65363):
                idx = min(idx + 1, total - 1)
            elif k in (2424832, 81, 65361):
                idx = max(idx - 1, 0)
            elif k == 13:
                self.background_gray = cv2.cvtColor(frame_ref, cv2.COLOR_BGR2GRAY)
                break
            elif k == 27:
                cv2.destroyWindow(win_frame)
                cap_config.release()
                return
        cv2.destroyWindow(win_frame)
        selected = select_video_points(cap_config, idx, 2, 'Config: Define Baseline')
        if selected is None:
            cap_config.release()
            return
        idx, self.points_baseline = selected
        x1, y1 = self.points_baseline[0]
        x2, y2 = self.points_baseline[1]
        if x2 - x1 != 0:
            self.m_baseline = (y2 - y1) / (x2 - x1)
            self.c_baseline = y1 - self.m_baseline * x1
        else:
            self.m_baseline = 0
            self.c_baseline = y1
        cv2.destroyAllWindows()
        cap_config.release()
        self.cap_vel = cv2.VideoCapture(path)
        self.current_mode = 'DROP'
        self.params.update({'min_area': 300, 'fps_real': self.params.get('fps_real', 10000)})
        self.data = {'history_pos': [], 'preimpact_diameter': float('nan'), 'times': [], 'positions': [], 'falling_areas': [], 'last_diam_val': None, 'max_w_px': 0}
        self.frame_id = 0
        self.impact_detected = False
        self.vel_active = True
        if hasattr(self, 'lbl_status'):
            self.lbl_status.configure(text='Baseline defined. Starting Fourth Method analysis...')
        self.analysis_active = True
        self.vel_active = True
        if hasattr(self, 'lbl_status'):
            self.lbl_status.configure(text='Impact analysis in progress...')
            if not hasattr(self, 'progress_bar'):
                parent_frame = self.lbl_status.master
                self.progress_bar = ctk.CTkProgressBar(parent_frame)
                self.progress_bar.pack(side='top', fill='x', padx=10, pady=10)
        if hasattr(self, 'progress_bar'):
            self.progress_bar.set(0)
        self.update_idletasks()
        self.process_impact_frame_four()

    def process_impact_frame_four(self):
        if not self.vel_active or self.cap_vel is None:
            return
        if not getattr(self, 'analysis_active', False) or not getattr(self, 'vel_active', False) or self.cap_vel is None:
            return
        if hasattr(self, 'lbl_status'):
            self.lbl_status.configure(text='Impact analysis in progress...')
            if not hasattr(self, 'progress_bar'):
                parent_frame = self.lbl_status.master
                self.progress_bar = ctk.CTkProgressBar(parent_frame)
                self.progress_bar.pack(side='top', fill='x', padx=10, pady=5)
        p, d = (self.params, self.data)
        ret, frame = self.cap_vel.read()
        if not ret:
            if hasattr(self, 'progress_bar'):
                self.progress_bar.set(1.0)
            if hasattr(self, 'lbl_status'):
                self.lbl_status.configure(text='Impact analysis completed!')
            if len(d['positions']) > 2:
                times = np.array(d['times'])
                pos_m = np.array(d['positions']) * p['scale'] / 1000.0
                n_frames_impact = min(8, len(pos_m))
                times_end = times[-n_frames_impact:]
                pos_m_end = pos_m[-n_frames_impact:]
                v_impact, _ = np.polyfit(times_end, pos_m_end, 1)
                v_abs = abs(v_impact)
                d_mean_mm = d['preimpact_diameter']
                if not np.isfinite(d_mean_mm) or d_mean_mm <= 0:
                    messagebox.showwarning('Insufficient measurements', 'No valid pre-impact diameter was measured; dimensionless numbers cannot be calculated.')
                    self.cap_vel.release()
                    self.vel_active = False
                    return
                d_m = d_mean_mm / 1000.0
                numbers = dimensionless_numbers(v_abs, d_m, LiquidProperties(p['density'], p['viscosity'], p['tension']))
                re, we, oh = numbers.reynolds, numbers.weber, numbers.ohnesorge
                mean_area_px2 = sum(d['falling_areas']) / len(d['falling_areas']) if d['falling_areas'] else 0
                self.show_dimensionless_results(v_abs, d_mean_mm, re, we, oh, mean_area_px2)
            self.cap_vel.release()
            self.vel_active = False
            return
        total_frames = int(self.cap_vel.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames > 0 and hasattr(self, 'progress_bar'):
            progresso = self.frame_id / total_frames
            self.progress_bar.set(progresso)
            if hasattr(self, 'lbl_status'):
                self.lbl_status.configure(text=f'Impact analysis in progress... {int(progresso * 100)}% (Frame: {self.frame_id}/{total_frames})')
            if self.frame_id % 5 == 0 or self.frame_id == total_frames:
                self.update_idletasks()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if hasattr(self, 'background_gray') and self.background_gray is not None:
            if gray.shape == self.background_gray.shape:
                diff = cv2.absdiff(gray, self.background_gray)
                clean = cv2.bilateralFilter(diff, 5, 75, 75)
                _, mask = cv2.threshold(clean, 15, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            else:
                clean = cv2.bilateralFilter(frame, 5, 75, 75)
                gray_clean = cv2.cvtColor(clean, cv2.COLOR_BGR2GRAY)
                _, mask = cv2.threshold(gray_clean, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        else:
            clean = cv2.bilateralFilter(frame, 5, 75, 75)
            gray_clean = cv2.cvtColor(clean, cv2.COLOR_BGR2GRAY)
            _, mask = cv2.threshold(gray_clean, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        h_img, w_img = frame.shape[:2]
        for x in range(w_img):
            y_limit = int(self.m_baseline * x + self.c_baseline)
            if 0 <= y_limit < h_img:
                mask[y_limit:, x] = 0
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        thick_cnt = getattr(self, 'thick_impact_contour', 2)
        thick_baseline = getattr(self, 'thick_impact_baseline', 2)
        thick_hgt = getattr(self, 'thick_impact_height', 2)
        pt_start = (0, int(self.c_baseline))
        pt_end = (w_img, int(self.m_baseline * w_img + self.c_baseline))
        cv2.line(frame, pt_start, pt_end, (0, 255, 255), thick_baseline)
        if cnts:
            c = min(cnts, key=lambda ct: abs(cv2.moments(ct)['m10'] / (cv2.moments(ct)['m00'] + 1e-05) - w_img / 2))
            area_current_px = cv2.contourArea(c)
            if area_current_px > p['min_area']:
                M = cv2.moments(c)
                if M['m00'] > 0:
                    yc = M['m01'] / M['m00']
                    xc = M['m10'] / M['m00']
                else:
                    x_box, y_box, w_box, h_box = cv2.boundingRect(c)
                    yc = y_box + h_box / 2.0
                    xc = x_box + w_box / 2.0
                x_box, box_top_y, w_box, h_box = cv2.boundingRect(c)
                y_baseline_droplet_box = box_top_y + h_box
                hull = cv2.convexHull(c)
                x_center_box = x_box + w_box // 2
                y_limit_center = self.m_baseline * x_center_box + self.c_baseline
                if not self.impact_detected:
                    d['falling_areas'].append(area_current_px)
                    d['times'].append(self.frame_id * p['dt'])
                    d['positions'].append(yc)
                    if len(c) >= 5:
                        ellipse = cv2.fitEllipse(c)
                        d['preimpact_diameter'] = (ellipse[1][0] + ellipse[1][1]) / 2 * p['scale']
                        cv2.ellipse(frame, ellipse, (255, 0, 0), 2)
                    cv2.circle(frame, (int(xc), int(yc)), 3, (0, 255, 0), -1)
                    if abs(y_baseline_droplet_box - y_limit_center) < 5:
                        self.impact_detected = True
                else:
                    points_on_baseline = []
                    for pt in c:
                        px, py = (pt[0][0], pt[0][1])
                        expected_y = self.m_baseline * px + self.c_baseline
                        if abs(py - expected_y) <= 3:
                            points_on_baseline.append((px, int(expected_y)))
                    if len(points_on_baseline) >= 2:
                        points_on_baseline = sorted(points_on_baseline, key=lambda pt: pt[0])
                        p_left = points_on_baseline[0]
                        p_right = points_on_baseline[-1]
                        diameter_pixel = np.sqrt((p_right[0] - p_left[0]) ** 2 + (p_right[1] - p_left[1]) ** 2)
                        diameter_mm = diameter_pixel * p['scale']
                        beta = diameter_mm / d['preimpact_diameter'] if np.isfinite(d['preimpact_diameter']) and d['preimpact_diameter'] > 0 else float('nan')
                        area_mm2 = area_current_px * p['scale'] ** 2
                        time_current = self.frame_id * p['dt']
                        top_point = tuple(hull[hull[:, :, 1].argmin()][0])
                        baseline_y_at_top_x = self.m_baseline * top_point[0] + self.c_baseline
                        height_pixel = abs(baseline_y_at_top_x - top_point[1])
                        height_mm = height_pixel * p['scale']
                        last_d = d.get('last_diam_val')
                        dd_dt = (diameter_mm - last_d) / p['dt'] if last_d is not None else 0.0
                        d['last_diam_val'] = diameter_mm
                        if diameter_pixel > d['max_w_px']:
                            d['max_w_px'] = diameter_pixel
                        cv2.drawContours(frame, [hull], -1, (0, 255, 0), thick_cnt)
                        cv2.line(frame, p_left, p_right, (0, 0, 255), thick_baseline)
                        cv2.line(frame, top_point, (top_point[0], int(baseline_y_at_top_x)), (255, 0, 255), thick_hgt)
                        self.tree.insert('', 'end', values=(f'{time_current:.5f}', '-', f'{diameter_mm:.3f}', f'{beta:.3f}', f'{height_mm:.3f}', f'{area_mm2:.3f}', f'{dd_dt:.3f}'))
                    else:
                        diameter_mm = 0.0
                        beta = 0.0
                        time_current = self.frame_id * p['dt']
                        d['last_diam_val'] = None
                        cv2.drawContours(frame, [hull], -1, (0, 0, 255), 1)
                        self.tree.insert('', 'end', values=(f'{time_current:.5f}', '-', '0.000', '0.000', '-', '-', '-'))
        self.display_frame(frame, update_original=True)
        self.frame_id += 1
        self.after(1, self.process_impact_frame_four)

    def configure_physical_parameters(self):
        display_names = {'fps_real': 'Real Frames Per Second (FPS)', 'scale': 'Scale (mm/pixel)', 'minimum_falling_area': 'Minimum Falling Area (px²)', 'minimum_post_impact_area': 'Minimum Post-Impact Area (px²)', 'dt': 'Time Step (calculated from FPS)', 'reference_frames_before_impact': 'Reference Frames Before Impact', 'tolerance': 'Base Line Tolerance (px)', 'gray_thresh': 'Grayscale Threshold', 'density': 'Fluid Density (kg/m³)', 'viscosity': 'Dynamic Viscosity (Pa·s)', 'tension': 'Surface Tension (N/m)'}
        default_values = {'fps_real': 10000.0, 'scale': 0.01, 'minimum_falling_area': 20.0, 'minimum_post_impact_area': 50.0, 'dt': 1 / 10000.0, 'reference_frames_before_impact': 3, 'tolerance': 3.0, 'gray_thresh': 5.0, 'density': 1000.0, 'viscosity': 0.001, 'tension': 0.072}
        dialog = tk.Toplevel(self)
        dialog.title('Analysis Parameters Configuration')
        dialog.geometry('450x500')
        dialog.grab_set()
        entries = {}
        for i, (key, value) in enumerate(default_values.items()):
            tk.Label(dialog, text=f'{display_names[key]}:').grid(row=i, column=0, padx=20, pady=5, sticky='e')
            entry = tk.Entry(dialog)
            entry.insert(0, str(value))
            entry.grid(row=i, column=1, padx=20, pady=5)
            entries[key] = entry
        params = {}

        def confirm():
            try:
                for key in default_values:
                    value = float(entries[key].get())
                    if not math.isfinite(value):
                        raise ValueError(f"{key} must be finite")
                    if key in {'fps_real', 'scale', 'density', 'viscosity', 'tension'} and value <= 0:
                        raise ValueError(f"{key} must be greater than zero")
                    if key in {'minimum_falling_area', 'minimum_post_impact_area', 'reference_frames_before_impact', 'tolerance'} and value < 0:
                        raise ValueError(f"{key} must not be negative")
                    params[key] = value
                # The recording acquisition frame rate determines elapsed time.
                params['dt'] = 1.0 / params['fps_real']
                dialog.destroy()
            except ValueError as error:
                messagebox.showerror('Invalid parameters', str(error), parent=dialog)

        tk.Button(dialog, text='Confirm and Continue', command=confirm, height=2, width=20).grid(row=len(default_values), columnspan=2, pady=25)
        self.wait_window(dialog)
        return params if params else None

    def show_dimensionless_results(self, v, d_mean, re, we, oh, area_pre):
        result_win = tk.Toplevel(self)
        result_win.title('Physical Analysis Results')
        result_win.geometry('350x380')
        result_win.update_idletasks()
        result_win.wait_visibility()
        result_win.grab_set()
        results = [('Impact Velocity (v):', f'{v:.4f} m/s'), ('Mean Pre-impact Diameter (D):', f'{d_mean:.4f} mm'), ('Reynolds Number (Re):', f'{re:.2f}'), ('Weber Number (We):', f'{we:.2f}'), ('Ohnesorge Number (Oh):', f'{oh:.4f}'), ('Mean Pre-Impact Projected Area:', f'{area_pre:.2f} mm²\n')]
        for i, (label, val) in enumerate(results):
            tk.Label(result_win, text=label, font=('Arial', 10, 'bold')).grid(row=i, column=0, padx=20, pady=10, sticky='e')
            tk.Label(result_win, text=val, font=('Arial', 10)).grid(row=i, column=1, padx=20, pady=10, sticky='w')
        tk.Button(result_win, text='Close', command=result_win.destroy, width=15).grid(row=6, columnspan=2, pady=15)

    def select_baseline_manually(self, path_video):
        cap = cv2.VideoCapture(path_video)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_current_idx = 0
        points = []
        line_params = {'p1': (0, 300), 'p2': (1000, 300)}
        name_window = 'A/D: Frame | 2 Clicks: Define Inclined Line | ENTER: Confirm'

        def get_frame(idx):
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            return frame if ret else None
        example_frame = get_frame(frame_current_idx)
        temp_img = example_frame.copy()

        def click_event(event, x, y, flags, param):
            nonlocal temp_img, points
            if event == cv2.EVENT_LBUTTONDOWN:
                points.append((x, y))
                cv2.circle(temp_img, (x, y), 4, (0, 255, 0), -1)
                if len(points) == 2:
                    temp_img = example_frame.copy()
                    cv2.line(temp_img, points[0], points[1], (0, 0, 255), 2)
                    line_params['p1'], line_params['p2'] = (points[0], points[1])
                    points = []
                cv2.imshow(name_window, temp_img)
        cv2.namedWindow(name_window)
        cv2.setMouseCallback(name_window, click_event)
        while True:
            display_img = temp_img.copy()
            cv2.putText(display_img, f'Frame: {frame_current_idx}/{total_frames - 1}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.imshow(name_window, display_img)
            key = cv2.waitKey(0) & 255
            if key in [ord('d'), ord('D'), ord('a'), ord('A')]:
                if key in [ord('d'), ord('D')] and frame_current_idx < total_frames - 1:
                    frame_current_idx += 1
                elif key in [ord('a'), ord('A')] and frame_current_idx > 0:
                    frame_current_idx -= 1
                example_frame = get_frame(frame_current_idx)
                temp_img = example_frame.copy()
                cv2.line(temp_img, line_params['p1'], line_params['p2'], (0, 0, 255), 2)
            elif key == 13 or key == 27 or cv2.getWindowProperty(name_window, cv2.WND_PROP_VISIBLE) < 1:
                break
        cap.release()
        cv2.destroyWindow(name_window)
        return line_params
