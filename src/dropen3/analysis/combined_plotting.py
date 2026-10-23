"""Named, typed plot series for the exploratory combined analysis mode."""
from __future__ import annotations

import math
import numpy as np
import matplotlib.pyplot as plt

PLOT_TITLES = {
    'COMBINED_WIDTH': 'Substrate Contact Width vs Time',
    'COMBINED_BETA': 'Spreading Factor vs Time',
    'COMBINED_BETA_WIDTH': 'Spreading Factor vs Contact Width',
    'COMBINED_EXPANSION': 'Expansion to Maximum Spreading',
    'COMBINED_BETA_FIT': 'Quadratic Spreading Trend',
    'COMBINED_COMPLETE': 'Complete Spreading and Recoil',
    'COMBINED_HEIGHT_WIDTH': 'Height vs Contact Width',
    'COMBINED_ANGLE': '2D Spray Envelope Angle vs Acquisition Time',
    'COMBINED_SIZES': 'Individual Secondary Droplet Diameters',
    'COMBINED_COUNTS': 'Visible Droplets and Cumulative Assigned Track IDs',
}


def valid_pairs(rows, x_field, y_field):
    pairs = []
    for row in rows:
        x, y = getattr(row, x_field), getattr(row, y_field)
        if x is not None and y is not None and math.isfinite(x) and math.isfinite(y):
            pairs.append((float(x), float(y)))
    return pairs


def individual_secondary_diameters(observations):
    """Take the first below-baseline diameter of each track, not frame averages."""
    samples = {}
    for item in observations:
        if item.region == 'below' and item.track_id not in samples:
            samples[item.track_id] = item.equivalent_diameter_px
    return list(samples.values())


def draw_combined_plot(session, code):
    if code not in PLOT_TITLES:
        raise ValueError('Unknown combined plot identifier')
    rows = session.rows
    fig, axis = plt.subplots(figsize=(8, 5))
    x_label, y_label = 'Contact-Relative Time (s)', ''
    if code == 'COMBINED_SIZES':
        values = individual_secondary_diameters(session.observations)
        if not values:
            plt.close(fig)
            raise ValueError('No individual below-baseline droplet measurements are available')
        axis.hist(values, bins=min(20, max(1, int(math.sqrt(len(values))))))
        x_label, y_label = 'First Measured Diameter per Track (px)', 'Track Count'
    elif code == 'COMBINED_COUNTS':
        x = [row.acquisition_time_s for row in rows]
        y1 = [row.visible_secondary_count for row in rows]
        y2 = [row.cumulative_track_count for row in rows]
        axis.plot(x, y1, label='Visible Secondary Droplets')
        axis.plot(x, y2, label='Cumulative Assigned Track IDs')
        axis.legend()
        x_label, y_label = 'Acquisition Time (s)', 'Count'
    else:
        mapping = {
            'COMBINED_WIDTH': ('contact_time_s', 'contact_width_mm', 'Contact Width (mm)'),
            'COMBINED_BETA': ('contact_time_s', 'spreading_factor', 'Spreading Factor'),
            'COMBINED_BETA_WIDTH': ('contact_width_mm', 'spreading_factor', 'Spreading Factor'),
            'COMBINED_EXPANSION': ('contact_time_s', 'spreading_factor', 'Spreading Factor'),
            'COMBINED_BETA_FIT': ('contact_time_s', 'spreading_factor', 'Spreading Factor'),
            'COMBINED_COMPLETE': ('contact_time_s', 'spreading_factor', 'Spreading Factor'),
            'COMBINED_HEIGHT_WIDTH': ('contact_width_mm', 'height_mm', 'Height (mm)'),
            'COMBINED_ANGLE': ('acquisition_time_s', 'spray_envelope_angle_deg', '2D Envelope Angle (deg)'),
        }
        x_field, y_field, y_label = mapping[code]
        values = sorted(valid_pairs(rows, x_field, y_field))
        if code == 'COMBINED_EXPANSION' and values:
            maximum_index = max(range(len(values)), key=lambda i: values[i][1])
            values = values[:maximum_index + 1]
        if not values:
            plt.close(fig)
            raise ValueError('No valid measurements are available for the requested plot')
        x, y = np.array(values).T
        if code == 'COMBINED_BETA_FIT':
            if len(np.unique(x)) < 3:
                plt.close(fig)
                raise ValueError('At least three distinct contact-relative timestamps are required for a quadratic fit')
            # Center and normalize the time axis for better polynomial conditioning.
            center, scale = x.mean(), max(float(x.max() - x.min()), 1e-12)
            coefficients = np.polyfit((x - center) / scale, y, deg=2)
            axis.plot(x, y, 'o', label='Measured')
            x_line = np.linspace(float(x.min()), float(x.max()), 200)
            axis.plot(x_line, np.polyval(coefficients, (x_line - center) / scale),
                      label='Quadratic descriptive fit')
            axis.legend()
        else:
            axis.plot(x, y, '-o', markersize=3)
        if code in ('COMBINED_BETA_WIDTH', 'COMBINED_HEIGHT_WIDTH'):
            x_label = 'Contact Width (mm)'
        elif code == 'COMBINED_ANGLE':
            x_label = 'Acquisition Time (s)'
        if code == 'COMBINED_COMPLETE':
            maximum_index = int(np.argmax(y))
            axis.axvline(x[maximum_index], linestyle='--', label='Maximum Observed Spreading')
            axis.legend()
    axis.set(xlabel=x_label, ylabel=y_label, title=PLOT_TITLES[code])
    axis.grid(alpha=0.3)
    fig.tight_layout()
    return fig
