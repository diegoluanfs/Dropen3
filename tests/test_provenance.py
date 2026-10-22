import json
from types import SimpleNamespace
from dropen3.system.provenance import write_export_provenance


def test_metadata_tracks_processing_parameters(tmp_path):
    mock = SimpleNamespace(current_mode="DROP", last_method_selected="DROP_FOURTH",
                           params={"fps_real": 10000, "scale": 0.01})
    target = tmp_path / "study.csv"
    out = write_export_provenance(target, mock, columns=["Time (s)", "Beta"], rows=12)
    result = json.loads(out.read_text())
    assert result["analysis_mode"] == "DROP"
    assert result["processing_parameters"]["fps_real"] == 10000
    assert result["row_count"] == 12
    assert result["research_validation_status"] == "NOT_QUANTITATIVELY_VALIDATED"
