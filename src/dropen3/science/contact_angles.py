from __future__ import annotations
import math
import cv2
import numpy as np


def select_point_callback(event, x, y, flags, param):
    points, img, name_window = param
    if event == cv2.EVENT_LBUTTONDOWN:
        points.append((x, y))
        cv2.circle(img, (x, y), 1, (0, 0, 255), -1)
        cv2.imshow(name_window, img)


def points_near_baseline(contour, y_baseline, height=40):
    points_valid = []
    for x, y in contour:
        if y_baseline - height <= y <= y_baseline:
            points_valid.append((x, y))
    return np.array(points_valid)


def split_sides(points):
    if points.size == 0:
        return (np.array([]), np.array([]))
    center = np.mean(points[:, 0])
    left = points[points[:, 0] < center]
    right = points[points[:, 0] >= center]
    return (left, right)


def calculate_dropy_angle(points, side):
    x = points[:, 0]
    y = points[:, 1]
    coef = np.polyfit(x, y, 2)
    p = np.poly1d(coef)
    dp = np.polyder(p)
    idx = np.argmax(y)
    x0 = x[idx]
    slope = dp(x0)
    angle_baseline = math.degrees(math.atan(abs(slope)))
    if side == 'left':
        angle = 180 - angle_baseline if slope > 0 else angle_baseline
    else:
        angle = 180 - angle_baseline if slope < 0 else angle_baseline
    return (angle, slope)


def draw_tangents(frame, p_left, p_right, viz_left, viz_right):
    h, w = frame.shape[:2]
    if viz_left is not None and p_left is not None:
        a, b = np.polyfit(viz_left[:, 0], viz_left[:, 1], 1)
        x0, x1 = (max(int(p_left[0] - 20), 0), min(int(p_left[0] + 20), w - 1))
        y0, y1 = (a * x0 + b, a * x1 + b)
        cv2.line(frame, (int(x0), int(y0)), (int(x1), int(y1)), (0, 0, 255), 1)
        cv2.circle(frame, p_left, 1, (0, 0, 255), -1)
    if viz_right is not None and p_right is not None:
        a, b = np.polyfit(viz_right[:, 0], viz_right[:, 1], 1)
        x0, x1 = (max(int(p_right[0] - 20), 0), min(int(p_right[0] + 20), w - 1))
        y0, y1 = (a * x0 + b, a * x1 + b)
        cv2.line(frame, (int(x0), int(y0)), (int(x1), int(y1)), (255, 0, 255), 1)
        cv2.circle(frame, p_right, 1, (255, 0, 255), -1)
    return frame


def calculate_diameter(contour, frame):
    coords = contour.reshape(-1, 2)
    x_min = coords[:, 0].min()
    x_max = coords[:, 0].max()
    diameter = x_max - x_min
    y_mean = int(coords[:, 1].mean())
    p1 = (x_min, y_mean)
    p2 = (x_max, y_mean)
    cv2.line(frame, p1, p2, (0, 0, 255), 2)
    return (diameter, p1, p2)


def baseline_internal_angle(contour, y_baseline, margin_baseline=5, n_tangent_points=15, min_points=4):
    coords = contour.reshape(-1, 2)
    band = coords[np.abs(coords[:, 1] - y_baseline) <= margin_baseline]
    if len(band) < min_points:
        return (np.nan, np.nan, None, None, None, None)
    x_min = band[:, 0].min()
    x_max = band[:, 0].max()
    left = band[band[:, 0] <= x_min + n_tangent_points]
    right_ = band[band[:, 0] >= x_max - n_tangent_points]
    try:
        a_left, _ = np.polyfit(left[:, 0], left[:, 1], 1)
        angle_left = 180 - math.degrees(math.atan(a_left))
        p_left = (int(left[:, 0].mean()), int(left[:, 1].mean()))
        viz_left = left
    except:
        angle_left = np.nan
        p_left = None
        viz_left = None
    try:
        a_right, _ = np.polyfit(right_[:, 0], right_[:, 1], 1)
        angle_right = 180 + math.degrees(math.atan(a_right))
        p_right = (int(right_[:, 0].mean()), int(right_[:, 1].mean()))
        viz_right = right_
    except:
        angle_right = np.nan
        p_right = None
        viz_right = None
    return (angle_left, angle_right, p_left, p_right, viz_left, viz_right)


def weighted_baseline_angle(contour, y_baseline, margin_baseline=15, n_tangent_points=30, min_points=5):
    points = contour.reshape(-1, 2).astype(float)
    window_vertical = points[np.abs(points[:, 1] - y_baseline) <= margin_baseline]
    if len(window_vertical) < min_points:
        window_vertical = points[np.abs(points[:, 1] - y_baseline) <= margin_baseline + 15]
        if len(window_vertical) < min_points:
            return (np.nan, np.nan, None, None, None, None)
    x_min = np.min(window_vertical[:, 0])
    x_max = np.max(window_vertical[:, 0])
    points_left = points[(points[:, 0] <= x_min + n_tangent_points) & (np.abs(points[:, 1] - y_baseline) <= margin_baseline + 20)]
    points_right = points[(points[:, 0] >= x_max - n_tangent_points) & (np.abs(points[:, 1] - y_baseline) <= margin_baseline + 20)]
    if len(points_left) > n_tangent_points:
        dist_left = np.sqrt((points_left[:, 0] - x_min) ** 2 + (points_left[:, 1] - y_baseline) ** 2)
        idx = np.argsort(dist_left)
        points_left = points_left[idx[:n_tangent_points]]
    if len(points_right) > n_tangent_points:
        dist_right = np.sqrt((points_right[:, 0] - x_max) ** 2 + (points_right[:, 1] - y_baseline) ** 2)
        idx = np.argsort(dist_right)
        points_right = points_right[idx[:n_tangent_points]]

    def fit_individual_tangent(points, x_contato, side='left'):
        if len(points) < 3:
            return (np.nan, None)
        try:
            x = points[:, 0]
            y = points[:, 1]
            distances = np.abs(x - x_contato)
            max_dist = np.max(distances)
            if max_dist == 0:
                max_dist = 1.0
            pesos = np.exp(-distances / max_dist)
            grau = 2 if len(points) >= 6 else 1
            coeffs = np.polyfit(x, y, grau, w=pesos)
            p = np.poly1d(coeffs)
            derivative = p.deriv()
            m = float(derivative(x_contato))
            angle_rad = math.atan(abs(m))
            angle_deg = math.degrees(angle_rad)
            if side == 'left':
                angle_final = 180 - angle_deg if m > 0 else angle_deg
            else:
                angle_final = 180 - angle_deg if m < 0 else angle_deg
            point_visual = (int(x_contato), int(p(x_contato)))
            return (angle_final, point_visual)
        except Exception as e:
            print(f'Weighted fit error ({side}): {e}')
            return (np.nan, None)
    angle_left, p_left = fit_individual_tangent(points_left, x_min, side='left')
    angle_right, p_right = fit_individual_tangent(points_right, x_max, side='right')
    return (angle_left, angle_right, p_left, p_right, points_left, points_right)


def polynomial_baseline_angle(contour, y_baseline, margin_baseline=10, n_tangent_points=15, min_points=4):
    coords = contour.reshape(-1, 2)
    band = coords[np.abs(coords[:, 1] - y_baseline) <= margin_baseline]
    if len(band) < min_points:
        return (np.nan, np.nan, None, None, None, None)
    x_min = band[:, 0].min()
    x_max = band[:, 0].max()
    left = band[band[:, 0] <= x_min + n_tangent_points]
    right_ = band[band[:, 0] >= x_max - n_tangent_points]

    def calculate_polynomial_angle(points, x_contato, side='left'):
        if len(points) < 5:
            return (np.nan, None)
        coeffs = np.polyfit(points[:, 0], points[:, 1], 4)
        p = np.poly1d(coeffs)
        derivative = p.deriv()
        m = derivative(x_contato)
        angle_rad = math.atan(m)
        angle_deg = math.degrees(angle_rad)
        if side == 'left':
            return (abs(angle_deg), (int(x_contato), int(p(x_contato))))
        else:
            return (abs(angle_deg), (int(x_contato), int(p(x_contato))))
    try:
        angle_left, p_left = calculate_polynomial_angle(left, x_min, side='left')
    except:
        angle_left, p_left = (np.nan, None)
    try:
        angle_right, p_right = calculate_polynomial_angle(right_, x_max, side='right')
    except:
        angle_right, p_right = (np.nan, None)
    return (angle_left, angle_right, p_left, p_right, left, right_)


def calculate_weighted_angle(points, side):
    if len(points) < 5:
        return 0.0
    x = points[:, 0].astype(float)
    y = points[:, 1].astype(float)
    x_contato = np.min(x) if side == 'left' else np.max(x)
    distances = np.abs(x - x_contato)
    pesos = np.exp(-distances / (np.max(distances) + 1e-05))
    try:
        coef = np.polyfit(x, y, 2, w=pesos)
        p = np.poly1d(coef)
        dp = np.polyder(p)
        slope = dp(x_contato)
        angle_rad = math.atan(abs(slope))
        angle_deg = math.degrees(angle_rad)
        if side == 'left':
            return 180 - angle_deg if slope > 0 else angle_deg
        else:
            return 180 - angle_deg if slope < 0 else angle_deg
    except:
        return 0.0


def draw_angle_arc(img, point_baseline, angle, side='left', radius=15, color=(255, 0, 0)):
    x0, y0 = point_baseline
    if side == 'left':
        start, end = (360 - angle, 360)
    else:
        start, end = (180, 180 + angle)
    cv2.ellipse(img, (int(x0), int(y0)), (radius, radius), 0, start, end, color, 2)
