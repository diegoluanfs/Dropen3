import json
from importlib.resources import files
from dropen3.__main__ import main
from dropen3.system.doctor import collect_diagnostics, render_text


def test_resource_embedded_in_package():
    assert files("dropen3.assets").joinpath("logo.png").read_bytes().startswith(b"\x89PNG")


def test_doctor_json_is_serializable():
    report = collect_diagnostics(check_display=False)
    assert report["application"] == "Dropen3"
    assert report["summary"]["PASS"] >= 1
    assert "OpenCV" in render_text(report)
    assert json.loads(json.dumps(report))["platform"] == report["platform"]


def test_doctor_command_can_emit_report(tmp_path):
    output = tmp_path / "diagnostics.json"
    code = main(["doctor", "--json", "--output", str(output)])
    report = json.loads(output.read_text(encoding="utf-8"))
    assert code == (1 if report["summary"]["FAIL"] else 0)
