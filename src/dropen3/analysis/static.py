from __future__ import annotations
import os
import cv2
import numpy as np
import scipy.optimize as spopt
from tkinter import filedialog
from tkinter import messagebox
from scipy.signal import savgol_filter
from dropen3.ui.point_selection import select_image_points
from dropen3.science.contact_angles import calculate_dropy_angle, draw_angle_arc, points_near_baseline, select_point_callback, split_sides


class StaticAnalysisMixin:

    def fitting(self):
        if self.img_result_original is None:
            from tkinter import messagebox
            messagebox.showwarning('Warning', 'Upload an image first!')
            return
        roi = cv2.selectROI('Select the Drop (Press ENTER)', self.img_result_original, fromCenter=False)
        cv2.destroyWindow('Select the Drop (Press ENTER)')
        x_roi, y_roi, w_roi, h_roi = roi
        if w_roi == 0 or h_roi == 0:
            return
        roi_img = self.img_result_original[y_roi:y_roi + h_roi, x_roi:x_roi + w_roi]
        gray = cv2.cvtColor(roi_img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        if not contours:
            self.lbl_status.configure(text='Error: No outline in ROI.')
            return
        cnt = max(contours, key=cv2.contourArea)
        points = cnt.reshape(-1, 2)
        x_data = (points[:, 0] + x_roi).astype(float)
        y_data = (points[:, 1] + y_roi).astype(float)
        x_m, y_m = (np.mean(x_data), np.mean(y_data))

        def calc_R(xc, yc):
            return np.sqrt((x_data - xc) ** 2 + (y_data - yc) ** 2)

        def f_2(c):
            Ri = calc_R(*c)
            return Ri - Ri.mean()
        center_estimate = (x_m, y_m)
        center_2, _ = spopt.leastsq(f_2, center_estimate)
        xc, yc = center_2
        R = calc_R(*center_2).mean()
        y_baseline = np.max(y_data)
        x_min, x_max = (np.min(x_data), np.max(x_data))
        xbas1, ybas1 = (x_min - xc, y_baseline - yc)
        xbas2, ybas2 = (x_max - xc, y_baseline - yc)
        dx, dy = (xbas2 - xbas1, ybas2 - ybas1)
        dr = np.sqrt(dx ** 2 + dy ** 2)
        D = xbas1 * ybas2 - xbas2 * ybas1
        discriminant = R ** 2 * dr ** 2 - D ** 2
        if discriminant < 0:
            self.lbl_status.configure(text='Error: Invalid intersection in ROI.')
            return
        delta_root = np.sqrt(discriminant)
        sign_dy = np.sign(dy) if dy != 0 else 1
        pt1_x = (D * dy + sign_dy * dx * delta_root) / dr ** 2 + xc
        pt2_x = (D * dy - sign_dy * dx * delta_root) / dr ** 2 + xc
        pt1_y = (-D * dx + abs(dy) * delta_root) / dr ** 2 + yc
        pt2_y = (-D * dx - abs(dy) * delta_root) / dr ** 2 + yc
        theta1 = abs(np.degrees(-np.pi / 2 + np.arctan2(yc - pt1_y, xc - pt1_x)))
        theta2 = abs(np.degrees(np.pi / 2 + np.arctan2(yc - pt2_y, xc - pt2_x)))
        vis_img = self.img_result_original.copy()
        cv2.rectangle(vis_img, (x_roi, y_roi), (x_roi + w_roi, y_roi + h_roi), (0, 255, 0), 1)
        cv2.circle(vis_img, (int(xc), int(yc)), int(R), (255, 0, 0), 2)
        cv2.line(vis_img, (int(x_min), int(y_baseline)), (int(x_max), int(y_baseline)), (0, 255, 255), 2)
        cv2.circle(vis_img, (int(pt1_x), int(pt1_y)), 6, (0, 0, 255), -1)
        cv2.circle(vis_img, (int(pt2_x), int(pt2_y)), 6, (0, 0, 255), -1)
        self.display_frame(vis_img, update_original=False)
        self.lbl_status.configure(text=f'WCA (ROI): L={theta1:.2f}° | R={theta2:.2f}°')
        self.tree.insert('', 'end', values=(len(self.tree.get_children()) + 1, f'{theta1:.2f}', f'{theta2:.2f}', 'Circle Fit (ROI)'))

    def run_standard_static_analysis(self):
        method_current = 'WCA_NORMAL'
        if self.last_method_selected != method_current:
            for item in self.tree.get_children():
                self.tree.delete(item)
            self.last_method_selected = method_current
        path = filedialog.askopenfilename(filetypes=[('Images', '*.jpg *.png *.jpeg'), ('All', '*.*')])
        if not path:
            return
        self.video_path = path
        source_file_name = os.path.basename(path)
        img = cv2.imread(path)
        if img is None:
            return
        self.current_mode = 'WCA'
        orig = img.copy()
        while True:
            r = cv2.selectROI('Select ROI - [Enter] Confirm | [ESC] Cancel', img, showCrosshair=True)
            cv2.destroyWindow('Select ROI - [Enter] Confirm | [ESC] Cancel')
            x_roi, y_roi, w_roi, h_roi = r
            if w_roi == 0 or h_roi == 0:
                resposta = messagebox.askyesno('Invalid ROI', 'No region was selected.\nDo you want to try selecting the ROI again?')
                if resposta:
                    continue
                else:
                    return
            roi_preview = img[y_roi:y_roi + h_roi, x_roi:x_roi + w_roi].copy()
            cv2.putText(roi_preview, 'Confirm? [Y]-Yes | [R]-Redo ROI', (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            cv2.imshow('Confirm ROI', roi_preview)
            key = cv2.waitKey(0)
            cv2.destroyWindow('Confirm ROI')
            if key == ord('r') or key == ord('R'):
                continue
            else:
                break
        roi = img[y_roi:y_roi + h_roi, x_roi:x_roi + w_roi]
        points_baseline = select_image_points(roi, 2, 'Select Base')
        if points_baseline is None:
            return
        p1, p2 = points_baseline
        y_baseline = max(p1[1], p2[1])
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 30, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
        if not contours:
            return
        contour = max(contours, key=cv2.contourArea).reshape(-1, 2)
        points = points_near_baseline(contour, y_baseline, self.tangent_static)
        roi_debug = roi.copy()
        for x, y in points:
            cv2.circle(roi_debug, (x, y), 1, (255, 0, 0), -1)
        cv2.imshow('Selected Points', roi_debug)
        cv2.waitKey(0)
        cv2.destroyWindow('Selected Points')
        left, right = split_sides(points)
        left, right = (left[:40], right[:40])
        try:
            angle_left, slope_left = calculate_dropy_angle(left, 'left')
            angle_right, slope_right = calculate_dropy_angle(right, 'right')
            angle_mean = (angle_left + angle_right) / 2
            cv2.drawContours(orig, [contour + [x_roi, y_roi]], -1, (0, 255, 0), self.thick_static_contour)
            cv2.line(orig, (x_roi + p1[0], y_roi + p1[1]), (x_roi + p2[0], y_roi + p2[1]), (0, 0, 255), self.thick_static_baseline)
            for p, slope in zip([p1, p2], [slope_left, slope_right]):
                dx = 40
                dy = int(slope * dx)
                cv2.line(orig, (x_roi + int(p[0] - dx), y_roi + int(p[1] - dy)), (x_roi + int(p[0] + dx), y_roi + int(p[1] + dy)), (0, 255, 255), self.thick_static_tangent)
            draw_angle_arc(orig, (x_roi + p1[0], y_roi + p1[1]), angle_left, 'left')
            draw_angle_arc(orig, (x_roi + p2[0], y_roi + p2[1]), angle_right, 'right')
            cv2.putText(orig, f'Left: {angle_left:.2f}', (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            cv2.putText(orig, f'Right: {angle_right:.2f}', (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            cv2.putText(orig, f'Average: {angle_mean:.2f}', (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            self.display_frame(orig)
            self.lbl_status.configure(text=f'Analysis Completed: Average {angle_mean:.2f}°')
            self.tree.insert('', 'end', values=(source_file_name, f'{angle_left:.2f}', f'{angle_right:.2f}', f'{angle_mean:.2f}'))
        except Exception as e:
            messagebox.showerror('Error', str(e))

    def draw_fitted_curve(self, img, coef, points_y, offset_x, offset_y, color=(255, 255, 0)):
        y_min = int(min(points_y))
        y_max = int(max(points_y))
        curve_points = []
        for y_val in range(y_min, y_max + 1):
            x_val = coef[0] * y_val ** 2 + coef[1] * y_val + coef[2]
            curve_points.append([int(x_val + offset_x), int(y_val + offset_y)])
        if len(curve_points) > 1:
            points_array = np.array(curve_points, np.int32).reshape((-1, 1, 2))
            cv2.polylines(img, [points_array], False, color, 1)

    def draw_tangent(self, img, point_baseline, slope_dx_dy, side, color=(255, 0, 255)):
        x0, y0 = point_baseline
        length = 50
        if side == 'left':
            dy = -length
            dx = dy * slope_dx_dy
        else:
            dy = -length
            dx = dy * slope_dx_dy
        p2 = (int(x0 + dx), int(y0 + dy))
        cv2.line(img, (int(x0), int(y0)), p2, color, 1)

    def draw_angle_arc(self, img, center, angle_value, side, color=(0, 255, 0)):
        radius = 30
        espessura = 1
        if side == 'left':
            start_angle = 0
            end_angle = -angle_value
        else:
            start_angle = 180
            end_angle = 180 + angle_value
        cv2.ellipse(img, center, (radius, radius), 0, start_angle, end_angle, color, espessura)

    def run_advanced_static_analysis(self):
        method_current = 'WCA_ADVANCED'
        if self.last_method_selected != method_current:
            for item in self.tree.get_children():
                self.tree.delete(item)
            self.last_method_selected = method_current
        path = filedialog.askopenfilename(filetypes=[('Images', '*.jpg *.png *.jpeg'), ('All', '*.*')])
        if not path:
            return
        self.video_path = path
        source_file_name = os.path.basename(path)
        img = cv2.imread(path)
        if img is None:
            return
        orig = img.copy()
        r = cv2.selectROI('Select Region of Interest', img, showCrosshair=True)
        cv2.destroyWindow('Select Region of Interest')
        x_roi, y_roi, w_roi, h_roi = r
        if w_roi == 0 or h_roi == 0:
            return
        roi = img[y_roi:y_roi + h_roi, x_roi:x_roi + w_roi]
        points_baseline = select_image_points(roi, 2, 'Select Baseline')
        if points_baseline is None:
            return
        p1, p2 = points_baseline
        y_baseline = max(p1[1], p2[1])
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        v = np.median(gray)
        sigma = 0.33
        lower = int(max(0, (1.0 - sigma) * v))
        upper = int(min(255, (1.0 + sigma) * v))
        edges = cv2.Canny(gray, lower, upper)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        if not contours:
            return
        contours_valid = []
        for c in contours:
            points = c.reshape(-1, 2)
            if len(points) > 50:
                width = np.max(points[:, 0]) - np.min(points[:, 0])
                contours_valid.append((width, points))
        if not contours_valid:
            return
        contour = max(contours_valid, key=lambda item: item[0])[1]
        tolerance_height = self.tangent_static_pol
        minimum_points_obrigatorio = max(10, self.tangent_static_baseline_points)
        for tentativa in range(3):
            lista_points = [p for p in contour if abs(p[1] - y_baseline) < tolerance_height]
            if len(lista_points) >= minimum_points_obrigatorio:
                break
            tolerance_height = int(tolerance_height * 1.5)
        if len(lista_points) < minimum_points_obrigatorio:
            messagebox.showerror('Detection Error', f"Too few points near the baseline ({len(lista_points)} found).\n\nSuggestions:\n1. Improve image contrast and illumination.\n2. Select the substrate baseline at the droplet contact location.\n3. Increase 'tangent_static_pol' in the settings.")
            return
        points = np.array(lista_points)
        x_mean = np.mean(points[:, 0])
        left = points[points[:, 0] < x_mean]
        right = points[points[:, 0] >= x_mean]
        left = left[np.argsort(left[:, 1])]
        right = right[np.argsort(right[:, 1])]

        def suavizar(p):
            if len(p) < 11:
                return p
            x = savgol_filter(p[:, 0], 11, 3)
            y = savgol_filter(p[:, 1], 11, 3)
            return np.column_stack((x, y))
        left = suavizar(left)
        right = suavizar(right)

        def calculate_angle(points, side):
            n = min(30, len(points))
            points = points[np.argsort(points[:, 1])][:n]
            x = points[:, 0]
            y = points[:, 1]
            coef = np.polyfit(y, x, 2)
            y_contato = np.max(y)
            x_contato = coef[0] * y_contato ** 2 + coef[1] * y_contato + coef[2]
            dx_dy = 2 * coef[0] * y_contato + coef[1]
            if dx_dy != 0:
                slope_v = 1 / abs(dx_dy)
                angle_baseline = np.degrees(np.arctan(slope_v))
            else:
                angle_baseline = 90.0
            if side == 'left':
                angle = 180 - angle_baseline if dx_dy > 0 else angle_baseline
            else:
                angle = 180 - angle_baseline if dx_dy < 0 else angle_baseline
            return (angle, dx_dy, (x_contato, y_contato), coef, y)
        angle_left, slope_left, pt_left, coef_left, y_left = calculate_angle(left, 'left')
        angle_right, slope_right, pt_right, coef_right, y_right = calculate_angle(right, 'right')
        angle_mean = (angle_left + angle_right) / 2
        cv2.drawContours(orig, [contour + [x_roi, y_roi]], -1, (0, 255, 0), self.thick_static_contour)
        cv2.line(orig, (x_roi + p1[0], y_roi + p1[1]), (x_roi + p2[0], y_roi + p2[1]), (0, 0, 255), self.thick_static_baseline)
        self.draw_fitted_curve(orig, coef_left, y_left, x_roi, y_roi, (255, 255, 0))
        self.draw_fitted_curve(orig, coef_right, y_right, x_roi, y_roi, (255, 255, 0))
        pt_left_global = (pt_left[0] + x_roi, pt_left[1] + y_roi)
        pt_right_global = (pt_right[0] + x_roi, pt_right[1] + y_roi)
        point_baseline_left = (int(pt_left[0] + x_roi), int(pt_left[1] + y_roi))
        point_baseline_right = (int(pt_right[0] + x_roi), int(pt_right[1] + y_roi))
        self.draw_angle_arc(orig, point_baseline_left, angle_left, 'left')
        self.draw_angle_arc(orig, point_baseline_right, angle_right, 'right')
        self.draw_tangent(orig, point_baseline_left, slope_left, 'left')
        self.draw_tangent(orig, point_baseline_right, slope_right, 'right')
        cv2.putText(orig, f'Left: {angle_left:.2f}', (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)
        cv2.putText(orig, f'Right: {angle_right:.2f}', (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)
        cv2.putText(orig, f'Average: {angle_mean:.2f}', (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        edges_bgr = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
        cv2.line(edges_bgr, (p1[0], int(y_baseline)), (p2[0], int(y_baseline)), (0, 0, 255), 2)
        roi_final_desenhada = orig[y_roi:y_roi + h_roi, x_roi:x_roi + w_roi]
        debug_horizontal = np.hstack((edges_bgr, roi_final_desenhada))
        cv2.putText(debug_horizontal, '[ENTER]: Confirm | [ESC]: Cancel', (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1, cv2.LINE_AA)
        cv2.imshow('Visual Debug - Analysis Pipeline', debug_horizontal)
        key = cv2.waitKey(0) & 255
        cv2.destroyWindow('Visual Debug - Analysis Pipeline')
        if key == 27:
            return
        self.display_frame(orig)
        self.tree.insert('', 'end', values=(source_file_name, f'{angle_left:.2f}', f'{angle_right:.2f}', f'{angle_mean:.2f}', 'N/A'))

    def select_three_points(self, img_roi):
        return select_image_points(img_roi, 3, 'Select 3 Points (Base 1, Base 2, Angle)')

    def run_manual_analysis(self):
        path = filedialog.askopenfilename(filetypes=[('Images', '*.jpg *.png *.jpeg'), ('All', '*.*')])
        if not path:
            return
        self.video_path = path
        file_name = os.path.basename(path)
        img = cv2.imread(path)
        if img is None:
            return
        orig = img.copy()
        r = cv2.selectROI('Select the Droplet Region', img, showCrosshair=True)
        cv2.destroyWindow('Select the Droplet Region')
        x_roi, y_roi, w_roi, h_roi = r
        if w_roi == 0 or h_roi == 0:
            return
        roi = img[y_roi:y_roi + h_roi, x_roi:x_roi + w_roi]
        points = self.select_three_points(roi)
        if points:
            p1, p2, p3 = points
            v_baseline = np.array([p1[0] - p2[0], p1[1] - p2[1]])
            v_face = np.array([p3[0] - p2[0], p3[1] - p2[1]])
            norm_b = np.linalg.norm(v_baseline)
            norm_f = np.linalg.norm(v_face)
            if norm_b > 0 and norm_f > 0:
                cos_theta = np.dot(v_baseline, v_face) / (norm_b * norm_f)
                angle_rad = np.arccos(np.clip(cos_theta, -1.0, 1.0))
                angle_deg = np.degrees(angle_rad)
                angle_left = 'N/A'
                angle_right = 'N/A'
                angle_mean = 'N/A'
                if p2[0] < p1[0]:
                    angle_left = angle_deg
                    side_label = 'Left'
                else:
                    angle_right = angle_deg
                    side_label = 'Right'
                self.tree.insert('', 'end', values=(file_name, f'{angle_left:.2f}' if isinstance(angle_left, float) else angle_left, f'{angle_right:.2f}' if isinstance(angle_right, float) else angle_right, 'Manual'))
                p1_g = (p1[0] + x_roi, p1[1] + y_roi)
                p2_g = (p2[0] + x_roi, p2[1] + y_roi)
                p3_g = (p3[0] + x_roi, p3[1] + y_roi)
                cv2.line(orig, p1_g, p2_g, (0, 0, 255), 2)
                cv2.line(orig, p2_g, p3_g, (255, 0, 255), 2)
                text = f'Ang: {angle_deg:.2f} deg'
                cv2.putText(orig, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                self.display_frame(orig)
