from __future__ import annotations
import tkinter as tk
import customtkinter as ctk


class SettingsMixin:

    def show_hysteresis_settings(self):
        if self.settings_container:
            self.settings_container.destroy()
        self.settings_container = ctk.CTkFrame(self.sidebar, fg_color='transparent')
        self.settings_container.pack(fill='x', padx=10, pady=10)
        ctk.CTkLabel(self.settings_container, text='Parameter adjustment', font=('Roboto', 12, 'bold'), text_color='#1f538d').pack(pady=(0, 10))
        ctk.CTkLabel(self.settings_container, text='Threshold:').pack(anchor='w')
        self.lbl_thresh_val = ctk.CTkLabel(self.settings_container, text=f'{self.threshold_hysteresis}')
        self.lbl_thresh_val.pack(anchor='e')
        self.slider_thresh = ctk.CTkSlider(self.settings_container, from_=0, to=255, command=self.update_thresh_value)
        self.slider_thresh.set(self.threshold_hysteresis)
        self.slider_thresh.pack(fill='x', pady=5)
        ctk.CTkLabel(self.settings_container, text='Tangent Points:').pack(anchor='w', pady=(10, 0))
        self.lbl_tangent_val = ctk.CTkLabel(self.settings_container, text=f'{self.n_points_tangent_val}')
        self.lbl_tangent_val.pack(anchor='e')
        self.slider_tangent = ctk.CTkSlider(self.settings_container, from_=5, to=100, command=self.update_tangent_value)
        self.slider_tangent.set(self.n_points_tangent_val)
        self.slider_tangent.pack(fill='x', pady=5)
        ctk.CTkLabel(self.settings_container, text='Minimum Fit Points:').pack(anchor='w', pady=(10, 0))
        self.lbl_min_points_val = ctk.CTkLabel(self.settings_container, text=f'{self.min_points_fit}')
        self.lbl_min_points_val.pack(anchor='e')
        self.slider_min_points = ctk.CTkSlider(self.settings_container, from_=4, to=100, command=self.update_min_points_fit)
        self.slider_min_points.set(self.min_points_fit)
        self.slider_min_points.pack(fill='x', pady=5)

    def show_impact_settings(self):
        if self.settings_container:
            self.settings_container.destroy()
        self.settings_container = ctk.CTkFrame(self.sidebar, fg_color='transparent')
        self.settings_container.pack(fill='x', padx=10, pady=10)
        ctk.CTkLabel(self.settings_container, text='Parameter adjustment', font=('Roboto', 12, 'bold'), text_color='#1f538d').pack(pady=(0, 10))
        ctk.CTkLabel(self.settings_container, text='Threshold:').pack(anchor='w')
        self.lbl_thresh_val = ctk.CTkLabel(self.settings_container, text=f'{self.threshold_impact}')
        self.lbl_thresh_val.pack(anchor='e')
        self.slider_thresh = ctk.CTkSlider(self.settings_container, from_=0, to=255, command=self.update_thresh_value_impact)
        self.slider_thresh.set(self.threshold_impact)
        self.slider_thresh.pack(fill='x', pady=5)
        ctk.CTkLabel(self.settings_container, text='Thickness:').pack(anchor='w', pady=(10, 0))
        thick_frame = ctk.CTkFrame(self.settings_container, fg_color='transparent')
        thick_frame.pack(fill='x', pady=5)

        def create_line_selector(parent, label_text, var_name, row):
            ctk.CTkLabel(parent, text=label_text, font=('Roboto', 10)).grid(row=row, column=0, sticky='w', padx=2, pady=2)
            if not hasattr(self, var_name):
                setattr(self, var_name, 2)
            val_var = tk.StringVar(value=str(getattr(self, var_name)))
            entry = ctk.CTkEntry(parent, textvariable=val_var, width=35, height=22, justify='center')
            entry.grid(row=row, column=2, padx=2, pady=2)

            def alterar(delta):
                try:
                    val = int(val_var.get()) + delta
                    val = max(1, min(10, val))
                    val_var.set(str(val))
                    setattr(self, var_name, val)
                except ValueError:
                    pass
            btn_menos = ctk.CTkButton(parent, text='-', width=22, height=22, command=lambda: alterar(-1))
            btn_menos.grid(row=row, column=1, padx=1, pady=2)
            btn_mais = ctk.CTkButton(parent, text='+', width=22, height=22, command=lambda: alterar(1))
            btn_mais.grid(row=row, column=3, padx=1, pady=2)
        create_line_selector(thick_frame, 'Contour:', 'thick_impact_contour', 0)
        create_line_selector(thick_frame, 'Baseline:', 'thick_impact_baseline', 1)
        create_line_selector(thick_frame, 'Height:', 'thick_impact_height', 2)

    def show_static_settings(self):
        if self.settings_container:
            self.settings_container.destroy()
        self.settings_container = ctk.CTkFrame(self.sidebar, fg_color='transparent')
        self.settings_container.pack(fill='x', padx=10, pady=10)
        ctk.CTkLabel(self.settings_container, text='Parameter adjustment', font=('Roboto', 12, 'bold'), text_color='#1f538d').pack(pady=(0, 10))
        ctk.CTkLabel(self.settings_container, text='Number of points:').pack(anchor='w')
        self.lbl_thresh_val = ctk.CTkLabel(self.settings_container, text=f'{self.tangent_static}')
        self.lbl_thresh_val.pack(anchor='e')
        self.slider_thresh = ctk.CTkSlider(self.settings_container, from_=0, to=50, command=self.update_thresh_value_static)
        self.slider_thresh.set(self.tangent_static)
        self.slider_thresh.pack(fill='x', pady=5)
        ctk.CTkLabel(self.settings_container, text='Thickness:').pack(anchor='w', pady=(10, 0))
        thick_frame = ctk.CTkFrame(self.settings_container, fg_color='transparent')
        thick_frame.pack(fill='x', pady=5)

        def create_line_selector(parent, label_text, var_name, row):
            ctk.CTkLabel(parent, text=label_text, font=('Roboto', 10)).grid(row=row, column=0, sticky='w', padx=2, pady=2)
            val_var = tk.StringVar(value=str(getattr(self, var_name)))
            entry = ctk.CTkEntry(parent, textvariable=val_var, width=35, height=22, justify='center')
            entry.grid(row=row, column=2, padx=2, pady=2)

            def alterar(delta):
                try:
                    val = int(val_var.get()) + delta
                    val = max(1, min(10, val))
                    val_var.set(str(val))
                    setattr(self, var_name, val)
                except ValueError:
                    pass
            btn_menos = ctk.CTkButton(parent, text='-', width=22, height=22, command=lambda: alterar(-1))
            btn_menos.grid(row=row, column=1, padx=1, pady=2)
            btn_mais = ctk.CTkButton(parent, text='+', width=22, height=22, command=lambda: alterar(1))
            btn_mais.grid(row=row, column=3, padx=1, pady=2)
        create_line_selector(thick_frame, 'Contour:', 'thick_static_contour', 0)
        create_line_selector(thick_frame, 'Baseline:', 'thick_static_baseline', 1)
        create_line_selector(thick_frame, 'Tangent:', 'thick_static_tangent', 2)

    def show_polynomial_settings(self):
        if self.settings_container:
            self.settings_container.destroy()
        self.settings_container = ctk.CTkFrame(self.sidebar, fg_color='transparent')
        self.settings_container.pack(fill='x', padx=10, pady=10)
        ctk.CTkLabel(self.settings_container, text='Parameter adjustment', font=('Roboto', 12, 'bold'), text_color='#1f538d').pack(pady=(0, 10))
        ctk.CTkLabel(self.settings_container, text='Number of points:').pack(anchor='w')
        self.lbl_thresh_val = ctk.CTkLabel(self.settings_container, text=f'{self.tangent_static_pol}')
        self.lbl_thresh_val.pack(anchor='e')
        self.slider_thresh = ctk.CTkSlider(self.settings_container, from_=0, to=50, command=self.update_thresh_value_static_pol)
        self.slider_thresh.set(self.tangent_static_pol)
        self.slider_thresh.pack(fill='x', pady=5)
        ctk.CTkLabel(self.settings_container, text='Number of points base:').pack(anchor='w')
        self.lbl_thresh_val = ctk.CTkLabel(self.settings_container, text=f'{self.tangent_static_baseline_points}')
        self.lbl_thresh_val.pack(anchor='e')
        self.slider_thresh = ctk.CTkSlider(self.settings_container, from_=0, to=50, command=self.update_thresh_value_static_baseline_points)
        self.slider_thresh.set(self.tangent_static_baseline_points)
        self.slider_thresh.pack(fill='x', pady=5)

    def update_thresh_value(self, val):
        self.threshold_hysteresis = int(val)
        self.lbl_thresh_val.configure(text=f'{self.threshold_hysteresis}')

    def update_tangent_value(self, val):
        self.n_points_tangent_val = int(val)
        self.lbl_tangent_val.configure(text=f'{self.n_points_tangent_val}')

    def update_min_points_fit(self, val):
        self.min_points_fit = int(val)
        self.lbl_min_points.configure(text=f'{self.min_points_fit}')

    def update_thresh_value_impact(self, val):
        self.threshold_impact = int(val)
        self.lbl_thresh_val.configure(text=f'{self.threshold_impact}')

    def update_thresh_value_static(self, val):
        self.tangent_static = int(val)
        self.lbl_thresh_val.configure(text=f'{self.tangent_static}')

    def update_thresh_value_static_pol(self, val):
        self.tangent_static_pol = int(val)
        self.lbl_thresh_val.configure(text=f'{self.tangent_static_pol}')

    def update_thresh_value_static_baseline_points(self, val):
        self.tangent_static_baseline_points = int(val)
        self.lbl_thresh_val.configure(text=f'{self.tangent_static_baseline_points}')
