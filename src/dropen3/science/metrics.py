"""Reference measurement definitions from the Dropen3 research manuscript.

The functions are independent of the UI and validate dimensions before returning
values. Scientific accuracy depends on separately validated image measurements.
All physical values are in SI units unless explicitly named otherwise.
"""
from __future__ import annotations
from dataclasses import dataclass
import math
from collections.abc import Sequence


def _finite(value: float, name: str, *, positive: bool = False) -> float:
    value = float(value)
    if not math.isfinite(value) or (positive and value <= 0):
        condition = "a positive finite" if positive else "a finite"
        raise ValueError(f"{name} must be {condition} number")
    return value


@dataclass(frozen=True)
class LiquidProperties:
    density_kg_m3: float
    dynamic_viscosity_pa_s: float
    surface_tension_n_m: float

    def __post_init__(self):
        _finite(self.density_kg_m3, "density_kg_m3", positive=True)
        _finite(self.dynamic_viscosity_pa_s, "dynamic_viscosity_pa_s", positive=True)
        _finite(self.surface_tension_n_m, "surface_tension_n_m", positive=True)


@dataclass(frozen=True)
class DimensionlessNumbers:
    reynolds: float
    weber: float
    ohnesorge: float


def dimensionless_numbers(velocity_m_s: float, diameter_m: float,
                          liquid: LiquidProperties) -> DimensionlessNumbers:
    velocity = _finite(velocity_m_s, "velocity_m_s")
    diameter = _finite(diameter_m, "diameter_m", positive=True)
    if velocity < 0:
        raise ValueError("velocity_m_s must be non-negative; supply velocity magnitude")
    rho, mu, gamma = liquid.density_kg_m3, liquid.dynamic_viscosity_pa_s, liquid.surface_tension_n_m
    re = rho * velocity * diameter / mu
    we = rho * velocity ** 2 * diameter / gamma
    oh = mu / math.sqrt(rho * gamma * diameter)
    results = DimensionlessNumbers(re, we, oh)
    for name, value in vars(results).items():
        _finite(value, name)
    return results


def original_frame_time(frame_index: int, first_contact_index: int, acquisition_fps: float) -> float:
    """Return time relative to first contact, even when intervening frames are skipped."""
    fps = _finite(acquisition_fps, "acquisition_fps", positive=True)
    if not isinstance(frame_index, int) or not isinstance(first_contact_index, int):
        raise TypeError("Frame indices must be integers")
    if frame_index < 0 or first_contact_index < 0:
        raise ValueError("Frame indices must be non-negative")
    return (frame_index - first_contact_index) / fps


def contact_width_m(left_contact_x_px: float, right_contact_x_px: float,
                    scale_m_per_pixel: float) -> float:
    """Width between the left and right substrate contact positions; not silhouette width."""
    left = _finite(left_contact_x_px, "left_contact_x_px")
    right = _finite(right_contact_x_px, "right_contact_x_px")
    scale = _finite(scale_m_per_pixel, "scale_m_per_pixel", positive=True)
    if right < left:
        raise ValueError("Right contact position must not precede left contact position")
    return (right - left) * scale


def spreading_factor(contact_width_m_value: float, preimpact_diameter_m: float) -> float:
    contact_width = _finite(contact_width_m_value, "contact_width_m")
    diameter = _finite(preimpact_diameter_m, "preimpact_diameter_m", positive=True)
    if contact_width < 0:
        raise ValueError("Contact width must be non-negative")
    return contact_width / diameter


def maximum_spreading_factor(widths_m: Sequence[float], preimpact_diameter_m: float) -> float:
    if not widths_m:
        raise ValueError("At least one measurement is required")
    return max(spreading_factor(w, preimpact_diameter_m) for w in widths_m)


def contact_angle_hysteresis(advancing_angle_deg: float, receding_angle_deg: float) -> float:
    """For externally selected advancing/receding angles under a specified protocol."""
    advancing = _finite(advancing_angle_deg, "advancing_angle_deg")
    receding = _finite(receding_angle_deg, "receding_angle_deg")
    if not 0 <= receding <= 180 or not 0 <= advancing <= 180:
        raise ValueError("Contact angles must be between 0 and 180 degrees")
    if advancing < receding:
        raise ValueError("Advancing angle must be >= receding angle for this definition")
    return advancing - receding
