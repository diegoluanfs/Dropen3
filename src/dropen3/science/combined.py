"""Scientific contracts for exploratory combined spray and impact measurements.

The estimators in this module are not experimentally validated. All spatial
measurements refer to original source-image pixels; time uses acquisition FPS.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import math
from typing import Optional

from dropen3.science.metrics import LiquidProperties, dimensionless_numbers


def positive_finite(value: float, name: str) -> float:
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be finite and greater than zero")
    return value


@dataclass(frozen=True)
class Baseline:
    """Nonvertical line through two original-image pixel coordinates."""
    p1: tuple[float, float]
    p2: tuple[float, float]

    def __post_init__(self):
        if not all(math.isfinite(float(v)) for p in (self.p1, self.p2) for v in p):
            raise ValueError("Baseline coordinates must be finite")
        if abs(self.p2[0] - self.p1[0]) < 1e-9:
            raise ValueError("Vertical baselines are not supported in side-view analysis")

    @property
    def slope(self) -> float:
        return (self.p2[1] - self.p1[1]) / (self.p2[0] - self.p1[0])

    def y_at(self, x: float) -> float:
        return self.p1[1] + self.slope * (x - self.p1[0])

    def signed_distance_px(self, x: float, y: float) -> float:
        """Positive below substrate, negative above it, in normal pixels."""
        return (y - self.y_at(x)) / math.hypot(1, self.slope)

    def length_px(self, left_x: float, right_x: float) -> float:
        if right_x < left_x:
            raise ValueError("Contact coordinates must be ordered from left to right")
        return (right_x - left_x) * math.hypot(1, self.slope)


@dataclass(frozen=True)
class CombinedConfig:
    acquisition_fps: float
    mm_per_pixel: float
    liquid: LiquidProperties
    min_primary_area_px2: float = 50.0
    min_secondary_area_px2: float = 5.0
    max_secondary_area_px2: float = 2000.0
    primary_threshold: int = 15
    secondary_threshold: int = 120
    contact_tolerance_px: float = 3.0
    max_tracking_distance_px: float = 45.0
    maximum_missed_frames: int = 2
    min_velocity_samples: int = 3

    def __post_init__(self):
        positive_finite(self.acquisition_fps, 'acquisition_fps')
        positive_finite(self.mm_per_pixel, 'mm_per_pixel')
        positive_finite(self.min_primary_area_px2, 'min_primary_area_px2')
        positive_finite(self.min_secondary_area_px2, 'min_secondary_area_px2')
        positive_finite(self.max_secondary_area_px2, 'max_secondary_area_px2')
        positive_finite(self.max_tracking_distance_px, 'max_tracking_distance_px')
        positive_finite(self.contact_tolerance_px, 'contact_tolerance_px')
        if self.max_secondary_area_px2 <= self.min_secondary_area_px2:
            raise ValueError('Secondary area upper bound must exceed lower bound')
        if not 0 <= self.primary_threshold <= 255 or not 0 <= self.secondary_threshold <= 255:
            raise ValueError('Segmentation thresholds must be between 0 and 255')
        if self.maximum_missed_frames < 0 or self.min_velocity_samples < 3:
            raise ValueError('Tracker gap and velocity sample count are invalid')

    @classmethod
    def from_legacy_parameters(cls, params: dict) -> 'CombinedConfig':
        """Translate the existing GUI parameter names without changing their SI units."""
        return cls(
            acquisition_fps=float(params['fps_real']),
            mm_per_pixel=float(params['scale']),
            liquid=LiquidProperties(float(params['density']), float(params['viscosity']), float(params['tension'])),
            min_primary_area_px2=float(params.get('minimum_post_impact_area', 50)),
            primary_threshold=int(params.get('gray_thresh', 15)),
            secondary_threshold=int(params.get('spray_threshold', 120)),
            contact_tolerance_px=float(params.get('tolerance', 3)),
        )


@dataclass(frozen=True)
class SecondaryObservation:
    frame_index: int
    track_id: int
    center_x_px: float
    center_y_px: float
    equivalent_diameter_px: float
    region: str


@dataclass(frozen=True)
class CombinedFrameResult:
    frame_index: int
    acquisition_time_s: float
    contact_time_s: Optional[float] = None
    above_baseline_count: int = 0
    below_baseline_count: int = 0
    visible_secondary_count: int = 0
    cumulative_track_count: int = 0
    mean_secondary_diameter_px: Optional[float] = None
    spray_envelope_angle_deg: Optional[float] = None
    contact_width_mm: Optional[float] = None
    spreading_factor: Optional[float] = None
    height_mm: Optional[float] = None
    projected_area_mm2: Optional[float] = None
    contact_width_rate_mm_s: Optional[float] = None
    main_droplet_detected: bool = False
    first_contact_detected: bool = False
    status: str = 'not_measured'

    def with_time_origin(self, first_contact_index: Optional[int], fps: float):
        return replace(self, contact_time_s=(self.frame_index - first_contact_index) / fps
                       if first_contact_index is not None else None)


@dataclass(frozen=True)
class ImpactSummary:
    first_contact_frame: Optional[int]
    initial_diameter_mm: Optional[float]
    preimpact_velocity_m_s: Optional[float]
    reynolds: Optional[float]
    weber: Optional[float]
    ohnesorge: Optional[float]
    maximum_spreading_factor: Optional[float]
    maximum_spreading_frame: Optional[int]
    warnings: tuple[str, ...] = ()


def physical_summary(
    first_contact: Optional[int], diameter_mm: Optional[float],
    velocity_m_s: Optional[float], liquid: LiquidProperties,
    rows: list[CombinedFrameResult], warnings: tuple[str, ...] = (),
) -> ImpactSummary:
    valid_spreading = [(r.spreading_factor, r.frame_index) for r in rows
                       if r.spreading_factor is not None and math.isfinite(r.spreading_factor)]
    maximum = max(valid_spreading) if valid_spreading else None
    groups = None
    if diameter_mm is not None and velocity_m_s is not None:
        groups = dimensionless_numbers(velocity_m_s, diameter_mm / 1000.0, liquid)
    return ImpactSummary(
        first_contact, diameter_mm, velocity_m_s,
        groups.reynolds if groups else None,
        groups.weber if groups else None,
        groups.ohnesorge if groups else None,
        maximum[0] if maximum else None, maximum[1] if maximum else None,
        warnings,
    )
