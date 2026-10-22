import numpy as np
from dropen3.science.contact_angles import points_near_baseline, split_sides, calculate_dropy_angle


def test_near_baseline_excludes_below_substrate():
    contour = np.array([[5, 85], [7, 100], [9, 110], [11, 70]])
    filtered = points_near_baseline(contour, y_baseline=100, height=20)
    assert filtered.tolist() == [[5, 85], [7, 100]]


def test_empty_contour_split():
    left, right = split_sides(np.array([]))
    assert left.size == right.size == 0


def test_quadratic_derivative_returns_finite_result():
    xs = np.arange(10, 20)
    contour = np.column_stack([xs, (xs - 10) ** 2])
    angle, slope = calculate_dropy_angle(contour, "left")
    assert np.isfinite(angle) and np.isfinite(slope)
