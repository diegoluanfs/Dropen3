from __future__ import annotations
import math
import cv2
import numpy as np
from tkinter import filedialog
from dropen3.ui.point_selection import select_video_points


class SprayAnalysisMixin:

    def run_spray_droplet_analysis(self):
        method_current = 'DROP_SPRAY'
        if self.last_method_selected != method_current:
            for item in self.tree.get_children():
                self.tree.delete(item)
            self.last_method_selected = method_current
        path = filedialog.askopenfilename(filetypes=[('Videos', '*.avi *.mp4 *.tif'), ('All files', '*.*')])
        if not path:
            return
        self.video_path = path
        self.params = self.configure_physical_parameters()
        cap_config = cv2.VideoCapture(path)
        total = int(cap_config.get(cv2.CAP_PROP_FRAME_COUNT))
        if total <= 0:
            cap_config.release()
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
        columns_spray = ('frame', 'time', 'droplets_before', 'droplets_after', 'total_droplets', 'diameter_mean_px', 'cone_angle_degrees')
        self.tree.configure(columns=columns_spray)
        for col in columns_spray:
            self.tree.heading(col, text=col.replace('_', ' ').title())
            self.tree.column(col, width=110, anchor='center')
        self.cap_vel = cv2.VideoCapture(path)
        self.current_mode = 'DROP'
        self.data = {'times': [], 'spray_angles': [], 'droplet_counts': [], 'size_distributions': []}
        self.frame_id = 0
        self.analysis_active = True
        self.vel_active = True
        if hasattr(self, 'lbl_status'):
            self.lbl_status.configure(text='Baseline set. Analyzing droplets and spray cone...')
        self.update_idletasks()
        self.process_spray_frame()

    def process_spray_frame(self):
        if not getattr(self, 'analysis_active', False) or not getattr(self, 'vel_active', False) or self.cap_vel is None:
            return
        p, d = (self.params, self.data)
        ret, frame = self.cap_vel.read()
        if not ret:
            self.cap_vel.release()
            self.vel_active = False
            if hasattr(self, 'lbl_status'):
                self.lbl_status.configure(text='Drop and spray contour analysis completed!')
            return
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        h_img, w_img = frame.shape[:2]
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        thresh_val = max(100, int(self.threshold_impact * 3))
        _, mask = cv2.threshold(blur, thresh_val, 255, cv2.THRESH_BINARY_INV)
        m_baseline = getattr(self, 'm_baseline', 0)
        c_baseline = getattr(self, 'c_baseline', 0)
        pt_start = (0, int(c_baseline))
        pt_end = (w_img, int(m_baseline * w_img + c_baseline))
        cv2.line(frame, pt_start, pt_end, (0, 255, 255), 2)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        droplets_before = 0
        droplets_after = 0
        diameters_droplets = []
        spray_left_next = None
        spray_right_next = None
        spray_left_far = None
        spray_right_far = None
        min_area_droplet = 5
        max_area_droplet = 2000
        for c in cnts:
            area = cv2.contourArea(c)
            if min_area_droplet < area < max_area_droplet:
                M = cv2.moments(c)
                if M['m00'] > 0:
                    cx = int(M['m10'] / M['m00'])
                    cy = int(M['m01'] / M['m00'])
                else:
                    x_b, y_b, w_b, h_b = cv2.boundingRect(c)
                    cx, cy = (x_b + w_b // 2, y_b + h_b // 2)
                y_baseline_no_x = m_baseline * cx + c_baseline
                diameter_eq = 2.0 * math.sqrt(area / math.pi)
                diameters_droplets.append(diameter_eq)
                if cy < y_baseline_no_x:
                    droplets_before += 1
                    cv2.drawContours(frame, [c], -1, (0, 255, 0), 1)
                else:
                    droplets_after += 1
                    cv2.drawContours(frame, [c], -1, (0, 0, 255), 1)
                    distance_from_baseline = cy - y_baseline_no_x
                    center_x = w_img // 2
                    if cx < center_x:
                        if spray_left_next is None or cy < spray_left_next[1]:
                            spray_left_next = (cx, cy)
                        if spray_left_far is None or cy > spray_left_far[1]:
                            spray_left_far = (cx, cy)
                    else:
                        if spray_right_next is None or cy < spray_right_next[1]:
                            spray_right_next = (cx, cy)
                        if spray_right_far is None or cy > spray_right_far[1]:
                            spray_right_far = (cx, cy)
                cv2.circle(frame, (cx, cy), 1, (255, 0, 0), -1)
        total_droplets = droplets_before + droplets_after
        cone_angle = 0.0
        if spray_left_next and spray_right_next and spray_left_far and spray_right_far:
            vertice_x = (spray_left_next[0] + spray_right_next[0]) / 2
            vertice_y = m_baseline * vertice_x + c_baseline
            v_left = (spray_left_far[0] - vertice_x, spray_left_far[1] - vertice_y)
            v_right = (spray_right_far[0] - vertice_x, spray_right_far[1] - vertice_y)
            angle_left = math.atan2(v_left[1], v_left[0]) * 180.0 / math.pi
            angle_right = math.atan2(v_right[1], v_right[0]) * 180.0 / math.pi
            cone_angle = abs(angle_right - angle_left)
            if cone_angle > 180:
                cone_angle = 360 - cone_angle
            cv2.line(frame, (int(vertice_x), int(vertice_y)), spray_left_far, (255, 0, 255), 2)
            cv2.line(frame, (int(vertice_x), int(vertice_y)), spray_right_far, (255, 0, 255), 2)
        diameter_mean_px = np.mean(diameters_droplets) if diameters_droplets else 0.0
        time_current = self.frame_id * p['dt']
        d['times'].append(time_current)
        d['spray_angles'].append(cone_angle)
        d['droplet_counts'].append(total_droplets)
        if diameters_droplets:
            d['size_distributions'].append(diameters_droplets)
        self.tree.insert('', 'end', values=(self.frame_id, f'{time_current:.5f}', droplets_before, droplets_after, total_droplets, f'{diameter_mean_px:.2f}', f'{cone_angle:.2f}'))
        self.display_frame(frame, update_original=True)
        self.frame_id += 1
        self.after(10, self.process_spray_frame)
