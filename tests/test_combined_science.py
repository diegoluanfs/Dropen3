"""Synthetic checks of the combined scientific contracts (not lab validation)."""
import dataclasses
import math
import numpy as np
import pytest

from dropen3.science.combined import (Baseline, CombinedConfig, CombinedFrameResult,
                                     physical_summary)
from dropen3.science.metrics import LiquidProperties


LIQUID = LiquidProperties(1000, 0.001, 0.072)


def test_baseline_horizontal_signed_distances():
    line = Baseline((10, 50), (110, 50))
    assert line.slope == 0
    assert line.signed_distance_px(20, 45) == -5
    assert line.signed_distance_px(20, 55) == 5
    assert line.length_px(20, 60) == 40


def test_baseline_inclined_correct_normal_geometry():
    line = Baseline((0, 0), (100, 100))
    assert line.y_at(25) == 25
    assert line.signed_distance_px(0, math.sqrt(2)) == pytest.approx(1)
    assert line.length_px(0, 10) == pytest.approx(math.sqrt(200))


@pytest.mark.parametrize('end', [(1, 100), (1, 1)])
def test_vertical_baseline_rejected(end):
    with pytest.raises(ValueError, match='Vertical'):
        Baseline((1, 0), end)


def test_invalid_baseline_pixels_rejected():
    with pytest.raises(ValueError, match='finite'):
        Baseline((float('nan'), 0), (1, 1))


def test_backward_contacts_rejected():
    with pytest.raises(ValueError, match='ordered'):
        Baseline((0, 50), (100, 50)).length_px(100, 10)


@pytest.mark.parametrize('key,value', [('acquisition_fps', 0), ('mm_per_pixel', -1),
                                      ('min_secondary_area_px2', -5),
                                      ('max_tracking_distance_px', float('nan'))])
def test_invalid_configuration_rejected(key, value):
    kwargs = dict(acquisition_fps=1000, mm_per_pixel=0.01, liquid=LIQUID)
    kwargs[key] = value
    with pytest.raises(ValueError):
        CombinedConfig(**kwargs)


def test_invalid_threshold_and_tracking_rejected():
    with pytest.raises(ValueError):
        CombinedConfig(1000, .01, LIQUID, secondary_threshold=300)
    with pytest.raises(ValueError):
        CombinedConfig(1000, .01, LIQUID, maximum_missed_frames=-1)
    with pytest.raises(ValueError):
        CombinedConfig(1000, .01, LIQUID, min_velocity_samples=2)


def test_legacy_parameter_units():
    config = CombinedConfig.from_legacy_parameters(dict(
        fps_real=2000, scale=0.05, density=995, viscosity=.0012,
        tension=.073, tolerance=4))
    assert config.acquisition_fps == 2000
    assert config.mm_per_pixel == .05
    assert config.liquid.dynamic_viscosity_pa_s == .0012


def test_contact_relative_time_keeps_original_index():
    row = CombinedFrameResult(21, .021).with_time_origin(20, 1000)
    assert row.frame_index == 21
    assert row.acquisition_time_s == .021
    assert row.contact_time_s == .001
    assert CombinedFrameResult(21, .021).with_time_origin(None, 1000).contact_time_s is None


def test_summary_dimensionless_identity_and_maximum():
    rows = [CombinedFrameResult(4, .004, spreading_factor=1.1),
            CombinedFrameResult(5, .005, spreading_factor=1.5)]
    summary = physical_summary(4, 2., 1., LIQUID, rows)
    assert summary.reynolds == pytest.approx(2000)
    assert summary.weber == pytest.approx(1000 * .002 / .072)
    assert summary.ohnesorge == pytest.approx(math.sqrt(summary.weber) / summary.reynolds)
    assert summary.maximum_spreading_factor == 1.5
    assert summary.maximum_spreading_frame == 5


def test_missing_information_cannot_be_replaced_by_d0_one():
    summary = physical_summary(None, None, None, LIQUID, [])
    assert summary.first_contact_frame is None
    assert summary.initial_diameter_mm is None
    assert summary.reynolds is None
    assert summary.maximum_spreading_factor is None


def test_result_is_immutable():
    row = CombinedFrameResult(1, 0.001)
    with pytest.raises(dataclasses.FrozenInstanceError):
        row.frame_index = 100
