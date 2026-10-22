from __future__ import annotations
import os
import cv2
import customtkinter as ctk
import matplotlib.pyplot as plt
from tkinter import filedialog
from tkinter import messagebox


class VideoToolsMixin:

    def generate_video_sequence(self):
        if not hasattr(self, 'video_path') or not self.video_path or (not os.path.exists(self.video_path)):
            messagebox.showwarning('Warning', 'No valid video has been loaded.')
            return
        config_win = ctk.CTkToplevel(self)
        config_win.title('Frame Extraction Settings')
        config_win.geometry('420x520')
        config_win.attributes('-topmost', True)
        config_win.update()
        config_win.grab_set()
        ctk.CTkLabel(config_win, text='Video Extraction Settings', font=('Roboto', 16, 'bold')).pack(pady=10)
        form_frame = ctk.CTkFrame(config_win)
        form_frame.pack(fill='both', expand=True, padx=15, pady=5)
        ctk.CTkLabel(form_frame, text='Initial Contact Frame (t = 0 ms):', font=('Roboto', 12, 'bold')).pack(anchor='w', padx=10, pady=(10, 2))
        contact_frame_entry = ctk.CTkEntry(form_frame)
        val_default_frame = getattr(self, 'initial_contact_frame', 9)
        contact_frame_entry.insert(0, str(val_default_frame))
        contact_frame_entry.pack(fill='x', padx=10, pady=2)
        ctk.CTkLabel(form_frame, text='Target Times (ms, separated by comma):', font=('Roboto', 12, 'bold')).pack(anchor='w', padx=10, pady=(10, 2))
        entry_times = ctk.CTkEntry(form_frame)
        entry_times.insert(0, '0.0, 0.2, 0.5, 1.0, 2.0, 4.0, 7.0, 10.0, 15.0')
        entry_times.pack(fill='x', padx=10, pady=2)
        ctk.CTkLabel(form_frame, text='Crop ROI (ymin, ymax, xmin, xmax):', font=('Roboto', 12, 'bold')).pack(anchor='w', padx=10, pady=(10, 2))
        roi_grid = ctk.CTkFrame(form_frame, fg_color='transparent')
        roi_grid.pack(fill='x', padx=10, pady=2)
        ctk.CTkLabel(roi_grid, text='ymin:').grid(row=0, column=0, padx=2, pady=2, sticky='e')
        entry_ymin = ctk.CTkEntry(roi_grid, width=70)
        entry_ymin.insert(0, '0')
        entry_ymin.grid(row=0, column=1, padx=5, pady=2)
        ctk.CTkLabel(roi_grid, text='ymax:').grid(row=0, column=2, padx=2, pady=2, sticky='e')
        entry_ymax = ctk.CTkEntry(roi_grid, width=70)
        entry_ymax.insert(0, '350')
        entry_ymax.grid(row=0, column=3, padx=5, pady=2)
        ctk.CTkLabel(roi_grid, text='xmin:').grid(row=1, column=0, padx=2, pady=2, sticky='e')
        entry_xmin = ctk.CTkEntry(roi_grid, width=70)
        entry_xmin.insert(0, '100')
        entry_xmin.grid(row=1, column=1, padx=5, pady=2)
        ctk.CTkLabel(roi_grid, text='xmax:').grid(row=1, column=2, padx=2, pady=2, sticky='e')
        entry_xmax = ctk.CTkEntry(roi_grid, width=70)
        entry_xmax.insert(0, '800')
        entry_xmax.grid(row=1, column=3, padx=5, pady=2)

        def executar_processamento():
            try:
                initial_contact_frame = int(contact_frame_entry.get().strip())
                times_alvo_ms = [float(t.strip()) for t in entry_times.get().split(',') if t.strip()]
                ymin = int(entry_ymin.get().strip())
                ymax = int(entry_ymax.get().strip())
                xmin = int(entry_xmin.get().strip())
                xmax = int(entry_xmax.get().strip())
                crop_roi = [ymin, ymax, xmin, xmax]
            except ValueError:
                messagebox.showerror('Input Error', 'Fill all fields with valid numeric values.')
                return
            self.initial_contact_frame = initial_contact_frame
            output_file = filedialog.asksaveasfilename(title='Save Image Sequence', defaultextension='.png', filetypes=[('PNG Image', '*.png'), ('JPEG Image', '*.jpg'), ('All Files', '*.*')])
            if not output_file:
                return
            config_win.destroy()
            fps_gravacao = 10000.0
            source_fps = 30.0
            frames_para_extrair = []
            actual_times_ms = []
            for t_ms in times_alvo_ms:
                source_frame_offset = int(round(t_ms / 1000.0 * fps_gravacao))
                source_frame_index = initial_contact_frame + source_frame_offset
                t_real = (source_frame_index - initial_contact_frame) / fps_gravacao * 1000.0
                frames_para_extrair.append(source_frame_index)
                actual_times_ms.append(t_real)
            cap = cv2.VideoCapture(self.video_path)
            if not cap.isOpened():
                messagebox.showerror('Error', f'Unable to open the video:\n{self.video_path}')
                return
            images_extraidas = []
            for idx in frames_para_extrair:
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ret, frame = cap.read()
                if not ret:
                    print(f'Aviso: Unable to read frame {idx}. End of video reached.')
                    break
                if len(frame.shape) == 3:
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                if crop_roi:
                    ymin_c, ymax_c, xmin_c, xmax_c = crop_roi
                    frame = frame[ymin_c:ymax_c, xmin_c:xmax_c]
                images_extraidas.append(frame)
            cap.release()
            if not images_extraidas:
                messagebox.showerror('Error', 'No frames could be extracted from the video.')
                return
            num_frames = len(images_extraidas)
            fig, axes = plt.subplots(1, num_frames, figsize=(2 * num_frames, 3.0), dpi=300)
            if num_frames == 1:
                axes = [axes]
            for i, (img, t_ms) in enumerate(zip(images_extraidas, actual_times_ms)):
                ax = axes[i]
                if len(img.shape) == 2 or img.shape[2] == 1:
                    ax.imshow(img, cmap='gray')
                else:
                    ax.imshow(img)
                ax.text(0.05, 0.9, f'{t_ms:.1f} ms', transform=ax.transAxes, color='white', fontsize=8, fontweight='bold', bbox=dict(boxstyle='round,pad=0.2', facecolor='black', alpha=0.6))
                ax.axis('off')
            plt.subplots_adjust(wspace=0.02, hspace=0)
            plt.tight_layout()
            plt.savefig(output_file, bbox_inches='tight', pad_inches=0.05)
            plt.show()
            messagebox.showinfo('Success', f'Sequence panel saved to:\n{output_file}')
        ctk.CTkButton(config_win, text='Generate Panel', command=executar_processamento, fg_color='#1f538d').pack(pady=15, padx=20, fill='x')

    def generate_masked_video_sequence(self):
        if not hasattr(self, 'video_path') or not self.video_path or (not os.path.exists(self.video_path)):
            messagebox.showwarning('Warning', 'No valid video was loaded into the system!')
            return
        config_win = ctk.CTkToplevel(self)
        config_win.title('Frame Panel - Method 4 (Drop Impact)')
        config_win.geometry('420x550')
        config_win.attributes('-topmost', True)
        config_win.update()
        config_win.grab_set()
        ctk.CTkLabel(config_win, text='Extraction with Mask (Method 4)', font=('Roboto', 16, 'bold')).pack(pady=10)
        form_frame = ctk.CTkFrame(config_win)
        form_frame.pack(fill='both', expand=True, padx=15, pady=5)
        ctk.CTkLabel(form_frame, text='Initial Contact Frame (t = 0 ms):', font=('Roboto', 12, 'bold')).pack(anchor='w', padx=10, pady=(10, 2))
        contact_frame_entry = ctk.CTkEntry(form_frame)
        val_default_frame = getattr(self, 'initial_contact_frame', 9)
        contact_frame_entry.insert(0, str(val_default_frame))
        contact_frame_entry.pack(fill='x', padx=10, pady=2)
        ctk.CTkLabel(form_frame, text='Target Times (ms, comma-separated):', font=('Roboto', 12, 'bold')).pack(anchor='w', padx=10, pady=(10, 2))
        entry_times = ctk.CTkEntry(form_frame)
        entry_times.insert(0, '0.0, 0.2, 0.5, 1.0, 2.0, 4.0, 7.0, 10.0, 15.0')
        entry_times.pack(fill='x', padx=10, pady=2)
        ctk.CTkLabel(form_frame, text='Crop ROI (ymin, ymax, xmin, xmax):', font=('Roboto', 12, 'bold')).pack(anchor='w', padx=10, pady=(10, 2))
        roi_grid = ctk.CTkFrame(form_frame, fg_color='transparent')
        roi_grid.pack(fill='x', padx=10, pady=2)
        ctk.CTkLabel(roi_grid, text='ymin:').grid(row=0, column=0, padx=2, pady=2, sticky='e')
        entry_ymin = ctk.CTkEntry(roi_grid, width=70)
        entry_ymin.insert(0, str(getattr(self, 'crop_ymin', 0)))
        entry_ymin.grid(row=0, column=1, padx=5, pady=2)
        ctk.CTkLabel(roi_grid, text='ymax:').grid(row=0, column=2, padx=2, pady=2, sticky='e')
        entry_ymax = ctk.CTkEntry(roi_grid, width=70)
        entry_ymax.insert(0, str(getattr(self, 'crop_ymax', 350)))
        entry_ymax.grid(row=0, column=3, padx=5, pady=2)
        ctk.CTkLabel(roi_grid, text='xmin:').grid(row=1, column=0, padx=2, pady=2, sticky='e')
        entry_xmin = ctk.CTkEntry(roi_grid, width=70)
        entry_xmin.insert(0, str(getattr(self, 'crop_xmin', 100)))
        entry_xmin.grid(row=1, column=1, padx=5, pady=2)
        ctk.CTkLabel(roi_grid, text='xmax:').grid(row=1, column=2, padx=2, pady=2, sticky='e')
        entry_xmax = ctk.CTkEntry(roi_grid, width=70)
        entry_xmax.insert(0, str(getattr(self, 'crop_xmax', 800)))
        entry_xmax.grid(row=1, column=3, padx=5, pady=2)

        def process_method_four_mask():
            try:
                initial_contact_frame = int(contact_frame_entry.get().strip())
                times_alvo_ms = [float(t.strip()) for t in entry_times.get().split(',') if t.strip()]
                ymin = int(entry_ymin.get().strip())
                ymax = int(entry_ymax.get().strip())
                xmin = int(entry_xmin.get().strip())
                xmax = int(entry_xmax.get().strip())
                crop_roi = [ymin, ymax, xmin, xmax]
            except ValueError:
                messagebox.showerror('Input Error', 'Please fill all fields with valid numbers!')
                return
            self.initial_contact_frame = initial_contact_frame
            self.crop_ymin, self.crop_ymax = (ymin, ymax)
            self.crop_xmin, self.crop_xmax = (xmin, xmax)
            output_file = filedialog.asksaveasfilename(title='Save Panel with Mask (Method 4)', defaultextension='.png', filetypes=[('PNG Image', '*.png'), ('JPEG Image', '*.jpg'), ('All Files', '*.*')])
            if not output_file:
                return
            config_win.destroy()
            fps_gravacao = getattr(self, 'fps', 10000.0)
            if hasattr(self, 'params') and 'fps_real' in self.params:
                fps_gravacao = float(self.params['fps_real'])
            frames_para_extrair = []
            actual_times_ms = []
            for t_ms in times_alvo_ms:
                offset_frames = int(round(t_ms / 1000.0 * fps_gravacao))
                idx_frame = initial_contact_frame + offset_frames
                t_real = (idx_frame - initial_contact_frame) / fps_gravacao * 1000.0
                frames_para_extrair.append(idx_frame)
                actual_times_ms.append(t_real)
            cap = cv2.VideoCapture(self.video_path)
            if not cap.isOpened():
                messagebox.showerror('Error', f'Could not open video:\n{self.video_path}')
                return
            masked_images = []
            m_baseline = getattr(self, 'm_baseline', 0)
            c_baseline = getattr(self, 'c_baseline', 0)
            for idx in frames_para_extrair:
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ret, frame = cap.read()
                if not ret:
                    continue
                h_f, w_f = frame.shape[:2]
                pt_start_baseline = (0, int(c_baseline))
                pt_end_baseline = (w_f, int(m_baseline * w_f + c_baseline))
                cv2.line(frame, pt_start_baseline, pt_end_baseline, (0, 255, 255), 1)
                if hasattr(self, 'm4_results_per_frame') and idx in self.m4_results_per_frame:
                    res_m4 = self.m4_results_per_frame[idx]
                    hull = res_m4.get('hull')
                    p_left = res_m4.get('p_left')
                    p_right = res_m4.get('p_right')
                    top_point = res_m4.get('top_point')
                    baseline_y_at_top_x = res_m4.get('baseline_y_at_top_x')
                    if hull is not None:
                        cv2.drawContours(frame, [hull], -1, (0, 255, 0), 2)
                    if p_left is not None and p_right is not None:
                        cv2.line(frame, tuple(p_left), tuple(p_right), (0, 0, 255), 3)
                    if top_point is not None and baseline_y_at_top_x is not None:
                        cv2.line(frame, tuple(top_point), (top_point[0], int(baseline_y_at_top_x)), (255, 0, 255), 2)
                else:
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    if hasattr(self, 'background_gray') and self.background_gray is not None and (gray.shape == self.background_gray.shape):
                        diff = cv2.absdiff(gray, self.background_gray)
                        clean = cv2.bilateralFilter(diff, 5, 75, 75)
                        _, mask = cv2.threshold(clean, 15, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                    else:
                        clean = cv2.bilateralFilter(frame, 5, 75, 75)
                        gray_clean = cv2.cvtColor(clean, cv2.COLOR_BGR2GRAY)
                        _, mask = cv2.threshold(gray_clean, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
                    for x in range(w_f):
                        y_limit = int(m_baseline * x + c_baseline)
                        if 0 <= y_limit < h_f:
                            mask[y_limit:, x] = 0
                    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    if cnts:
                        c = min(cnts, key=lambda ct: abs(cv2.moments(ct)['m10'] / (cv2.moments(ct)['m00'] + 1e-05) - w_f / 2))
                        min_area = self.params.get('min_area', 300) if hasattr(self, 'params') else 300
                        if cv2.contourArea(c) > min_area:
                            hull = cv2.convexHull(c)
                            cv2.drawContours(frame, [hull], -1, (0, 255, 0), 2)
                            points_on_baseline = []
                            for pt in c:
                                px, py = (pt[0][0], pt[0][1])
                                expected_y = m_baseline * px + c_baseline
                                if abs(py - expected_y) <= 3:
                                    points_on_baseline.append((px, int(expected_y)))
                            if len(points_on_baseline) >= 2:
                                points_on_baseline = sorted(points_on_baseline, key=lambda p: p[0])
                                p_left = points_on_baseline[0]
                                p_right = points_on_baseline[-1]
                                cv2.line(frame, p_left, p_right, (0, 0, 255), 3)
                if crop_roi:
                    ymin_c, ymax_c, xmin_c, xmax_c = crop_roi
                    frame_crop = frame[ymin_c:ymax_c, xmin_c:xmax_c].copy()
                else:
                    frame_crop = frame.copy()
                frame_rgb = cv2.cvtColor(frame_crop, cv2.COLOR_BGR2RGB)
                masked_images.append(frame_rgb)
            cap.release()
            if not masked_images:
                messagebox.showerror('Error', 'No frame could be processed.')
                return
            n_frames = len(masked_images)
            fig, axes = plt.subplots(1, n_frames, figsize=(3 * n_frames, 3.5), dpi=300)
            if n_frames == 1:
                axes = [axes]
            for i, (img, t_ms) in enumerate(zip(masked_images, actual_times_ms)):
                axes[i].imshow(img)
                ax = axes[i]
                if len(img.shape) == 2 or img.shape[2] == 1:
                    ax.imshow(img, cmap='gray')
                else:
                    ax.imshow(img)
                ax.text(0.05, 0.9, f'{t_ms:.1f} ms', transform=ax.transAxes, color='white', fontsize=8, fontweight='bold', bbox=dict(boxstyle='round,pad=0.2', facecolor='black', alpha=0.6))
                ax.axis('off')
            plt.tight_layout()
            plt.savefig(output_file, bbox_inches='tight', dpi=300)
            plt.close(fig)
            messagebox.showinfo('Success', f'Method 4 Panel saved at:\n{output_file}')
        ctk.CTkButton(form_frame, text='Generate Panel (Method 4)', fg_color='#28a745', hover_color='#218838', command=process_method_four_mask).pack(fill='x', padx=10, pady=15)
