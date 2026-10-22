from __future__ import annotations
import cv2
import customtkinter as ctk
import pandas as pd
from tkinter import filedialog
from tkinter import messagebox
from dropen3.system.provenance import write_export_provenance


class ExportMixin:

    def save_current_image(self):
        if self.img_result_original is None:
            messagebox.showwarning('Warning', 'There is no image to save!')
            return
        img_to_save = getattr(self, 'current_vis_img', self.img_result_original)
        file_path = filedialog.asksaveasfilename(defaultextension='.png', filetypes=[('PNG files', '*.png'), ('JPEG files', '*.jpg'), ('All files', '*.*')], title='Save Measurement Image')
        if file_path:
            try:
                cv2.imwrite(file_path, img_to_save)
                messagebox.showinfo('Success', f'Image saved in:\n{file_path}')
            except Exception as e:
                messagebox.showerror('Error', f'Failed to save image: {e}')

    def show_data_table(self):
        self.canvas_view.pack_forget()
        self.table_container.pack(fill='both', expand=True)
        headers = {'WCA': ['Frame', 'Left Angle (°)', 'Right Angle (°)', 'Mean (°)'], 'HIS': ['Frame', 'Time (s)', 'Diameter (px)', 'Base Diameter (px)', 'Left Advance (px)', 'Right Advance (px)', 'Left Angle (°)', 'Right Angle (°)', 'Hysteresis (°)', 'Projected Base Area (px²)'], 'DROP': ['Time (s)', 'Position (mm)', 'Diameter (mm)', 'Beta', 'Height (mm)', 'Projected Area (mm²)', 'dD/dt (mm/s)'], 'DROP_SPRAY': ['Frame', 'Time (s)', 'Droplet Count', 'Mean Diameter (px)', 'Cone Angle (°)']}
        mode_tabela = self.current_mode
        if mode_tabela == 'DROP' and getattr(self, 'last_method_selected', None) == 'DROP_SPRAY':
            mode_tabela = 'DROP_SPRAY'
        cols = headers.get(mode_tabela, ['Data'])
        self.tree['columns'] = cols
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150, anchor='center')
        self.lbl_status.configure(text=f'Data Table: Mode {self.current_mode}')

    def save_data_table(self):
        items = self.tree.get_children()
        if not items:
            messagebox.showwarning('Warning', 'The table is empty. There is no data to save.')
            return
        columns = self.tree['columns']
        data = []
        for item in items:
            data.append(self.tree.item(item)['values'])
        df = pd.DataFrame(data, columns=columns)
        file_path = filedialog.asksaveasfilename(filetypes=[('Excel (XLSX)', '*.xlsx'), ('CSV (semicolon-separated UTF-8)', '*.csv'), ('Text (tab-separated)', '*.txt'), ('All files', '*.*')], title='Save Analysis Data')
        if not file_path:
            return
        try:
            path_lower = file_path.lower()
            if path_lower.endswith('.xlsx'):
                df.to_excel(file_path, index=False, engine='openpyxl')
            elif path_lower.endswith('.txt'):
                df.to_csv(file_path, index=False, sep='\t', encoding='utf-8')
            else:
                if not path_lower.endswith('.csv'):
                    file_path += '.csv'
                df.to_csv(file_path, index=False, sep=';', encoding='utf-8-sig')
            try:
                sidecar = write_export_provenance(file_path, self, columns=list(df.columns), rows=len(df))
            except (OSError, TypeError, ValueError) as metadata_error:
                messagebox.showwarning('Metadata warning', f'The data file was saved, but its metadata could not be saved: {metadata_error}')
            else:
                messagebox.showinfo('Success', f'Data and reproducibility metadata saved to:\n{file_path}\n{sidecar}')
        except Exception as e:
            messagebox.showerror('Error saving', f'The file could not be saved:\n{str(e)}')

    def show_analyze_options(self):
        self.option_win = ctk.CTkToplevel(self)
        self.option_win.title('Analysis Options')
        self.option_win.geometry('300x600')
        self.option_win.attributes('-topmost', True)
        ctk.CTkLabel(self.option_win, text='Select Chart Type', font=('Roboto', 16, 'bold')).pack(pady=10)
        if self.current_mode == 'WCA':
            ctk.CTkButton(self.option_win, text='Angles vs sample', command=lambda: self.plot_graph('WCA_EVO')).pack(pady=5, padx=20, fill='x')
            ctk.CTkButton(self.option_win, text='Distribution (Histogram)', command=lambda: self.plot_graph('WCA_HIST')).pack(pady=5, padx=20, fill='x')
            ctk.CTkButton(self.option_win, text='Angles vs sample (Tree Points)', command=lambda: self.plot_graph('WCA_EVO_TWO')).pack(pady=5, padx=20, fill='x')
        elif self.current_mode == 'HIS':
            ctk.CTkButton(self.option_win, text='Diameter vs. Time', command=lambda: self.plot_graph('HIS_DIA_TIME')).pack(pady=5, padx=20, fill='x')
            ctk.CTkButton(self.option_win, text='CA vs. Time', command=lambda: self.plot_graph('HIS_TIME_CA')).pack(pady=5, padx=20, fill='x')
            ctk.CTkButton(self.option_win, text='Angles vs. Diameter', command=lambda: self.plot_graph('HIS_ANG_DIA')).pack(pady=5, padx=20, fill='x')
            ctk.CTkButton(self.option_win, text='Angles vs Contact Area', command=lambda: self.plot_graph('HIS_ANG_AREA')).pack(pady=5, padx=20, fill='x')
            ctk.CTkButton(self.option_win, text='Mean Contact Angle vs Diameter', command=lambda: self.plot_graph('HIS_DIA_CA')).pack(pady=5, padx=20, fill='x')
            ctk.CTkButton(self.option_win, text='Mean Contact Angle vs Diameter (FIT)', command=lambda: self.plot_graph('HIS_DIA_CA_FIT')).pack(pady=5, padx=20, fill='x')
            ctk.CTkButton(self.option_win, text='Contact Angles vs Diameter (FIT)', command=lambda: self.plot_graph('HIS_ANG_DIA_FIT')).pack(pady=5, padx=20, fill='x')
            ctk.CTkButton(self.option_win, text='Multiple plots', command=lambda: self.plot_graph('HIS_MULT')).pack(pady=5, padx=20, fill='x')
            ctk.CTkButton(self.option_win, text='Multiple plots', command=lambda: self.plot_graph('HIS_MULT_FIT')).pack(pady=5, padx=20, fill='x')
        elif self.current_mode == 'DROP':
            ctk.CTkButton(self.option_win, text='Diameter vs. Time', command=lambda: self.plot_graph('DROP_DIA')).pack(pady=5, padx=20, fill='x')
            ctk.CTkButton(self.option_win, text='Beta vs Time', command=lambda: self.plot_graph('DROP_BETA')).pack(pady=5, padx=20, fill='x')
            ctk.CTkButton(self.option_win, text='Beta vs Diameter', command=lambda: self.plot_graph('DROP_BETA_DIA')).pack(pady=5, padx=20, fill='x')
            ctk.CTkButton(self.option_win, text='Beta vs Time', command=lambda: self.plot_graph('DROP_BETA_MAX')).pack(pady=5, padx=20, fill='x')
            ctk.CTkButton(self.option_win, text='Beta vs Time (FIT)', command=lambda: self.plot_graph('DROP_BETA_MAX_FIT')).pack(pady=5, padx=20, fill='x')
            ctk.CTkButton(self.option_win, text='Beta vs Time (Complete)', command=lambda: self.plot_graph('DROP_BETA_MAX_FIT_BEFORE_AFTER')).pack(pady=5, padx=20, fill='x')
            ctk.CTkButton(self.option_win, text='Diameter X H', command=lambda: self.plot_graph('DROP_DIA_ALT')).pack(pady=5, padx=20, fill='x')
            ctk.CTkButton(self.option_win, text='Spray Cone Angle vs Time', command=lambda: self.plot_graph('DROP_SPRAY_ANGLE'), fg_color='#1f538d').pack(pady=5, padx=20, fill='x')
            ctk.CTkButton(self.option_win, text='Secondary Droplet Size Distribution', command=lambda: self.plot_graph('DROP_DROPLET_DIST'), fg_color='#1f538d').pack(pady=5, padx=20, fill='x')
            ctk.CTkButton(self.option_win, text='Generate Frames from Video', command=self.generate_video_sequence, fg_color='#1f538d').pack(pady=5, padx=20, fill='x')
            ctk.CTkButton(self.option_win, text='Generate Masked Frames Panel', command=self.generate_masked_video_sequence, fg_color='#28a745').pack(pady=5, padx=20, fill='x')
