from __future__ import annotations
import cv2
import customtkinter as ctk
from tkinter import messagebox
from dropen3.ui.widgets import Tooltip


class HomeMixin:

    def show_important_info(self):
        info_win = ctk.CTkToplevel(self)
        info_win.title('Important Information & Guidelines')
        info_win.geometry('600x650')
        info_win.attributes('-topmost', True)
        info_win.update_idletasks()
        info_win.wait_visibility()
        info_win.grab_set()
        ctk.CTkLabel(info_win, text='Dropen3 - Software Guidelines & Best Practices', font=('Roboto', 18, 'bold'), text_color='#1f538d').pack(pady=(15, 10))
        scroll_frame = ctk.CTkScrollableFrame(info_win, width=540, height=500, corner_radius=10)
        scroll_frame.pack(padx=20, pady=10, fill='both', expand=True)
        sections = [('1. About the Software', 'Dropen3 is an advanced computational framework designed for high-throughput automated Contact Angle (CA), wettability hysteresis, and dynamic droplet impact analysis. It utilizes robust image processing, Canny edge detection, polynomial modeling, and Weighted Least Squares (WLS) algorithms to provide inspectable interfacial measurements requiring experimental validation.'), ('2. General Best Practices', '- Ensure the baseline is precisely horizontal or accurately calibrated before starting analysis.\n- For high-speed drop impact videos, ensure the recording starts cleanly before droplet contact.\n- Always double-check and tune the threshold parameters and tangent point counts if minor contour deviations appear.\n- Make use of the ROI (Region of Interest) tools to filter out background disturbances, reflections, or needles.'), ('3. Video & Image Quality Requirements', '- Lighting & Contrast: High background-to-droplet contrast is essential. Backlighting is highly recommended to produce sharp droplet silhouettes.\n- Resolution & Scaling: Clear spatial scale calibration (mm/pixel) must be supplied for precise metric conversions.\n- Frame Rate (FPS): For rapid dynamic phenomena (e.g., impact spreading and retraction), high-speed camera recordings ranging from 1,000 to 10,000 FPS are strongly recommended to capture transient wetting phases accurately.'), ('4. Analysis Modules Overview', '- Static Angle: Evaluates equilibrium contact angles utilizing tangent or polynomial fitting.\n- Hysteresis: Tracks advancing and receding contact angles over time or volume shifts.\n- Drop Impact: Calculates impact velocities, droplet height, dynamic diameter evolution, and dimensionless numbers (Reynolds, Weber, Ohnesorge).')]
        for section_title, section_body in sections:
            ctk.CTkLabel(scroll_frame, text=section_title, font=('Roboto', 14, 'bold'), text_color='#28a745').pack(anchor='w', pady=(10, 2))
            lbl_desc = ctk.CTkLabel(scroll_frame, text=section_body, font=('Roboto', 12), justify='left', wraplength=500)
            lbl_desc.pack(anchor='w', pady=(0, 5))
        ctk.CTkButton(info_win, text='Close Window', fg_color='#dc3545', hover_color='#c82333', command=info_win.destroy).pack(pady=15)

    def show_home_view(self):
        self.show_edges = False
        self.table_container.pack_forget()
        self.canvas_view.pack(fill='both', expand=True)
        if self.img_result_original is not None:
            self.display_frame(self.img_result_original, update_original=False)
        self.lbl_status.configure(text='Active display screen')

    def create_main_menu(self):
        # Leaving a running combined workflow must cancel its pending callbacks.
        if getattr(self, 'combined_session', None) is not None:
            self.stop_combined_analysis()
            self.combined_session = None
            self.combined_summary = None
        if hasattr(self, 'settings_container') and self.settings_container:
            self.settings_container.destroy()
            self.settings_container = None
        for child in self.menu_container.winfo_children():
            child.destroy()
        btn_static = ctk.CTkButton(self.menu_container, text='Static Angle', command=lambda: self.show_sub_menu('WCA'))
        btn_static.pack(pady=10, fill='x')
        Tooltip(btn_static, 'Measure the contact angle of a stationary droplet using different fitting methods.')
        btn_hysteresis = ctk.CTkButton(self.menu_container, text='Hysteresis', command=lambda: self.show_sub_menu('HIS'))
        btn_hysteresis.pack(pady=10, fill='x')
        Tooltip(btn_hysteresis, 'Analyze advancing and receding angles to determine surface wettability properties.')
        btn_dropimpact = ctk.CTkButton(self.menu_container, text='Drop Impact', command=lambda: self.show_sub_menu('DROP'))
        btn_dropimpact.pack(pady=10, fill='x')
        Tooltip(btn_dropimpact, 'Calculate the velocity and spreading factor of a droplet during impact.')
        btn_combined = ctk.CTkButton(self.menu_container, text='Combined Spray and Impact', command=lambda: self.show_sub_menu('SPRAY_IMPACT'))
        btn_combined.pack(pady=10, fill='x')
        Tooltip(btn_combined, 'Exploratory combined analysis: spray tracking and main-droplet geometry.')
        btn_info = ctk.CTkButton(self.menu_container, text='INFORMATION & GUIDELINES', fg_color='#A93226', hover_color='#7B241C', command=self.show_important_info)
        btn_info.pack(padx=20, pady=20)
        Tooltip(btn_info, 'Important information about analyses and files.')

    def show_sub_menu(self, mode):
        if mode != 'SPRAY_IMPACT' and getattr(self, 'combined_session', None) is not None:
            self.stop_combined_analysis()
            self.combined_session = None
            self.combined_summary = None
        self.current_mode = mode
        for child in self.menu_container.winfo_children():
            child.destroy()
        titles = {'WCA': ['Tangent method', 'Polynomial Fit', 'Three points'], 'HIS': ['Adv-Rec', 'Polynomial', 'Weighted Least Squares', 'WLS (Pre-deposited Drop)'], 'DROP': ['Envelope-Diameter Method', 'Interfacial Baseline Method', 'Spray & Secondary Droplets'], 'SPRAY_IMPACT': ['Combined Spray and Impact']}
        ctk.CTkButton(self.menu_container, text='← Return', fg_color='#444', command=self.create_main_menu).pack(pady=(0, 10), fill='x')
        for method in titles[mode]:
            if method == 'Tangent method':
                btn_standard = ctk.CTkButton(self.menu_container, text=method, command=lambda: [self.show_static_settings(), self.run_standard_static_analysis()])
                btn_standard.pack(pady=5, fill='x')
                Tooltip(btn_standard, 'To measure the equilibrium contact angle of a stationary droplet on a horizontal surface.')
            elif method == 'Polynomial Fit':
                btn_fitting = ctk.CTkButton(self.menu_container, text=method, command=lambda: [self.show_polynomial_settings(), self.run_advanced_static_analysis()])
                btn_fitting.pack(pady=5, fill='x')
                Tooltip(btn_fitting, "This method uses a second-degree equation to automatically model the droplet's curvature and calculate the tangent at the contact point")
            elif method == 'Three points':
                btn_points = ctk.CTkButton(self.menu_container, text=method, command=lambda: [self.show_polynomial_settings(), self.run_manual_analysis()])
                btn_points.pack(pady=5, fill='x')
                Tooltip(btn_points, 'This manual approach defines the contact angle by connecting three user-selected points to form the base and the slope of the droplet.')
            elif method == 'Adv-Rec':
                btn_adv_rec = ctk.CTkButton(self.menu_container, text=method, command=lambda: [self.show_hysteresis_settings(), self.run_advancing_hysteresis()])
                btn_adv_rec.pack(pady=5, fill='x')
                Tooltip(btn_adv_rec, 'To measure the Advancing Angle ($\\theta_A$) and the Receding Angle ($\\theta_R$)')
            elif method == 'Polynomial':
                btn_polynomial = ctk.CTkButton(self.menu_container, text=method, command=lambda: [self.show_hysteresis_settings(), self.run_polynomial_hysteresis()])
                btn_polynomial.pack(pady=5, fill='x')
                Tooltip(btn_polynomial, 'To measure the Advancing Angle ($\\theta_A$) and the Receding Angle ($\\theta_R$)')
            elif method == 'Weighted Least Squares':
                btn_run_wls = ctk.CTkButton(self.menu_container, text=method, command=lambda: [self.show_hysteresis_settings(), self.run_weighted_hysteresis()])
                btn_run_wls.pack(pady=5, fill='x')
                Tooltip(btn_run_wls, 'Calculate the contact angle using polynomials with Weighted Least Squares (WLS).')
            elif method == 'WLS (Pre-deposited Drop)':
                btn_run_wls_novo = ctk.CTkButton(self.menu_container, text=method, command=lambda: [self.show_hysteresis_settings(), self.run_first_frame_weighted_hysteresis()])
                btn_run_wls_novo.pack(pady=5, fill='x')
                Tooltip(btn_run_wls_novo, 'Calculate the contact angle using Weighted Least Squares (WLS) for droplets already deposited on the surface from the first frame, bypassing background subtraction')
            elif method == 'Envelope-Diameter Method':
                btn_Third = ctk.CTkButton(self.menu_container, text=method, command=lambda: [self.show_impact_settings(), self.run_impact_method_three()])
                btn_Third.pack(pady=5, fill='x')
                Tooltip(btn_Third, 'This method analyzes droplet impact by tracking the maximum envelope diameter (maximum width) of the droplet during spreading and retraction using image segmentation and contour fitting.')
            elif method == 'Interfacial Baseline Method':
                btn_four = ctk.CTkButton(self.menu_container, text=method, command=lambda: [self.show_impact_settings(), self.run_drop_impact_analysis()])
                btn_four.pack(pady=5, fill='x')
                Tooltip(btn_four, 'This method analyzes droplet impact by measuring the droplet diameter at the baseline during spreading using image segmentation.')
            elif method == 'Combined Spray and Impact':
                button = ctk.CTkButton(self.menu_container, text=method, command=self.run_combined_spray_impact_analysis)
                button.pack(pady=5, fill='x')
                Tooltip(button, 'Select reference frame and substrate baseline, then analyze the same video.')
            elif method == 'Spray & Secondary Droplets':
                btn_spray = ctk.CTkButton(self.menu_container, text=method, command=lambda: [self.show_impact_settings(), self.run_spray_droplet_analysis()])
                btn_spray.pack(pady=5, fill='x')
                Tooltip(btn_spray, 'Captures spray cone angle, secondary droplet size distribution, and droplet count following high-speed impact using background subtraction.')
            else:
                ctk.CTkButton(self.menu_container, text=method, command=self.load_media).pack(pady=5, fill='x')

    def reset_analysis(self):
        if getattr(self, 'combined_session', None) is not None:
            self.stop_combined_analysis()
            self.combined_session = None
            self.combined_summary = None
        if hasattr(self, 'after_id') and self.after_id:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        for item in self.tree.get_children():
            self.tree.delete(item)
        if hasattr(self, 'vel_data'):
            self.vel_data = {'times': [], 'positions': [], 'diameters': [], 'pre_impact': []}
        if hasattr(self, 'vel_state'):
            self.vel_state = {'frame_id': 0, 'impact_detected': False, 'background': None, 'preimpact_diameter': float('nan')}
        self.current_frame_idx = 0
        self.analysis_active = False
        self.vel_active = False
        self.img_result_original = None
        if hasattr(self, 'lbl_frame_counter'):
            self.lbl_frame_counter.configure(text='Frame: 0 / 0')
        self.canvas_view.configure(image='', text='Awaiting media...')
        self.canvas_view.image = None
        self.lbl_status.configure(text='System reset. Ready for new measurements.')
        messagebox.showinfo('Reset', 'All data and images were successfully cleaned.')

    def reset_all(self):
        if getattr(self, 'combined_session', None) is not None:
            self.stop_combined_analysis()
            self.combined_session = None
            self.combined_summary = None
        self.video_playing = False
        self.analysis_active = False
        self.vel_active = False
        if self.after_id:
            self.after_cancel(self.after_id)
            self.after_id = None
        if self.cap:
            self.cap.release()
            self.cap = None
        if hasattr(self, 'cap_vel') and self.cap_vel:
            self.cap_vel.release()
            self.cap_vel = None
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.current_frame_idx = 0
        self.total_frames = 0
        self.vel_data = {'times': [], 'positions': [], 'diameters': [], 'pre_impact': []}
        self.vel_state = {'frame_id': 0, 'impact_detected': False, 'background': None, 'preimpact_diameter': float('nan')}
        self.img_result_original = None
        self.canvas_view.configure(image='', text='Awaiting media...')
        self.canvas_view.image = None
        if hasattr(self, 'lbl_frame_counter'):
            self.lbl_frame_counter.configure(text='Frame: 0 / 0')
        if hasattr(self, 'video_slider_var'):
            self.video_slider_var.set(0)
        self.lbl_status.configure(text='System reset. Ready for new measurements.')
        messagebox.showinfo('Reset', 'All data and images were successfully cleaned.')
        print('All data and video handles have been reset.')

    def restart_video(self):
        if getattr(self, 'current_mode', None) == 'SPRAY_IMPACT':
            self.restart_combined_analysis()
            return
        mode_current = getattr(self, 'current_mode', None)
        method_current = getattr(self, 'last_method_selected', None)
        has_data = len(self.tree.get_children()) > 0
        mode_valid = mode_current in ['HIS', 'DROP']
        path_video = getattr(self, 'video_path', None)
        if has_data or mode_valid:
            self.analysis_active = True
            self.vel_active = True
            self.video_playing = False
            for item in self.tree.get_children():
                self.tree.delete(item)
            if hasattr(self, 'data') and isinstance(self.data, dict):
                self.data = {'history_pos': [], 'preimpact_diameter': 1.0, 'times': [], 'positions': [], 'falling_areas': [], 'last_diam_val': None, 'max_w_px': 0}
            self.p_left_initial = None
            self.p_right_initial = None
            self.frame_id = 0
            self.impact_detected = False
            if hasattr(self, 'lbl_status'):
                self.lbl_status.configure(text='Analysis automatically restarted from the beginning...')
        else:
            self.video_playing = False
            self.analysis_active = False
            self.vel_active = False
            if hasattr(self, 'lbl_status'):
                self.lbl_status.configure(text='Video restarted from the beginning.')
            if hasattr(self, 'btn_play'):
                self.btn_play.configure(text='START')
        self.current_frame_idx = 0
        if hasattr(self, 'video_slider_var'):
            self.video_slider_var.set(0)
        if self.cap:
            if not self.cap.isOpened() and path_video:
                self.cap = cv2.VideoCapture(path_video)
            else:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        if hasattr(self, 'cap_vel'):
            if (self.cap_vel is None or not self.cap_vel.isOpened()) and path_video:
                self.cap_vel = cv2.VideoCapture(path_video)
            elif self.cap_vel is not None:
                self.cap_vel.set(cv2.CAP_PROP_POS_FRAMES, 0)
        if hasattr(self, 'cap_hysteresis'):
            if (self.cap_hysteresis is None or not self.cap_hysteresis.isOpened()) and path_video:
                self.cap_hysteresis = cv2.VideoCapture(path_video)
            elif self.cap_hysteresis is not None:
                self.cap_hysteresis.set(cv2.CAP_PROP_POS_FRAMES, 0)
        if has_data or mode_valid:
            if mode_current == 'HIS':
                if method_current == 'WCA_WLS_DYNAMIC':
                    self.process_next_weighted_frame()
                elif method_current == 'WCA_WLS_FIRST_FRAME':
                    self.process_next_first_frame_weighted()
                elif method_current == 'HIS_POLYNOMIAL':
                    if self.cap and (not self.cap.isOpened()) and path_video:
                        self.cap = cv2.VideoCapture(path_video)
                    self.process_polynomial_hysteresis_frame()
                else:
                    self.process_next_hysteresis_frame()
            elif mode_current == 'DROP':
                if method_current == 'DROP_FOURTH':
                    self.process_impact_frame_four()
                elif method_current == 'DROP_THIRD':
                    self.process_impact_frame_three()
                elif method_current == 'DROP_SPRAY':
                    self.process_spray_frame()
                elif hasattr(self, 'process_next_drop_frame'):
                    self.process_next_drop_frame()
        else:
            self.show_frame()

    def start_analysis(self):
        if getattr(self, 'current_mode', None) == 'SPRAY_IMPACT':
            self.resume_combined_analysis()
            return
        has_media = getattr(self, 'img_result_original', None) is not None or getattr(self, 'cap', None) is not None or hasattr(self, 'video_path')
        if not has_media:
            messagebox.showwarning('Warning', 'No media has been loaded! Please import an image/video and select an analysis method from the left menu first.')
            return
        has_method = hasattr(self, 'current_mode') and self.current_mode and getattr(self, 'last_method_selected', None)
        if not has_method:
            messagebox.showwarning('Warning', 'No analysis method selected! Please choose one of the methods from the left sidebar menu before starting.')
            return
        if not getattr(self, 'analysis_active', False):
            self.analysis_active = True
            self.vel_active = True
            self.lbl_status.configure(text='Analysis resumed...')
            mode = getattr(self, 'current_mode', '')
            method = getattr(self, 'last_method_selected', '')
            if mode == 'HIS':
                if method == 'WCA_WLS_DYNAMIC':
                    self.process_next_weighted_frame()
                elif method == 'WCA_WLS_FIRST_FRAME':
                    self.process_next_first_frame_weighted()
                elif method == 'HIS_POLYNOMIAL':
                    self.process_polynomial_hysteresis_frame()
                else:
                    self.process_next_hysteresis_frame()
            elif mode == 'DROP':
                if method == 'DROP_FOURTH':
                    self.process_impact_frame_four()
                elif method == 'DROP_THIRD':
                    self.process_impact_frame_three()
                elif method == 'DROP_SPRAY':
                    self.process_spray_frame()
                elif hasattr(self, 'process_next_drop_frame'):
                    self.process_next_drop_frame()
            elif mode == 'WCA':
                if method == 'WCA_NORMAL':
                    self.run_standard_static_analysis()
                elif method == 'WCA_ADVANCED':
                    self.run_advanced_static_analysis()
                elif method == 'WCA_THREE_POINTS':
                    self.run_manual_analysis()

    def pause_analysis(self):
        if getattr(self, 'current_mode', None) == 'SPRAY_IMPACT':
            self.pause_combined_analysis()
            return
        self.analysis_active = False
        self.vel_active = False
        self.lbl_status.configure(text='Analysis PAUSED.')
