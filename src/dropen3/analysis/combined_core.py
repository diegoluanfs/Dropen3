"""Headless, deterministic processing for exploratory spray/impact analysis.

No annotated frame is ever used as an input to segmentation. A detected track
is an image association, not proof of a physically unique secondary droplet.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import math
import cv2
import numpy as np

from dropen3.science.combined import (Baseline, CombinedConfig, CombinedFrameResult,
                                     SecondaryObservation, physical_summary)


@dataclass(frozen=True)
class Detection:
    x: float
    y: float
    diameter_px: float
    region: str


class SimpleTracker:
    """Deterministic one-to-one association with bounded missed detections."""

    def __init__(self, max_distance_px: float, maximum_missed_frames: int = 2):
        self.max_distance_px = max_distance_px
        self.maximum_missed_frames = maximum_missed_frames
        self.tracks: dict[int, tuple[float, float, int]] = {}
        self.next_id = 1
        self.total_assigned_ids = 0

    def update(self, detections: list[Detection], frame_index: int) -> list[tuple[int, Detection]]:
        available = [(identity, xyz) for identity, xyz in self.tracks.items()
                     if 0 < frame_index - xyz[2] <= self.maximum_missed_frames + 1]
        candidates = []
        for j, detection in enumerate(detections):
            for identity, (x, y, _) in available:
                distance = math.hypot(detection.x - x, detection.y - y)
                if distance <= self.max_distance_px:
                    candidates.append((distance, identity, j))
        candidates.sort()
        matched_ids, matched_indices = set(), set()
        assigned: dict[int, int] = {}
        for _, identity, index in candidates:
            if identity not in matched_ids and index not in matched_indices:
                matched_ids.add(identity)
                matched_indices.add(index)
                assigned[index] = identity
        for j in range(len(detections)):
            if j not in assigned:
                assigned[j] = self.next_id
                self.next_id += 1
                self.total_assigned_ids += 1
        result = []
        for j, detection in enumerate(detections):
            identity = assigned[j]
            self.tracks[identity] = (detection.x, detection.y, frame_index)
            result.append((identity, detection))
        self.tracks = {identity: state for identity, state in self.tracks.items()
                       if frame_index - state[2] <= self.maximum_missed_frames}
        return result


def segment_masks(frame_bgr: np.ndarray, background_gray: np.ndarray, config: CombinedConfig,
                  baseline: Baseline) -> tuple[np.ndarray, np.ndarray]:
    if frame_bgr is None or frame_bgr.ndim != 3 or frame_bgr.shape[2] != 3:
        raise ValueError('A BGR video frame is required')
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    if background_gray.shape != gray.shape:
        raise ValueError('Reference background and video frame dimensions must match')
    delta = cv2.absdiff(gray, background_gray)
    # The primary contour is based on actual movement relative to the reference.
    _, primary = cv2.threshold(cv2.GaussianBlur(delta, (5, 5), 0),
                               config.primary_threshold, 255, cv2.THRESH_BINARY)
    _, secondary = cv2.threshold(cv2.GaussianBlur(delta, (3, 3), 0),
                                 config.secondary_threshold, 255, cv2.THRESH_BINARY)
    primary = cv2.morphologyEx(primary, cv2.MORPH_CLOSE,
                              cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
    # Remove pixels below the baseline in the primary-drop mask, including on inclined surfaces.
    h, w = primary.shape
    yy = np.arange(h)[:, None]
    xx = np.arange(w)[None, :]
    primary[yy > (baseline.p1[1] + baseline.slope * (xx - baseline.p1[0])) + config.contact_tolerance_px] = 0
    return primary, secondary


def secondary_detections(mask: np.ndarray, baseline: Baseline, config: CombinedConfig,
                         excluded_contour: np.ndarray | None = None) -> list[Detection]:
    contours, _ = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    detections = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if not config.min_secondary_area_px2 <= area <= config.max_secondary_area_px2:
            continue
        moments = cv2.moments(contour)
        if moments['m00'] == 0:
            continue
        x, y = moments['m10'] / moments['m00'], moments['m01'] / moments['m00']
        if excluded_contour is not None and cv2.pointPolygonTest(excluded_contour, (x, y), False) >= 0:
            continue
        region = 'below' if baseline.signed_distance_px(x, y) >= 0 else 'above'
        detections.append(Detection(x, y, 2 * math.sqrt(area / math.pi), region))
    return sorted(detections, key=lambda det: (det.y, det.x))


def spray_envelope_angle(detections: list[Detection], baseline: Baseline) -> float | None:
    """Exploratory 2D envelope: angle between extreme rays below the baseline.

    This is a planar silhouette descriptor, NOT a verified physical cone angle.
    The chosen vertex is the mean x-coordinate of all detections below baseline.
    """
    lower = [det for det in detections if det.region == 'below']
    if len(lower) < 2:
        return None
    vertex_x = sum(det.x for det in lower) / len(lower)
    vertex_y = baseline.y_at(vertex_x)
    angles = [math.degrees(math.atan2(det.y - vertex_y, det.x - vertex_x))
              for det in lower if det.y > baseline.y_at(det.x)]
    if len(angles) < 2:
        return None
    angle = max(angles) - min(angles)
    return angle if 0 < angle <= 180 else None


def select_primary_contour(mask: np.ndarray, minimum_area: float,
                           previous_center: tuple[float, float] | None = None) -> np.ndarray | None:
    contours, _ = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidates = [cnt for cnt in contours if cv2.contourArea(cnt) >= minimum_area]
    if not candidates:
        return None
    # Largest consistent object is more reliable than image-center selection.
    candidates.sort(key=cv2.contourArea, reverse=True)
    if previous_center is None:
        return candidates[0]
    largest_area = cv2.contourArea(candidates[0])
    plausible = [c for c in candidates if cv2.contourArea(c) >= 0.35 * largest_area]
    def distance(contour):
        moment = cv2.moments(contour)
        if moment['m00'] <= 0:
            return float('inf')
        return math.hypot(moment['m10'] / moment['m00'] - previous_center[0],
                          moment['m01'] / moment['m00'] - previous_center[1])
    return min(plausible, key=distance)


def primary_geometry(contour: np.ndarray, baseline: Baseline, config: CombinedConfig,
                     *, after_contact: bool) -> tuple[float | None, float | None, float | None]:
    """Contact width, height, projected silhouette area, all in physical units.

    Invalid contact-point segmentation is missing (None), never a physical zero.
    """
    if contour is None:
        return None, None, None
    pts = contour.reshape((-1, 2)).astype(float)
    projected_area = cv2.contourArea(contour) * config.mm_per_pixel ** 2
    top_distances = np.array([baseline.signed_distance_px(x, y) for x, y in pts])
    height = max(0.0, -float(np.min(top_distances))) * config.mm_per_pixel
    if not after_contact:
        return None, height, projected_area
    contacts = pts[np.abs(top_distances) <= config.contact_tolerance_px]
    if len(contacts) < 2:
        return None, height, projected_area
    width = baseline.length_px(float(np.min(contacts[:, 0])), float(np.max(contacts[:, 0])))
    if width <= 0:
        return None, height, projected_area
    return width * config.mm_per_pixel, height, projected_area


class CombinedSession:
    """One deterministic pass through ordered frames, with explicit missing values."""

    def __init__(self, config: CombinedConfig, baseline: Baseline, reference: np.ndarray,
                 reference_frame_index: int):
        if reference is None or reference.ndim not in (2, 3):
            raise ValueError('A reference image is required')
        if reference_frame_index < 0:
            raise ValueError('Reference frame index cannot be negative')
        self.config = config
        self.baseline = baseline
        self.reference_gray = cv2.cvtColor(reference, cv2.COLOR_BGR2GRAY) if reference.ndim == 3 else reference.copy()
        self.reference_frame_index = reference_frame_index
        self.tracker = SimpleTracker(config.max_tracking_distance_px, config.maximum_missed_frames)
        self.rows: list[CombinedFrameResult] = []
        self.observations: list[SecondaryObservation] = []
        self.first_contact_frame: int | None = None
        self.preimpact_diameters_mm: list[float] = []
        self.preimpact_positions: list[tuple[int, float]] = []
        self.initial_diameter_mm: float | None = None
        self.velocity_m_s: float | None = None
        self.previous_primary_center: tuple[float, float] | None = None
        self.last_contact_width: tuple[int, float] | None = None
        self.last_frame_index = -1
        self.warnings: list[str] = ['Spray envelope and segmentation require experimental validation.']

    def process(self, frame: np.ndarray, frame_index: int) -> tuple[CombinedFrameResult, np.ndarray]:
        if frame_index <= self.last_frame_index:
            raise ValueError('Original video frame indices must be strictly increasing')
        self.last_frame_index = frame_index
        primary_mask, secondary_mask = segment_masks(frame, self.reference_gray, self.config, self.baseline)
        primary = select_primary_contour(primary_mask, self.config.min_primary_area_px2, self.previous_primary_center)
        center = None
        if primary is not None:
            moment = cv2.moments(primary)
            if moment['m00'] > 0:
                center = (moment['m10'] / moment['m00'], moment['m01'] / moment['m00'])
                self.previous_primary_center = center
        detections = secondary_detections(secondary_mask, self.baseline, self.config, primary)
        tracked = self.tracker.update(detections, frame_index)
        for identity, det in tracked:
            self.observations.append(SecondaryObservation(frame_index, identity, det.x, det.y,
                                                          det.diameter_px, det.region))
        visible_above = sum(det.region == 'above' for _, det in tracked)
        visible_below = sum(det.region == 'below' for _, det in tracked)
        spray_angle = spray_envelope_angle(detections, self.baseline)
        diameter = None
        contact = False
        if primary is not None:
            pts = primary.reshape(-1, 2).astype(float)
            bottom_distance = max(self.baseline.signed_distance_px(x, y) for x, y in pts)
            contact = bottom_distance >= -self.config.contact_tolerance_px
            if self.first_contact_frame is None and contact:
                self.first_contact_frame = frame_index
                if self.preimpact_diameters_mm:
                    self.initial_diameter_mm = float(np.median(self.preimpact_diameters_mm))
                if len(self.preimpact_positions) >= self.config.min_velocity_samples:
                    positions = self.preimpact_positions
                    times = np.array([i / self.config.acquisition_fps for i, _ in positions])
                    ys = np.array([y for _, y in positions])
                    if np.unique(times).size >= self.config.min_velocity_samples:
                        t = times - times.mean()
                        slope = float(np.dot(t, ys - ys.mean()) / np.dot(t, t))
                        self.velocity_m_s = abs(slope) * self.config.mm_per_pixel / 1000
                if self.initial_diameter_mm is None:
                    self.warnings.append('Pre-impact diameter unavailable: insufficient valid frames.')
                if self.velocity_m_s is None:
                    self.warnings.append('Pre-impact velocity unavailable: insufficient valid frames.')
            if self.first_contact_frame is None:
                # Equivalent ellipse diameter as described in collaborator code; label as proxy.
                if len(primary) >= 5:
                    ellipse = cv2.fitEllipse(primary)
                    diameter = 0.5 * (ellipse[1][0] + ellipse[1][1]) * self.config.mm_per_pixel
                    if math.isfinite(diameter) and diameter > 0:
                        self.preimpact_diameters_mm.append(diameter)
                if center is not None:
                    # Track motion normal to the selected substrate, also for inclined baselines.
                    self.preimpact_positions.append(
                        (frame_index, self.baseline.signed_distance_px(*center))
                    )
        width_mm, height_mm, area_mm2 = primary_geometry(
            primary, self.baseline, self.config, after_contact=self.first_contact_frame is not None
        )
        beta = width_mm / self.initial_diameter_mm if (width_mm is not None and self.initial_diameter_mm) else None
        rate = None
        if width_mm is not None:
            if self.last_contact_width is not None:
                prev_frame, prev_width = self.last_contact_width
                delta_t = (frame_index - prev_frame) / self.config.acquisition_fps
                if delta_t > 0:
                    rate = (width_mm - prev_width) / delta_t
            self.last_contact_width = (frame_index, width_mm)
        status = ('no_primary_contour' if primary is None else
                  'pre_contact' if self.first_contact_frame is None else
                  'contact_width_missing' if width_mm is None else 'measured')
        row = CombinedFrameResult(
            frame_index=frame_index,
            acquisition_time_s=frame_index / self.config.acquisition_fps,
            contact_time_s=(frame_index - self.first_contact_frame) / self.config.acquisition_fps
            if self.first_contact_frame is not None else None,
            above_baseline_count=visible_above, below_baseline_count=visible_below,
            visible_secondary_count=len(tracked), cumulative_track_count=self.tracker.total_assigned_ids,
            mean_secondary_diameter_px=float(np.mean([det.diameter_px for _, det in tracked])) if tracked else None,
            spray_envelope_angle_deg=spray_angle, contact_width_mm=width_mm,
            spreading_factor=beta, height_mm=height_mm, projected_area_mm2=area_mm2,
            contact_width_rate_mm_s=rate, main_droplet_detected=primary is not None,
            first_contact_detected=frame_index == self.first_contact_frame, status=status)
        self.rows.append(row)
        overlay = frame.copy()
        h, w = overlay.shape[:2]
        cv2.line(overlay, (0, round(self.baseline.y_at(0))),
                 (w - 1, round(self.baseline.y_at(w - 1))), (0, 255, 255), 1)
        if primary is not None:
            cv2.drawContours(overlay, [primary], -1, (0, 220, 50), 1)
        for identity, det in tracked:
            cv2.circle(overlay, (round(det.x), round(det.y)), 3, (255, 0, 200), 1)
            cv2.putText(overlay, str(identity), (round(det.x) + 4, round(det.y)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 0, 200), 1)
        return row, overlay

    def finalize(self):
        """Rebase every row to first contact; preserve original acquisition indices."""
        self.rows = [row.with_time_origin(self.first_contact_frame, self.config.acquisition_fps)
                     for row in self.rows]
        return self.rows, physical_summary(
            self.first_contact_frame, self.initial_diameter_mm, self.velocity_m_s,
            self.config.liquid, self.rows, tuple(self.warnings)
        )
