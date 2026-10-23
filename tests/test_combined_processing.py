"""Headless synthetic-video regression for combined analysis and tracking."""
import math
import numpy as np
import cv2
import pytest

from dropen3.analysis.combined_core import (
    CombinedSession, Detection, SimpleTracker, primary_geometry, segment_masks,
    select_primary_contour, secondary_detections, spray_envelope_angle,
)
from dropen3.science.combined import Baseline, CombinedConfig
from dropen3.science.metrics import LiquidProperties


@pytest.fixture
def config():
    return CombinedConfig(1000, .01, LiquidProperties(1000, .001, .072),
                          primary_threshold=12, secondary_threshold=12,
                          min_primary_area_px2=30, min_secondary_area_px2=4,
                          max_secondary_area_px2=250)


@pytest.fixture
def baseline():
    return Baseline((0, 90), (199, 90))


def background():
    return np.full((140, 200, 3), 255, dtype=np.uint8)


def frame(y=50, *, secondary=()):
    img = background()
    cv2.circle(img, (100, y), 12, (0, 0, 0), -1)
    for x, sy in secondary:
        cv2.circle(img, (x, sy), 4, (0, 0, 0), -1)
    return img


def test_reference_size_mismatch_raises(config, baseline):
    with pytest.raises(ValueError, match='dimensions'):
        segment_masks(frame(), np.zeros((10, 10), dtype=np.uint8), config, baseline)


def test_segmentation_does_not_mutate_source(config, baseline):
    original = frame(50, secondary=[(40, 105)])
    copy = original.copy()
    primary, secondary = segment_masks(original, cv2.cvtColor(background(), cv2.COLOR_BGR2GRAY), config, baseline)
    assert np.array_equal(original, copy)
    assert primary.shape == secondary.shape == (140, 200)
    assert secondary[105, 40] > 0
    assert primary[105, 40] == 0


def test_primary_chooses_largest_not_center(config, baseline):
    mask, _ = segment_masks(frame(40), cv2.cvtColor(background(), cv2.COLOR_BGR2GRAY), config, baseline)
    contour = select_primary_contour(mask, config.min_primary_area_px2)
    assert contour is not None and cv2.contourArea(contour) > 350


def test_geometry_is_projected_not_wetted(config, baseline):
    binary, _ = segment_masks(frame(78), cv2.cvtColor(background(), cv2.COLOR_BGR2GRAY), config, baseline)
    contour = select_primary_contour(binary, config.min_primary_area_px2)
    width, height, area = primary_geometry(contour, baseline, config, after_contact=True)
    assert width > 0
    assert height > 0
    assert area > 0
    assert width < 1


def test_no_contact_observation_is_missing(config, baseline):
    binary, _ = segment_masks(frame(20), cv2.cvtColor(background(), cv2.COLOR_BGR2GRAY), config, baseline)
    contour = select_primary_contour(binary, config.min_primary_area_px2)
    assert primary_geometry(contour, baseline, config, after_contact=False)[0] is None
    assert primary_geometry(None, baseline, config, after_contact=True) == (None, None, None)


def test_secondary_regions_and_area(config, baseline):
    mask = np.zeros((140, 200), dtype=np.uint8)
    cv2.circle(mask, (40, 105), 5, 255, -1)
    cv2.circle(mask, (100, 65), 5, 255, -1)
    detections = secondary_detections(mask, baseline, config)
    assert sorted(d.region for d in detections) == ['above', 'below']
    assert all(d.diameter_px > 0 for d in detections)


def test_envelope_requires_multiple_below_baseline():
    base = Baseline((0, 80), (200, 80))
    assert spray_envelope_angle([], base) is None
    assert spray_envelope_angle([Detection(50, 90, 4, 'below')], base) is None
    result = spray_envelope_angle([Detection(30, 110, 3, 'below'),
                                   Detection(170, 110, 3, 'below')], base)
    assert result is not None and 0 < result < 180


def test_tracker_one_to_one_and_temporary_occlusion():
    tracker = SimpleTracker(10, maximum_missed_frames=2)
    first = tracker.update([Detection(5, 5, 2, 'below'), Detection(50, 5, 2, 'below')], 0)
    assert [identity for identity, _ in first] == [1, 2]
    second = tracker.update([Detection(7, 5, 2, 'below')], 1)
    assert second[0][0] == 1
    third = tracker.update([Detection(52, 5, 2, 'below')], 2)
    assert third[0][0] == 2
    assert tracker.total_assigned_ids == 2


def test_tracker_expired_identity_issues_new_track():
    tracker = SimpleTracker(10, maximum_missed_frames=1)
    tracker.update([Detection(5, 5, 2, 'below')], 0)
    tracker.update([], 1)
    tracker.update([], 2)
    later = tracker.update([Detection(5, 5, 2, 'below')], 3)
    assert later[0][0] == 2
    assert tracker.total_assigned_ids == 2


def test_tracker_ties_are_deterministic():
    tracker = SimpleTracker(5)
    tracker.update([Detection(0, 0, 2, 'below'), Detection(2, 0, 2, 'below')], 0)
    assigned = tracker.update([Detection(1, 0, 2, 'below'), Detection(1, 0, 2, 'below')], 1)
    assert [track_id for track_id, _ in assigned] == [1, 2]


def test_complete_session_golden_synthetic(config, baseline):
    session = CombinedSession(config, baseline, background(), 0)
    source = [frame(y) for y in [25, 40, 60, 77, 80, 80]]
    for i, image in enumerate(source):
        row, overlay = session.process(image, i)
        assert overlay.shape == image.shape
        assert np.array_equal(image, source[i])
    rows, summary = session.finalize()
    assert len(rows) == 6
    assert summary.first_contact_frame == 3
    assert rows[3].contact_time_s == 0
    assert rows[0].contact_time_s == pytest.approx(-.003)
    assert summary.initial_diameter_mm > 0
    assert summary.preimpact_velocity_m_s == pytest.approx(.175)
    assert summary.reynolds > 0 and summary.weber > 0 and summary.ohnesorge > 0
    assert summary.maximum_spreading_factor is not None
    assert rows[0].spreading_factor is None
    assert rows[3].spreading_factor is not None
    assert rows[3].projected_area_mm2 > 0


def test_session_requires_monotonic_original_indices(config, baseline):
    session = CombinedSession(config, baseline, background(), 0)
    session.process(frame(), 5)
    with pytest.raises(ValueError, match='strictly increasing'):
        session.process(frame(), 5)


def test_session_missing_contact_means_missing_dimensionless_groups(config, baseline):
    session = CombinedSession(config, baseline, background(), 0)
    for index, y in enumerate((12, 25, 35)):
        session.process(frame(y), index)
    _, summary = session.finalize()
    assert summary.first_contact_frame is None
    assert summary.preimpact_velocity_m_s is None
    assert summary.reynolds is None


def test_session_reset_is_deterministic(config, baseline):
    frames = [frame(y, secondary=[(40 + idx, 105)]) for idx, y in enumerate((25, 40, 60, 77))]
    runs = []
    for _ in range(2):
        session = CombinedSession(config, baseline, background(), 0)
        for i, image in enumerate(frames):
            session.process(image, i)
        result, summary = session.finalize()
        runs.append((result, summary, session.observations))
    assert runs[0] == runs[1]


def test_preimpact_velocity_is_normal_to_an_inclined_baseline(config):
    """Horizontal motion parallel to a substrate is not impact-normal velocity."""
    base = Baseline((0, 50), (200, 90))
    session = CombinedSession(config, base, background(), 0)
    for index, x in enumerate((40, 60, 80, 100)):
        original = background()
        # First three droplet centers have constant normal distance to baseline.
        y = int(base.y_at(x) - (30 if index < 3 else 8))
        cv2.circle(original, (x, y), 7, (0, 0, 0), -1)
        session.process(original, index)
    assert session.first_contact_frame == 3
    assert len(session.preimpact_positions) == 3
    assert np.ptp([d for _, d in session.preimpact_positions]) < 0.1
    _, summary = session.finalize()
    assert summary.preimpact_velocity_m_s == pytest.approx(0, abs=1e-9)
