"""Regression tests for combined figures and lossless individual-observation export.

These tests exercise software contracts, not experimental measurement accuracy.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import cv2
import pytest

from dropen3.analysis.combined import CombinedAnalysisMixin, COMBINED_COLUMNS, row_values
from dropen3.analysis.combined_core import CombinedSession
from dropen3.analysis.combined_plotting import (
    PLOT_TITLES, draw_combined_plot, individual_secondary_diameters, valid_pairs,
)
from dropen3.science.combined import Baseline, CombinedConfig, CombinedFrameResult, SecondaryObservation
from dropen3.science.metrics import LiquidProperties


@pytest.fixture
def combined_session():
    config = CombinedConfig(1000, 0.01, LiquidProperties(1000, 0.001, 0.072),
                            min_primary_area_px2=30, secondary_threshold=12,
                            primary_threshold=12, min_secondary_area_px2=4,
                            max_secondary_area_px2=250)
    reference = np.full((140, 200, 3), 255, dtype=np.uint8)
    session = CombinedSession(config, Baseline((0, 90), (199, 90)), reference, 0)
    for index, y in enumerate((25, 40, 60, 77, 82, 82, 82)):
        frame = reference.copy()
        cv2.circle(frame, (100, y), 12, (0, 0, 0), -1)
        cv2.circle(frame, (40 + index, 109), 4, (0, 0, 0), -1)
        cv2.circle(frame, (150 - index, 111), 4, (0, 0, 0), -1)
        session.process(frame, index)
    session.finalize()
    return session


def test_plot_registry_has_ten_unique_english_codes():
    assert len(PLOT_TITLES) == len(set(PLOT_TITLES)) == 10
    assert all(name.startswith('COMBINED_') for name in PLOT_TITLES)


def test_every_combined_plot_handles_measured_session(combined_session):
    try:
        for code in PLOT_TITLES:
            try:
                fig = draw_combined_plot(combined_session, code)
            except ValueError as exc:
                # A plot may correctly refuse unavailable observations.
                assert 'No valid measurements' in str(exc) or 'At least three' in str(exc)
            else:
                assert fig.axes
                assert fig.axes[0].get_title() == PLOT_TITLES[code]
                assert fig.axes[0].get_xlabel()
                assert fig.axes[0].get_ylabel()
                plt.close(fig)
    finally:
        plt.close('all')


def test_invalid_plot_identifier_is_rejected(combined_session):
    with pytest.raises(ValueError, match='Unknown'):
        draw_combined_plot(combined_session, 'COMBINED_UNSUPPORTED')


def test_invalid_pairs_are_ignored():
    results = [CombinedFrameResult(0, 0., contact_time_s=None, contact_width_mm=1),
               CombinedFrameResult(1, .001, contact_time_s=.001, contact_width_mm=float('nan')),
               CombinedFrameResult(2, .002, contact_time_s=.002, contact_width_mm=2)]
    assert valid_pairs(results, 'contact_time_s', 'contact_width_mm') == [(.002, 2.)]


def test_quadratic_fit_requires_three_distinct_timestamps():
    class Session:
        rows = [CombinedFrameResult(1, .001, .001, spreading_factor=1),
                CombinedFrameResult(2, .002, .002, spreading_factor=2)]
        observations = []
    with pytest.raises(ValueError, match='three distinct'):
        draw_combined_plot(Session(), 'COMBINED_BETA_FIT')


def test_size_distribution_counts_tracks_not_frames():
    observations = [
        SecondaryObservation(0, 1, 2, 2, 4, 'below'),
        SecondaryObservation(1, 1, 3, 2, 5, 'below'),
        SecondaryObservation(0, 2, 4, 2, 6, 'above'),
        SecondaryObservation(1, 2, 4, 2, 7, 'below'),
    ]
    assert individual_secondary_diameters(observations) == [4, 7]


def test_csv_schema_matches_row_tuple(combined_session):
    assert len(COMBINED_COLUMNS) == len(row_values(combined_session.rows[0]))
    assert COMBINED_COLUMNS[0] == 'Frame'
    assert COMBINED_COLUMNS[-1] == 'Frame Status'


def test_export_preserves_every_observation_and_metadata(tmp_path: Path, combined_session):
    class FakeApplication(CombinedAnalysisMixin):
        pass

    app = FakeApplication()
    app.combined_session = combined_session
    app.combined_summary = combined_session.finalize()[1]
    app.combined_selected_baseline_frame = 0
    created = app.save_combined_observations(tmp_path / 'combined.csv')
    assert len(created) == 2
    with created[0].open(encoding='utf-8', newline='') as stream:
        observations = list(csv.DictReader(stream))
    assert len(observations) == len(combined_session.observations)
    assert observations
    assert all(int(row['track_id']) >= 1 for row in observations)
    data = json.loads(created[1].read_text(encoding='utf-8'))
    assert data['measurement_status'] == 'EXPLORATORY_NOT_VALIDATED'
    assert data['configuration']['acquisition_fps'] == 1000
    assert data['reference_frame_index'] == 0
    assert data['preimpact_velocity_fit_direction'] == 'substrate_normal'
    assert data['preimpact_velocity_fit_frame_indices'] == [0, 1, 2]
    assert data['initial_diameter_sample_count'] == 3
    assert data['impact_summary']['first_contact_frame'] == combined_session.first_contact_frame
    assert 'not confirmed unique physical droplets' in data['semantics']['cumulative_track_count']


def test_export_without_session_writes_nothing(tmp_path):
    class FakeApplication(CombinedAnalysisMixin):
        pass
    app = FakeApplication()
    assert app.save_combined_observations(tmp_path / 'unused.csv') == []
    assert list(tmp_path.iterdir()) == []


def test_frame_results_support_negative_pre_contact_time(combined_session):
    assert combined_session.rows[0].contact_time_s < 0
    assert combined_session.rows[combined_session.first_contact_frame].contact_time_s == 0
