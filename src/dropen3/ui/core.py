from __future__ import annotations
import tkinter as tk
import customtkinter as ctk
from tkinter import ttk
from PIL import Image
from importlib.resources import files
from dropen3.ui.widgets import Tooltip


class ApplicationCore:

    def __init__(self):
        super().__init__()
        self.title('Dropen3 - Wettability Analysis')
        self.geometry('1280x900')
        self.cap = None
        self.video_playing = False
        self.analysis_active = False
        self.current_frame_idx = 0
        self.total_frames = 0
        self.after_id = None
        self.show_edges = False
        self.zoom_factor = 1.0
        self.viewer_viewport = None
        self._viewer_resize_pending = None
        self.img_result_original = None
        self.roi_zoom = None
        self.dragging = False
        self.start_x = 0
        self.start_y = 0
        self.zoom_window_size = 150
        self.magnification = 5.0
        self.zoom_label = None
        self.last_method_selected = None
        self.zoom_hover_enabled = False
        self.cap_vel = None
        self.vel_active = False
        self.setup_ui()
        self.install_navigation_shortcuts()
        self.threshold_hysteresis = 200
        self.threshold_impact = 30
        self.tangent_static = 40
        self.tangent_static_pol = 15
        self.tangent_static_baseline_points = 20
        self.n_points_tangent_val = 15
        self.min_points_fit = 4
        self.thick_static_contour = 2
        self.thick_static_baseline = 2
        self.thick_static_tangent = 1
        self.thick_his_contour = 1
        self.thick_his_baseline = 2
        self.thick_his_tangent = 1
        self.thick_impact_contour = 2
        self.thick_impact_baseline = 2
        self.thick_impact_height = 2
        self.settings_container = None
        self.view_container.grid_propagate(False)
        self.view_container.pack_propagate(False)

    def setup_ui(self):
        self.main_layout = ctk.CTkFrame(self, corner_radius=0, fg_color='transparent')
        self.main_layout.pack(fill='both', expand=True)
        self.sidebar = ctk.CTkFrame(self.main_layout, width=220, corner_radius=0)
        self.sidebar.pack(side='left', fill='y')
        try:
            with files('dropen3.assets').joinpath('logo.png').open('rb') as resource:
                img_logo_pil = Image.open(resource).convert('RGBA')
            self.logo_image = ctk.CTkImage(light_image=img_logo_pil, dark_image=img_logo_pil, size=(100, 100))
            self.logo_label = ctk.CTkLabel(self.sidebar, image=self.logo_image, text='')
            self.logo_label.pack(pady=(0, 0))
        except Exception as e:
            print(f'Error loading logo: {e}')
        ctk.CTkLabel(self.sidebar, text='Dropen3', font=('Roboto', 20, 'bold')).pack(pady=(10, 30))
        self.menu_container = ctk.CTkFrame(self.sidebar, fg_color='transparent')
        self.menu_container.pack(fill='x', padx=10)
        self.create_main_menu()
        self.view_container = ctk.CTkFrame(self.main_layout, corner_radius=15)
        self.view_container.pack(side='right', fill='both', expand=True, padx=20, pady=10)
        self.top_toolbar = ctk.CTkFrame(self.view_container, height=40, fg_color='#222', corner_radius=10)
        self.top_toolbar.pack(fill='x', padx=15, pady=(15, 0))
        btn_home = ctk.CTkButton(self.top_toolbar, text='Home', width=80, fg_color='#1f538d', command=self.show_home_view)
        btn_home.pack(side='left', padx=5, pady=5)
        Tooltip(btn_home, 'Return to the main dashboard and reset the current view.')
        btn_import = ctk.CTkButton(self.top_toolbar, text='Import', width=100, command=self.load_media)
        btn_import.pack(side='left', padx=5, pady=5)
        Tooltip(btn_import, 'Load image or video files from your computer for analysis.')
        btn_Edge = ctk.CTkButton(self.top_toolbar, text='Edge detection', width=100, command=self.edge_detection)
        btn_Edge.pack(side='left', padx=10, pady=5)
        Tooltip(btn_Edge, "Toggle the silhouette detection to highlight the droplet's boundaries.")
        separator = ctk.CTkLabel(self.top_toolbar, text=' | ', text_color='#555555')
        separator.pack(side='left', padx=5, pady=5)
        btn_analyze = ctk.CTkButton(self.top_toolbar, text='Analyze', width=100, command=self.show_analyze_options)
        btn_analyze.pack(side='left', padx=10, pady=5)
        Tooltip(btn_analyze, 'Open the menu to generate evolution graphs and statistical distributions.')
        btn_datatable = ctk.CTkButton(self.top_toolbar, text='Data Table', width=100, command=self.show_data_table)
        btn_datatable.pack(side='left', padx=10, pady=5)
        Tooltip(btn_datatable, 'View and manage the numerical results of your measurements in a spreadsheet format.')
        btn_save = ctk.CTkButton(self.top_toolbar, text='Save Data', width=100, command=self.save_data_table)
        btn_save.pack(side='left', padx=5, pady=5)
        btn_save_img = ctk.CTkButton(self.top_toolbar, text='Save Image', width=100, command=self.save_current_image)
        btn_save_img.pack(side='left', padx=5, pady=5)
        Tooltip(btn_save, 'Export the current measurement table to an external file.')
        btn_reset = ctk.CTkButton(self.top_toolbar, text='Reset', width=100, fg_color='#6c757d', command=self.reset_analysis)
        btn_reset.pack(side='left', padx=5, pady=5)
        Tooltip(btn_reset, 'Clear all current progress and return the application to its initial state.')
        self.center_stack = ctk.CTkFrame(self.view_container, fg_color='transparent')
        self.center_stack.pack(fill='both', expand=True, padx=15, pady=15)
        # Viewer previews must not resize the main layout as zoom changes.
        self.center_stack.pack_propagate(False)
        self.canvas_view = ctk.CTkLabel(self.center_stack, text='Awaiting media...', fg_color='#0a0a0a', corner_radius=10)
        self.canvas_view.pack(fill='both', expand=True)
        self.table_container = ctk.CTkFrame(self.center_stack, fg_color='#1a1a1a')
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Treeview', background='#2b2b2b', foreground='white', fieldbackground='#2b2b2b', borderwidth=0)
        style.map('Treeview', background=[('selected', '#1f538d')])
        self.tree = ttk.Treeview(self.table_container, columns=(), show='headings')
        self.tree.pack(side='left', fill='both', expand=True)
        self.scrollbar = ttk.Scrollbar(self.table_container, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side='right', fill='y')
        self.canvas_view.bind('<MouseWheel>', self.on_mouse_wheel)
        self.canvas_view.bind('<Button-1>', self.on_click_press)
        self.canvas_view.bind('<B1-Motion>', self.on_mouse_drag)
        self.canvas_view.bind('<ButtonRelease-1>', self.on_click_release)
        self.canvas_view.bind('<Button-4>', self.on_mouse_wheel)
        self.canvas_view.bind('<Button-5>', self.on_mouse_wheel)
        self.canvas_view.bind('<Configure>', self.on_viewer_resize)
        self.canvas_view.bind('<Motion>', self.on_mouse_move)
        self.canvas_view.bind('<Leave>', self.hide_zoom_window)
        self.controls_panel = ctk.CTkFrame(self.view_container, height=120, fg_color='#1a1a1a', corner_radius=10)
        self.controls_panel.pack(fill='x', side='bottom', padx=15, pady=(0, 15))
        self.btns_wrapper = ctk.CTkFrame(self.controls_panel, fg_color='transparent')
        self.btns_wrapper.pack(expand=True)
        self.btn_prev = ctk.CTkButton(self.btns_wrapper, text='⏪', width=40, height=20, command=self.prev_frame)
        self.btn_prev.grid(row=0, column=0, padx=5, pady=10)
        self.btn_play = ctk.CTkButton(self.btns_wrapper, text='START', width=90, height=20, command=self.toggle_video)
        self.btn_play.grid(row=0, column=1, padx=5, pady=10)
        self.btn_next = ctk.CTkButton(self.btns_wrapper, text='⏩', width=40, height=20, command=self.next_frame)
        self.btn_next.grid(row=0, column=2, padx=5, pady=10)
        ctk.CTkLabel(self.btns_wrapper, text=' | ').grid(row=0, column=3, padx=10)
        self.btn_start_an = ctk.CTkButton(self.btns_wrapper, text='START ANALYSIS', width=40, height=20, fg_color='#28a745', hover_color='#218838', command=self.start_analysis)
        self.btn_start_an.grid(row=0, column=4, padx=5, pady=10)
        self.btn_pause_an = ctk.CTkButton(self.btns_wrapper, text='PAUSE ANALYSIS', width=40, height=20, fg_color='#dc3545', hover_color='#c82333', command=self.pause_analysis)
        self.btn_pause_an.grid(row=0, column=5, padx=5, pady=10)
        self.btn_reset_an = ctk.CTkButton(self.btns_wrapper, text='RESET', width=40, height=20, fg_color='#6c757d', hover_color='#5a6268', command=self.reset_all)
        self.btn_reset_an.grid(row=0, column=6, padx=5, pady=10)
        self.btn_restart_an = ctk.CTkButton(self.btns_wrapper, text='RESTART', width=40, height=20, fg_color='#6c757d', hover_color='#5a6268', command=self.restart_video)
        self.btn_restart_an.grid(row=0, column=7, padx=5, pady=10)
        self.btn_zoom_in = ctk.CTkButton(self.btns_wrapper, text='🔍+', width=40, height=20, command=lambda: self.apply_zoom(1.2))
        self.btn_zoom_in.grid(row=0, column=8, padx=2)
        self.btn_zoom_out = ctk.CTkButton(self.btns_wrapper, text='🔍-', width=40, height=20, command=lambda: self.apply_zoom(1 / 1.2))
        self.btn_zoom_out.grid(row=0, column=9, padx=2)
        self.btn_toggle_zoom = ctk.CTkButton(self.btns_wrapper, text='🔍 Hover: OFF', width=100, height=20, fg_color='#444444', command=self.toggle_zoom_hover)
        self.btn_toggle_zoom.grid(row=0, column=10, padx=5)
        self.video_slider_var = tk.DoubleVar(value=0)
        self.video_slider = ctk.CTkSlider(self.btns_wrapper, from_=0, to=100, variable=self.video_slider_var, command=self.on_slider_move)
        self.video_slider.grid(row=1, column=0, columnspan=11, sticky='ew', pady=(5, 5), padx=2)
        self.lbl_frame_counter = ctk.CTkLabel(self.btns_wrapper, text='Frame: 0 / 0', font=('Roboto', 11), text_color='#aaaaaa')
        self.lbl_frame_counter.grid(row=2, column=0, columnspan=11, pady=(2, 2))
        self.lbl_status = ctk.CTkLabel(self.view_container, text='Waiting for file to load...')
        self.lbl_status.pack(side='bottom')

    def install_navigation_shortcuts(self):
        """Navigate one video frame at a time without disrupting text editors."""
        for key in ('<Left>', '<Right>', '<KeyPress-a>', '<KeyPress-d>',
                    '<KeyPress-A>', '<KeyPress-D>'):
            self.bind_all(key, self.on_frame_key)

    def on_frame_key(self, event):
        """Handle frame navigation only in the application's main window."""
        if event.widget.winfo_toplevel() is not self:
            return None
        if isinstance(event.widget, (tk.Entry, tk.Text, tk.Spinbox,
                                     ttk.Entry, ttk.Combobox)):
            return None
        if event.widget.winfo_class() in ('CTkEntry', 'CTkTextbox'):
            return None
        if self.cap is None or not self.cap.isOpened():
            return None
        key = event.keysym.lower()
        if key not in ('left', 'a', 'right', 'd'):
            return None
        self.stop_video()
        if key in ('left', 'a'):
            self.prev_frame()
        else:
            self.next_frame()
        return 'break'
