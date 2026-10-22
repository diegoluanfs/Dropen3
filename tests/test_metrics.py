import math
import pytest
from dropen3.science.metrics import (
    LiquidProperties, dimensionless_numbers, contact_width_m,
    spreading_factor, maximum_spreading_factor, original_frame_time,
    contact_angle_hysteresis,
)


def test_dimensionless_reference_values():
    water = LiquidProperties(1000, 0.001, 0.072)
    result = dimensionless_numbers(2, 0.002, water)
    assert result.reynolds == pytest.approx(4000)
    assert result.weber == pytest.approx(111.11111111)
    assert result.ohnesorge == pytest.approx(math.sqrt(result.weber) / result.reynolds)


def test_physical_input_validation():
    with pytest.raises(ValueError):
        LiquidProperties(1000, 0.0, 0.072)
    with pytest.raises(ValueError):
        LiquidProperties(1000, 0.001, float('nan'))
    with pytest.raises(ValueError):
        dimensionless_numbers(-1, 0.002, LiquidProperties(1000, 0.001, 0.072))
    with pytest.raises(ValueError):
        dimensionless_numbers(1, 0, LiquidProperties(1000, 0.001, 0.072))


def test_timing_of_skipped_frames_uses_original_indices():
    assert original_frame_time(120, 100, 10000) == pytest.approx(0.002)
    assert original_frame_time(98, 100, 10000) == pytest.approx(-0.0002)
    with pytest.raises(ValueError):
        original_frame_time(2, 0, 0)


def test_contact_width_is_not_maximum_silhouette_width():
    width = contact_width_m(120, 180, 1e-5)
    assert width == pytest.approx(0.0006)
    assert spreading_factor(width, 0.0003) == pytest.approx(2)
    assert maximum_spreading_factor([0.0004, 0.0006, 0.0005], 0.0003) == pytest.approx(2)
    with pytest.raises(ValueError):
        contact_width_m(180, 120, 1e-5)


def test_hysteresis_requires_defined_angle_pair():
    assert contact_angle_hysteresis(150, 100) == 50
    with pytest.raises(ValueError):
        contact_angle_hysteresis(90, 110)
