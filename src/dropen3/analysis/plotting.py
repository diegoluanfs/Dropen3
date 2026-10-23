from __future__ import annotations
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from tkinter import messagebox
from scipy.signal import savgol_filter


class PlottingMixin:

    def plot_graph(self, type):
        if type.startswith('COMBINED_'):
            from dropen3.analysis.combined_plotting import draw_combined_plot
            session = getattr(self, 'combined_session', None)
            if session is None:
                messagebox.showwarning('No measurements', 'Run combined analysis before plotting.')
                return
            try:
                figure = draw_combined_plot(session, type)
            except ValueError as error:
                messagebox.showwarning('Unavailable measurement', str(error))
                return
            figure.show()
            return
        data = []
        for item in self.tree.get_children():
            data.append(self.tree.item(item)['values'])
        if not data:
            messagebox.showwarning('Warning', 'The data table is empty!')
            return
        df = pd.DataFrame(data)
        plt.figure(figsize=(8, 5))
        if type == 'WCA_EVO':
            df_plot = df.copy()
            df_plot[3] = df_plot[3].astype(float)
            df_plot = df_plot.sort_values(by=3, ascending=True)
            y = df_plot[3].values
            x = df_plot[0].values
            plt.plot(x, y, marker='o', linestyle='-', color='b', label='Average Angle')
            for i, txt in enumerate(y):
                plt.annotate(f'{txt:.1f}', (x[i], y[i]), textcoords='offset points', xytext=(0, 10), ha='center')
            plt.xticks(rotation=45)
            plt.ylabel('Contact Angle (°)')
            plt.title('Evolution of the Contact Angle (Sorted by Value)')
            plt.grid(True, axis='y', linestyle='--', alpha=0.6)
            plt.tight_layout()
        elif type == 'DROP_SPRAY_ANGLE':
            t = df[1].astype(float)
            angle = df[4].astype(float)
            plt.plot(t, angle, color='purple', marker='o', markersize=3)
            plt.xlabel('Time (s)')
            plt.ylabel('Spray Cone Angle (°)')
            plt.title('Evolution of Spray Cone Angle During Impact')
        elif type == 'DROP_DROPLET_DIST':
            all_diameters = []
            for item in self.tree.get_children():
                vals = self.tree.item(item)['values']
            if hasattr(self, 'data') and 'size_distributions' in self.data and self.data['size_distributions']:
                flat_sizes = [d * self.params.get('scale', 0.01) for sublist in self.data['size_distributions'] for d in sublist]
                plt.hist(flat_sizes, bins=20, color='teal', edgecolor='black', alpha=0.7)
                plt.xlabel('Secondary Droplet Diameter (mm)')
                plt.ylabel('Frequency Count')
                plt.title('Size Distribution of Secondary Droplets (Splash/Spray)')
            else:
                plt.text(0.5, 0.5, 'No droplet size data available.', horizontalalignment='center', transform=plt.gca().transAxes)
            plt.grid(True, linestyle='--', alpha=0.5)
        elif type == 'WCA_EVO_TWO':
            df_plot = df.copy()
            df_plot[1] = pd.to_numeric(df_plot[1], errors='coerce')
            df_plot[2] = pd.to_numeric(df_plot[2], errors='coerce')
            df_grouped = df_plot.groupby(0, as_index=False).agg({1: 'mean', 2: 'mean'})
            df_grouped[3] = df_grouped[[1, 2]].mean(axis=1)
            df_grouped = df_grouped.sort_values(by=3, ascending=True)
            y = df_grouped[3].values
            x = df_grouped[0].values
            plt.plot(x, y, marker='o', linestyle='-', color='b', label='Average Angle')
            for i, txt in enumerate(y):
                if not np.isnan(txt):
                    plt.annotate(f'{txt:.1f}', (x[i], y[i]), textcoords='offset points', xytext=(0, 10), ha='center')
            plt.xticks(rotation=45)
            plt.ylabel('Contact Angle (°)')
            plt.title('Evolution of the Contact Angle (Grouped by File)')
            plt.grid(True, axis='y', linestyle='--', alpha=0.6)
            plt.tight_layout()
        elif type == 'DROP_DIA':
            t = df[0].astype(float)
            d = df[2].astype(float)
            plt.scatter(t, d, color='red', s=10)
            plt.xlabel('Time (s)')
            plt.ylabel('Diameter (mm)')
            plt.title('Drop Diameter vs Time')
        elif type == 'HIS_TIME_CA':
            t = pd.to_numeric(df[1], errors='coerce')
            e = pd.to_numeric(df[6], errors='coerce')
            d = pd.to_numeric(df[7], errors='coerce')
            mask = ~t.isna() & ~d.isna() & ~e.isna() & (e <= 170) & (d <= 170)
            t = t[mask]
            e = np.round(e[mask])
            d = np.round(d[mask])
            plt.scatter(t, e, s=10, label='Left angle (°)', color='blue')
            plt.scatter(t, d, s=10, label='Right angle (°)', color='red')
            plt.xlabel('Time (s)')
            plt.ylabel('Contact Angle (°)')
            plt.title('Contact Angle vs Time')
            plt.legend()
        elif type == 'HIS_DIA_CA':
            df[2] = pd.to_numeric(df[2], errors='coerce')
            df[6] = pd.to_numeric(df[6], errors='coerce')
            df[7] = pd.to_numeric(df[7], errors='coerce')
            df_filtered = df[(df[6] <= 170) & (df[7] <= 170)].copy()
            if not df_filtered.empty:
                t = df_filtered[2]
                angle_left = df_filtered[6]
                angle_right = df_filtered[7]
                angle_mean = ((angle_left + angle_right) / 2).round().astype(int)
                plt.scatter(t, angle_mean, color='red', s=10)
                plt.xlabel('Diameter (mm)')
                plt.ylabel('Contact Angle (°)')
                plt.title('Drop Diameter vs Contact Angle')
            else:
                print('Warning: All data were filtered (angles > 180°).')
        elif type == 'HIS_DIA_CA_FIT':
            df[2] = np.round(pd.to_numeric(df[2], errors='coerce'), 0)
            df[3] = np.round(pd.to_numeric(df[6], errors='coerce'), 0)
            df[4] = np.round(pd.to_numeric(df[3], errors='coerce'), 0)
            df_filtered = df[(df[3] <= 170) & (df[4] <= 170)].dropna().copy()
            if not df_filtered.empty:
                t = df_filtered[2].values
                angle_left = df_filtered[3]
                angle_right = df_filtered[4]
                angle_mean = ((angle_left + angle_right) / 2).values
                plt.scatter(t, angle_mean, color='red', s=10, label='Experimental Data')
                if len(t) >= self.min_points_fit:
                    try:
                        z = np.polyfit(t, angle_mean, 1)
                        p = np.poly1d(z)
                        line_time = np.linspace(t.min(), t.max(), 100)
                        plt.plot(line_time, p(line_time), '--', color='blue', linewidth=2, label='Linear Trend')
                        print(f'Fit realizado: y = {z[0]:.4f}x + {z[1]:.4f} (n={len(t)})')
                    except Exception as e:
                        print(f'Error calculating the adjustment: {e}')
                plt.xlabel('Diameter (mm)')
                plt.ylabel('Contact Angle (°)')
                plt.title('Drop Diameter vs Contact Angle')
                plt.legend()
            else:
                print('Warning: All data has been filtered. (angles > 180°).')
        elif type == 'HIS_DIA_TIME':
            time = df[1].astype(float)
            diameters = df[2].astype(float)
            plt.plot(time, diameters, marker='o', markersize=3, linestyle='-', color='purple')
            plt.xlabel('Time (s)')
            plt.ylabel('Diameter (px)')
            plt.title('Evolution of Droplet Diameter')
        elif type == 'HIS_ANG_DIA':
            angle_left = pd.to_numeric(df[6], errors='coerce')
            angle_right = pd.to_numeric(df[7], errors='coerce')
            diameter = pd.to_numeric(df[2], errors='coerce')
            mask = (angle_left <= 170) & (angle_right <= 170)
            angle_left = np.round(angle_left[mask])
            angle_right = np.round(angle_right[mask])
            diameter = diameter[mask]
            fig, ax1 = plt.subplots(figsize=(8, 5))
            color_left, color_right = ('tab:blue', 'tab:red')
            ax1.set_xlabel('Diameter (px)')
            ax1.set_ylabel('Contact Angle (°)', color='black')
            ax1.scatter(diameter, angle_left, color=color_left, label='Left Angle', alpha=0.6)
            ax1.scatter(diameter, angle_right, color=color_right, label='Right Angle', alpha=0.6)
            ax1.tick_params(axis='y', labelcolor='black')
            ax1.legend(loc='upper left')
            ax1.set_title('Correlation: Contact Angles vs. Diameter')
            'Stacked plots sharing a time axis for droplet wettability and hysteresis measurements.\n            '
        elif type == 'HIS_MULT':
            t = pd.to_numeric(df[1], errors='coerce')
            diameter_baseline = pd.to_numeric(df[3], errors='coerce')
            av_left = pd.to_numeric(df[4], errors='coerce')
            av_right = pd.to_numeric(df[5], errors='coerce')
            angle_left = pd.to_numeric(df[6], errors='coerce')
            angle_right = pd.to_numeric(df[7], errors='coerce')
            mask = ~t.isna() & ~angle_left.isna() & ~angle_right.isna() & (angle_left <= 170) & (angle_right <= 170)
            t = t[mask]
            diameter_baseline = diameter_baseline[mask]
            av_left = av_left[mask]
            av_right = av_right[mask]
            angle_left = np.round(angle_left[mask])
            angle_right = np.round(angle_right[mask])
            fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(8, 10), sharex=True)
            ax1.scatter(t, angle_left, s=12, color='blue', label='Left angle. (°)')
            ax1.scatter(t, angle_right, s=12, color='red', label='Right angle. (°)')
            ax1.set_ylabel('$\\theta$ [degree]')
            ax1.set_title('Hysteresis Dynamics vs Time')
            ax1.grid(True, linestyle='--', alpha=0.5)
            ax1.legend(loc='upper right')
            ax2.scatter(t, diameter_baseline, s=12, color='purple', label='Base Diameter', facecolors='none', edgecolors='purple')
            ax2.set_ylabel('Base Diameter [px]')
            ax2.grid(True, linestyle='--', alpha=0.5)
            ax3.scatter(t, av_left, s=12, color='teal', label='Left shift (px)')
            ax3.scatter(t, av_right, s=12, color='darkorange', label='Right shift (px)')
            ax3.set_xlabel('Time [sec]')
            ax3.set_ylabel('Displacement [px]')
            ax3.grid(True, linestyle='--', alpha=0.5)
            ax3.legend(loc='upper right')
        elif type == 'HIS_MULT_FIT':
            from scipy.interpolate import UnivariateSpline
            t = pd.to_numeric(df[1], errors='coerce')
            diameter_baseline = pd.to_numeric(df[3], errors='coerce')
            av_left = pd.to_numeric(df[4], errors='coerce')
            av_right = pd.to_numeric(df[5], errors='coerce')
            angle_left = pd.to_numeric(df[6], errors='coerce')
            angle_right = pd.to_numeric(df[7], errors='coerce')
            mask = ~t.isna() & ~angle_left.isna() & ~angle_right.isna() & (angle_left <= 170) & (angle_right <= 170)
            t = t[mask].to_numpy()
            diameter_baseline = diameter_baseline[mask].to_numpy()
            av_left = av_left[mask].to_numpy()
            av_right = av_right[mask].to_numpy()
            angle_left = np.round(angle_left[mask].to_numpy())
            angle_right = np.round(angle_right[mask].to_numpy())
            sort_idx = np.argsort(t)
            t, diameter_baseline, av_left, av_right, angle_left, angle_right = (t[sort_idx], diameter_baseline[sort_idx], av_left[sort_idx], av_right[sort_idx], angle_left[sort_idx], angle_right[sort_idx])
            t_smooth = np.linspace(t.min(), t.max(), 300)
            fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(8, 10), sharex=True)
            ax1.scatter(t, angle_left, s=12, color='blue', alpha=0.4, label='Left angle (°)')
            ax1.scatter(t, angle_right, s=12, color='red', alpha=0.4, label='Right angle (°)')
            spl_angle_left = UnivariateSpline(t, angle_left, s=len(t) * 2)
            spl_angle_right = UnivariateSpline(t, angle_right, s=len(t) * 2)
            ax1.plot(t_smooth, spl_angle_left(t_smooth), color='darkblue', lw=2, label='Trend (Left)')
            ax1.plot(t_smooth, spl_angle_right(t_smooth), color='darkred', lw=2, label='Trend (Right)')
            ax1.set_ylabel('$\\theta$ [degree]')
            ax1.set_title('Hysteresis Dynamics vs Time')
            ax1.grid(True, linestyle='--', alpha=0.5)
            ax1.legend(loc='upper right')
            ax2.scatter(t, diameter_baseline, s=12, color='purple', alpha=0.4, facecolors='none', edgecolors='purple', label='Base Diameter')
            spl_diameter = UnivariateSpline(t, diameter_baseline, s=len(t) * 1.5)
            ax2.plot(t_smooth, spl_diameter(t_smooth), color='indigo', lw=2, label='Trend (Base)')
            ax2.set_ylabel('Base Diameter [px]')
            ax2.grid(True, linestyle='--', alpha=0.5)
            ax2.legend(loc='upper right')
            ax3.scatter(t, av_left, s=12, color='teal', alpha=0.4, label='Left shift (px)')
            ax3.scatter(t, av_right, s=12, color='darkorange', alpha=0.4, label='Right shift (px)')
            spl_av_left = UnivariateSpline(t, av_left, s=len(t) * 2)
            spl_av_right = UnivariateSpline(t, av_right, s=len(t) * 2)
            ax3.plot(t_smooth, spl_av_left(t_smooth), color='darkslategray', lw=2, label='Trend (Left Shift)')
            ax3.plot(t_smooth, spl_av_right(t_smooth), color='chocolate', lw=2, label='Trend (Right Shift)')
            ax3.set_xlabel('Time [sec]')
            ax3.set_ylabel('Displacement [px]')
            ax3.grid(True, linestyle='--', alpha=0.5)
            ax3.legend(loc='upper right')
        elif type == 'HIS_ANG_DIA_FIT':
            frame = pd.to_numeric(df[0], errors='coerce')
            time = pd.to_numeric(df[1], errors='coerce')
            diameter_raw = pd.to_numeric(df[2], errors='coerce')
            angle_left_raw = pd.to_numeric(df[6], errors='coerce')
            angle_right_raw = pd.to_numeric(df[7], errors='coerce')
            mask_valid = ~diameter_raw.isna() & ~angle_left_raw.isna() & ~angle_right_raw.isna() & (angle_left_raw >= 0) & (angle_left_raw <= 170) & (angle_right_raw >= 0) & (angle_right_raw <= 170)
            frame = frame[mask_valid].to_numpy()
            time = time[mask_valid].to_numpy()
            angle_left = np.round(angle_left_raw[mask_valid].to_numpy(), 0)
            angle_right = np.round(angle_right_raw[mask_valid].to_numpy(), 0)
            diameter = np.round(diameter_raw[mask_valid].to_numpy(), 0)
            if len(diameter) < 5:
                print('Insufficient points for segmentation and fitting.')
                return
            window = min(15, len(diameter) if len(diameter) % 2 != 0 else len(diameter) - 1)
            if window > 3:
                diameter_smoothed = savgol_filter(diameter, window_length=window, polyorder=1)
            else:
                diameter_smoothed = diameter.copy()
            derivative_diameter = np.gradient(diameter_smoothed)
            threshold_static = 0.15
            idx_cresce = np.where(derivative_diameter > threshold_static)[0]
            idx_constante = np.where(np.abs(derivative_diameter) <= threshold_static)[0]
            idx_decresce = np.where(derivative_diameter < -threshold_static)[0]
            fig, ax = plt.subplots(figsize=(9, 6))
            colors_left = {'cresce': '#1f77b4', 'constante': '#17becf', 'decresce': '#aec7e8'}
            colors_right = {'cresce': '#d62728', 'constante': '#ff7f0e', 'decresce': '#ffbb78'}
            if len(idx_cresce) >= 3:
                d_reg = diameter[idx_cresce]
                ae_reg = angle_left[idx_cresce]
                ad_reg = angle_right[idx_cresce]
                ax.scatter(d_reg, ae_reg, color=colors_left['cresce'], alpha=0.4, edgecolors='none')
                ax.scatter(d_reg, ad_reg, color=colors_right['cresce'], alpha=0.4, edgecolors='none')
                spatial_distance = np.linspace(d_reg.min(), d_reg.max(), 100)
                p_left = np.polyfit(d_reg, ae_reg, 1)
                p_right = np.polyfit(d_reg, ad_reg, 1)
                ax.plot(spatial_distance, np.polyval(p_left, spatial_distance), color=colors_left['cresce'], linestyle='-', linewidth=2, label='$\\theta_{Left}$ (Crescente)')
                ax.plot(spatial_distance, np.polyval(p_right, spatial_distance), color=colors_right['cresce'], linestyle='--', linewidth=2, label='$\\theta_{Right}$ (Crescente)')
            if len(idx_constante) >= 3:
                d_reg = diameter[idx_constante]
                ae_reg = angle_left[idx_constante]
                ad_reg = angle_right[idx_constante]
                ax.scatter(d_reg, ae_reg, color=colors_left['constante'], alpha=0.4, edgecolors='none')
                ax.scatter(d_reg, ad_reg, color=colors_right['constante'], alpha=0.4, edgecolors='none')
                p_left_inv = np.polyfit(ae_reg, d_reg, 1)
                left_spatial_angle = np.linspace(ae_reg.min(), ae_reg.max(), 100)
                diameter_fit_left = np.polyval(p_left_inv, left_spatial_angle)
                ax.plot(diameter_fit_left, left_spatial_angle, color=colors_left['constante'], linestyle='-', linewidth=2, label='$\\theta_{Left}$ (Static - Y fit)')
                p_right_inv = np.polyfit(ad_reg, d_reg, 1)
                right_spatial_angle = np.linspace(ad_reg.min(), ad_reg.max(), 100)
                diameter_fit_right = np.polyval(p_right_inv, right_spatial_angle)
                ax.plot(diameter_fit_right, right_spatial_angle, color=colors_right['constante'], linestyle='--', linewidth=2, label='$\\theta_{Right}$ (Static - Y fit)')
            if len(idx_decresce) >= 3:
                d_reg = diameter[idx_decresce]
                ae_reg = angle_left[idx_decresce]
                ad_reg = angle_right[idx_decresce]
                ax.scatter(d_reg, ae_reg, color=colors_left['decresce'], alpha=0.4, edgecolors='none')
                ax.scatter(d_reg, ad_reg, color=colors_right['decresce'], alpha=0.4, edgecolors='none')
                spatial_distance = np.linspace(d_reg.min(), d_reg.max(), 100)
                p_left = np.polyfit(d_reg, ae_reg, 1)
                p_right = np.polyfit(d_reg, ad_reg, 1)
                ax.plot(spatial_distance, np.polyval(p_left, spatial_distance), color=colors_left['decresce'], linestyle='-', linewidth=2, label='$\\theta_{Left}$ (Decrescente)')
                ax.plot(spatial_distance, np.polyval(p_right, spatial_distance), color=colors_right['decresce'], linestyle='--', linewidth=2, label='$\\theta_{Right}$ (Decrescente)')
            ax.set_xlabel('Droplet Base Diameter (px)', fontsize=12, fontweight='bold', labelpad=8)
            ax.set_ylabel('Contact Angle (°)', fontsize=12, fontweight='bold', labelpad=8)
            ax.set_title('WLS Hysteresis Correlation: Contact Angles vs. Base Diameter', fontsize=13, fontweight='bold', pad=12)
            ax.grid(True, linestyle=':', alpha=0.6)
            ax.tick_params(axis='both', which='major', labelsize=10)
            ax.legend(loc='best', fontsize=9, frameon=True, facecolor='#ffffff', edgecolor='#d3d3d3')
            plt.tight_layout()
        elif type == 'HIS_ANG_AREA':
            try:
                angle_left = pd.to_numeric(df[3])
                angle_right = pd.to_numeric(df[4])
                area = pd.to_numeric(df[6])
            except Exception as e:
                messagebox.showerror('Error', 'Insufficient data columns for Area.')
                return
            fig, ax = plt.subplots(figsize=(8, 5))
            angle_mean = (angle_left + angle_right) / 2
            ax.plot(area, angle_mean, color='black', linestyle='--', label='Mean', alpha=0.7)
            ax.set_xlabel('Contact Area (px²)')
            ax.set_ylabel('Contact Angle (°)')
            ax.set_title('Contact Angle vs. Contact Area')
            ax.legend()
        elif type == 'DROP_DIA_ALT':
            t = df[2].astype(float)
            beta = df[4].astype(float)
            plt.plot(t, beta, color='green')
            plt.xlabel('Height')
            plt.ylabel('Diameter')
            plt.title('Height vs. Diameter')
        elif type == 'DROP_BETA':
            t = df[0].astype(float)
            beta = df[3].astype(float)
            plt.plot(t, beta, color='green')
            plt.xlabel('Time (s)')
            plt.ylabel('spreading factor β (D/D0)')
            plt.title('spreading factor β vs. Timer')
        elif type == 'DROP_BETA_MAX_FIT':
            t = df[0].astype(float).values
            beta = df[3].astype(float).values
            idx_max = np.argmax(beta)
            t_exp = t[:idx_max + 1]
            beta_exp = beta[:idx_max + 1]
            coeffs = np.polyfit(t_exp, beta_exp, 2)
            trend_func = np.poly1d(coeffs)
            beta_trend = trend_func(t_exp)
            plt.scatter(t_exp, beta_exp, color='lightgreen', s=10, alpha=0.5, label='Experimental Data')
            plt.plot(t_exp, beta_trend, color='darkgreen', linewidth=2, label='Trend (2nd Order Fit)')
            beta_max = beta_exp[-1]
            t_max = t_exp[-1]
            plt.scatter(t_max, beta_max, color='red', zorder=5)
            plt.annotate(f'Max β: {beta_max:.2f}', xy=(t_max, beta_max), xytext=(t_max, beta_max * 1.05), horizontalalignment='center')
            plt.xlabel('Time (s)')
            plt.ylabel('spreading factor β (D/D0)')
            plt.title('Spreading Factor β: Expansion Trend Analysis')
            plt.legend()
            plt.grid(True, linestyle='--', alpha=0.7)
        elif type == 'DROP_BETA_MAX_FIT_BEFORE_AFTER':
            t = df[0].astype(float).values
            beta = df[3].astype(float).values
            idx_max = np.argmax(beta)
            if idx_max == 0 and len(beta) > 1:
                idx_max = np.argmax(beta[1:]) + 1
            t = t - t[0]
            t_max = t[idx_max]
            beta_max = beta[idx_max]
            x_limit_final = t_max * 4
            plt.xlim(0, x_limit_final)
            t_end_visual = min(t[-1], x_limit_final)
            retraction_center_position = (t_max + t_end_visual) / 2
            plt.plot(t, beta, color='black', marker='s', markersize=4, markerfacecolor='black', label='Experimental Data')
            plt.axvline(x=t_max, color='gray', linestyle='-', linewidth=1.5)
            plt.ylim(0, max(beta) * 1.2)
            y_max_plot = plt.ylim()[1]
            y_text = y_max_plot * 0.9
            plt.text(t_max / 2, y_text, 'Spreading', horizontalalignment='center', fontweight='bold', fontsize=10)
            plt.text(retraction_center_position, y_text, 'Retracting', horizontalalignment='center', fontweight='bold', fontsize=10)
            plt.annotate('', xy=(0, y_text * 1.03), xytext=(t_max, y_text * 1.03), arrowprops=dict(arrowstyle='<->', color='black'))
            plt.annotate('', xy=(t_max, y_text * 1.03), xytext=(t_end_visual, y_text * 1.03), arrowprops=dict(arrowstyle='<->', color='black'))
            y_seta_inferior = y_max_plot * 0.05
            plt.annotate('', xy=(0, y_seta_inferior), xytext=(t_max, y_seta_inferior), arrowprops=dict(arrowstyle='<->', color='red', linestyle='--'))
            plt.text(t_max / 2, y_seta_inferior * 1.3, f'$t_{{max}}$ = {t_max:.4f} s', horizontalalignment='center', color='red', fontweight='bold', fontsize=9)
            plt.xlabel('Time (ms)')
            plt.ylabel('spreading factor $\\beta$ ($D/D_0$)')
            plt.title('Droplet Impact Dynamics')
            plt.grid(False)
            plt.legend(loc='upper right')
        elif type == 'DROP_BETA_MAX':
            t = df[0].astype(float)
            beta = df[3].astype(float)
            idx_max = beta.idxmax()
            t_expansao = t.loc[:idx_max]
            beta_expansao = beta.loc[:idx_max]
            plt.plot(t_expansao, beta_expansao, color='green', linewidth=2)
            beta_max = beta_expansao.iloc[-1]
            t_max = t_expansao.iloc[-1]
            plt.scatter(t_max, beta_max, color='red', zorder=5)
            plt.annotate(f'Max β: {beta_max:.2f}', xy=(t_max, beta_max), xytext=(t_max, beta_max * 1.05), horizontalalignment='center')
            plt.xlabel('Time (s)')
            plt.ylabel('spreading factor β (D/D0)')
            plt.title('Spreading Factor β vs. Time (Expansion Phase)')
            plt.grid(True, linestyle='--', alpha=0.7)
        elif type == 'DROP_BETA_DIA':
            t = df[2].astype(float)
            beta = df[3].astype(float)
            plt.plot(t, beta, color='green')
            plt.xlabel('Diameter')
            plt.ylabel('spreading factor β (D/D0)')
            plt.title('spreading factor β vs. Diameter')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.show()
