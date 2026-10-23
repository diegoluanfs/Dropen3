"""Generate transparent, machine-readable experiment provenance for exports."""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any
from dropen3 import __version__


def _safe(value: Any):
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (list, tuple)):
        return [_safe(x) for x in value]
    if isinstance(value, dict):
        return {str(k): _safe(v) for k, v in value.items()}
    return repr(value)


def export_provenance(app, *, data_columns=None, number_of_rows=None) -> dict[str, Any]:
    """Capture configuration known to the app; explicitly flag missing metadata."""
    video_path = getattr(app, 'video_path', None)
    video_source = None
    if video_path:
        path = Path(video_path)
        try:
            stat = path.stat()
            video_source = {'file_name': path.name, 'size_bytes': stat.st_size,
                            'modified_utc': datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()}
            # Large videos require explicit offline checksums to avoid freezing the GUI.
            if stat.st_size <= 64 * 1024 * 1024:
                digest = hashlib.sha256()
                with path.open('rb') as input_file:
                    for chunk in iter(lambda: input_file.read(1024 * 1024), b''):
                        digest.update(chunk)
                video_source['sha256'] = digest.hexdigest()
            else:
                video_source['sha256'] = None
                video_source['sha256_note'] = 'Not computed automatically for files above 64 MiB'
        except OSError as error:
            video_source = {'file_name': path.name, 'metadata_error': str(error)}
    fields = ['threshold_hysteresis', 'threshold_impact', 'tangent_static',
              'tangent_static_pol', 'tangent_static_baseline_points',
              'min_points_fit', 'n_tangent_points_val', 'points_baseline',
              'limit_y_baseline', 'm_baseline', 'c_baseline']
    settings = {key: _safe(getattr(app, key)) for key in fields if hasattr(app, key)}
    combined = getattr(app, 'combined_session', None)
    combined_summary = getattr(app, 'combined_summary', None)
    return {
        'schema_version': 1,
        'application': 'Dropen3',
        'application_version': __version__,
        'exported_utc': datetime.now(timezone.utc).isoformat(),
        'analysis_mode': _safe(getattr(app, 'current_mode', None)),
        'analysis_method': _safe(getattr(app, 'last_method_selected', None)),
        'processing_parameters': _safe(getattr(app, 'params', None)),
        'settings': settings,
        'data_columns': _safe(data_columns),
        'row_count': number_of_rows,
        'input_media': video_source,
        'combined_analysis': (
            {'reference_frame_index': combined.reference_frame_index,
             'first_contact_frame': combined.first_contact_frame,
             'selected_baseline_frame': getattr(app, 'combined_selected_baseline_frame', None),
             'impact_summary_available': combined_summary is not None}
            if combined is not None else None
        ),
        'research_validation_status': 'NOT_QUANTITATIVELY_VALIDATED',
        'limitations': [
            'Frame timestamps and spatial calibration require external verification',
            'Projected silhouette width may differ from substrate contact width',
            'Advancing and receding angles require a defined experimental protocol',
        ],
    }


def write_export_provenance(destination: str | Path, app, *, columns=None, rows=None) -> Path:
    destination = Path(destination)
    sidecar = destination.with_name(destination.name + '.metadata.json')
    document = export_provenance(app, data_columns=columns, number_of_rows=rows)
    sidecar.write_text(json.dumps(document, indent=2, ensure_ascii=True, allow_nan=False) + '\n', encoding='utf-8')
    return sidecar
