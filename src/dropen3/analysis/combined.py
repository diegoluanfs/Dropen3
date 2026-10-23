"""Combined spray and impact GUI workflow and reproducible exports."""
from __future__ import annotations

from dataclasses import asdict
import csv
import json
from pathlib import Path

import cv2
from tkinter import filedialog, messagebox

from dropen3.analysis.combined_core import CombinedSession
from dropen3.science.combined import Baseline, CombinedConfig
from dropen3.ui.point_selection import select_video_points


COMBINED_COLUMNS = (
    'Frame', 'Acquisition Time (s)', 'Contact-Relative Time (s)',
    'Visible Above Baseline', 'Visible Below Baseline',
    'Visible Secondary Droplets', 'Cumulative Track IDs',
    'Mean Secondary Diameter (px)', '2D Spray Envelope Angle (deg)',
    'Contact Width (mm)', 'Spreading Factor', 'Height (mm)',
    'Projected Silhouette Area (mm2)', 'Contact Width Rate (mm/s)',
    'Main Droplet Detected', 'Frame Status',
)


def row_values(row):
    return (row.frame_index, row.acquisition_time_s, row.contact_time_s,
            row.above_baseline_count, row.below_baseline_count,
            row.visible_secondary_count, row.cumulative_track_count,
            row.mean_secondary_diameter_px, row.spray_envelope_angle_deg,
            row.contact_width_mm, row.spreading_factor, row.height_mm,
            row.projected_area_mm2, row.contact_width_rate_mm_s,
            row.main_droplet_detected, row.status)


def select_reference_frame(capture, title='Select Reference Background'):
    """Pick an unmodified frame using cross-platform A/D and extended arrow codes."""
    total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    if total <= 0 or not capture.isOpened():
        return None
    index = 0
    cv2.namedWindow(title, cv2.WINDOW_NORMAL)
    try:
        while True:
            capture.set(cv2.CAP_PROP_POS_FRAMES, index)
            success, frame = capture.read()
            if not success:
                return None
            preview = frame.copy()
            cv2.putText(preview, f'Frame {index}/{total - 1} | A/D or arrows: navigate | Enter: select',
                        (8, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 1)
            cv2.imshow(title, preview)
            key = cv2.waitKeyEx(30)
            if key in (13, 10):
                return index, frame.copy()
            if key == 27 or cv2.getWindowProperty(title, cv2.WND_PROP_VISIBLE) < 1:
                return None
            if key in (ord('a'), ord('A'), 2424832, 65361):
                index = max(0, index - 1)
            elif key in (ord('d'), ord('D'), 2555904, 65363):
                index = min(total - 1, index + 1)
    finally:
        cv2.destroyWindow(title)


class CombinedAnalysisMixin:
    def run_combined_spray_impact_analysis(self):
        self.stop_combined_analysis()
        path = filedialog.askopenfilename(filetypes=[('Video files', '*.avi *.mp4 *.mov *.mkv'),
                                                      ('All files', '*.*')])
        if not path:
            return
        parameters = self.configure_physical_parameters()
        if not parameters:
            return
        try:
            configuration = CombinedConfig.from_legacy_parameters(parameters)
        except (ValueError, TypeError, KeyError) as error:
            messagebox.showerror('Invalid parameters', str(error))
            return
        capture = cv2.VideoCapture(path)
        if not capture.isOpened():
            messagebox.showerror('Video error', 'The selected video could not be opened.')
            return
        try:
            reference = select_reference_frame(capture)
            if reference is None:
                return
            reference_index, background = reference
            selected = select_video_points(capture, reference_index, 2,
                                           'Select Substrate Baseline')
            if selected is None:
                return
            selected_index, points = selected
            baseline = Baseline(points[0], points[1])
        except (ValueError, cv2.error) as error:
            messagebox.showerror('Configuration error', str(error))
            return
        finally:
            capture.release()
        self.video_path = path
        self.params = parameters
        self.points_baseline = points
        self.current_mode = 'SPRAY_IMPACT'
        self.last_method_selected = 'SPRAY_IMPACT_COMBINED'
        self.combined_source_configuration = (configuration, baseline, background, reference_index)
        self.combined_selected_baseline_frame = selected_index
        self.restart_combined_analysis()

    def restart_combined_analysis(self):
        self.stop_combined_analysis()
        source = getattr(self, 'combined_source_configuration', None)
        path = getattr(self, 'video_path', None)
        if source is None or not path:
            return
        if getattr(self, 'cap_vel', None) is not None:
            self.cap_vel.release()
        self.cap_vel = cv2.VideoCapture(path)
        if not self.cap_vel.isOpened():
            messagebox.showerror('Video error', 'The video could not be reopened.')
            return
        config, baseline, reference, index = source
        self.combined_session = CombinedSession(config, baseline, reference, index)
        self.combined_summary = None
        self.combined_after_id = None
        self.combined_frame_index = 0
        self.combined_total_frames = int(self.cap_vel.get(cv2.CAP_PROP_FRAME_COUNT))
        self.current_mode = 'SPRAY_IMPACT'
        self.last_method_selected = 'SPRAY_IMPACT_COMBINED'
        self.analysis_active = True
        self.vel_active = True
        self._configure_combined_columns()
        self._set_combined_progress(0)
        self._schedule_combined_next()

    def _configure_combined_columns(self, *, clear=True):
        self.tree.configure(columns=COMBINED_COLUMNS, show='headings')
        for column in COMBINED_COLUMNS:
            self.tree.heading(column, text=column)
            self.tree.column(column, width=max(145, min(230, len(column) * 7)),
                             stretch=False, anchor='center')
        if clear:
            for item in self.tree.get_children():
                self.tree.delete(item)
        if not getattr(self, 'combined_horizontal_scrollbar', None):
            from tkinter import ttk
            self.combined_horizontal_scrollbar = ttk.Scrollbar(
                self.table_container, orient='horizontal', command=self.tree.xview)
            self.tree.configure(xscrollcommand=self.combined_horizontal_scrollbar.set)
            self.combined_horizontal_scrollbar.pack(side='bottom', fill='x')

    def _set_combined_progress(self, fraction):
        if getattr(self, 'combined_progress_bar', None) is None:
            import customtkinter as ctk
            self.combined_progress_bar = ctk.CTkProgressBar(self.controls_panel, height=9)
            self.combined_progress_bar.pack(fill='x', padx=20, pady=(0, 4))
        self.combined_progress_bar.set(max(0.0, min(float(fraction), 1.0)))

    def _schedule_combined_next(self):
        if not getattr(self, 'analysis_active', False):
            return
        if getattr(self, 'combined_after_id', None) is not None:
            return
        self.combined_after_id = self.after(10, self._combined_frame_step)

    def _combined_frame_step(self):
        self.combined_after_id = None
        if not getattr(self, 'analysis_active', False) or self.current_mode != 'SPRAY_IMPACT':
            return
        capture = getattr(self, 'cap_vel', None)
        if capture is None or not capture.isOpened():
            self.finish_combined_analysis()
            return
        success, frame = capture.read()
        if not success:
            self.finish_combined_analysis()
            return
        frame_index = self.combined_frame_index
        try:
            row, overlay = self.combined_session.process(frame, frame_index)
        except (ValueError, cv2.error) as error:
            self.stop_combined_analysis()
            self.lbl_status.configure(text=f'Combined analysis failed at frame {frame_index}.')
            messagebox.showerror('Analysis error', f'Frame {frame_index}: {error}')
            return
        self.combined_frame_index += 1
        self.tree.insert('', 'end', values=['' if value is None else value for value in row_values(row)])
        self.display_frame(overlay, update_original=True)
        self._set_combined_progress(self.combined_frame_index / max(1, self.combined_total_frames))
        self.lbl_status.configure(text=f'Combined analysis: frame {frame_index + 1} / {self.combined_total_frames}')
        self._schedule_combined_next()

    def finish_combined_analysis(self):
        if getattr(self, 'combined_session', None) is None:
            return
        rows, summary = self.combined_session.finalize()
        self.combined_summary = summary
        # Rewrite rows with the scientifically defined first-contact time origin.
        self._configure_combined_columns()
        for row in rows:
            self.tree.insert('', 'end', values=['' if v is None else v for v in row_values(row)])
        self.analysis_active = False
        self.vel_active = False
        if getattr(self, 'cap_vel', None) is not None:
            self.cap_vel.release()
            self.cap_vel = None
        self._set_combined_progress(1)
        self.lbl_status.configure(text=(
            f'Combined analysis complete: {len(rows)} frames; '
            f'first contact: {summary.first_contact_frame if summary.first_contact_frame is not None else "not resolved"}. '
            'Measurements remain experimentally unvalidated.'))

    def pause_combined_analysis(self):
        self.analysis_active = False
        self.vel_active = False
        callback = getattr(self, 'combined_after_id', None)
        if callback is not None:
            self.after_cancel(callback)
            self.combined_after_id = None
        if hasattr(self, 'lbl_status'):
            self.lbl_status.configure(text='Combined analysis paused.')

    def resume_combined_analysis(self):
        if getattr(self, 'combined_session', None) is None:
            return
        if self.combined_summary is not None:
            self.restart_combined_analysis()
            return
        self.analysis_active = True
        self.vel_active = True
        self._schedule_combined_next()

    def stop_combined_analysis(self):
        callback = getattr(self, 'combined_after_id', None)
        if callback is not None:
            self.after_cancel(callback)
            self.combined_after_id = None
        self.analysis_active = False
        self.vel_active = False
        if getattr(self, 'cap_vel', None) is not None:
            self.cap_vel.release()
            self.cap_vel = None

    def save_combined_observations(self, destination):
        """Export every segmented secondary observation and validated/missing summary."""
        session = getattr(self, 'combined_session', None)
        if session is None:
            return []
        destination = Path(destination)
        stem = destination.with_suffix('')
        observations_file = stem.with_name(stem.name + '.secondary_observations.csv')
        fieldnames = ('frame_index', 'track_id', 'center_x_px', 'center_y_px',
                      'equivalent_diameter_px', 'region')
        with observations_file.open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=fieldnames)
            writer.writeheader()
            for observation in session.observations:
                writer.writerow(asdict(observation))
        summary_file = stem.with_name(stem.name + '.impact_summary.json')
        summary = self.combined_summary
        payload = {
            'schema_version': 1, 'measurement_status': 'EXPLORATORY_NOT_VALIDATED',
            'reference_frame_index': session.reference_frame_index,
            'selected_baseline_frame_index': getattr(self, 'combined_selected_baseline_frame', None),
            'preimpact_velocity_fit_frame_indices': [index for index, _ in session.preimpact_positions],
            'preimpact_velocity_fit_direction': 'substrate_normal',
            'initial_diameter_sample_count': len(session.preimpact_diameters_mm),
            'baseline_original_pixels': [list(session.baseline.p1), list(session.baseline.p2)],
            'configuration': asdict(session.config),
            'impact_summary': asdict(summary) if summary is not None else None,
            'semantics': {
                'cumulative_track_count': 'Number of assigned image track IDs, not confirmed unique physical droplets',
                'spray_envelope_angle_deg': 'Exploratory 2D silhouette descriptor, not a calibrated cone measurement',
                'projected_area_mm2': 'Side-view projected area, not substrate wetted footprint',
                'mean_secondary_diameter_px': 'Per-frame arithmetic mean of segmented secondary observations',
            }
        }
        summary_file.write_text(json.dumps(payload, indent=2, allow_nan=False) + '\n', encoding='utf-8')
        return [observations_file, summary_file]
