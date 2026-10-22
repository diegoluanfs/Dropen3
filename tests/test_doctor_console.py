"""Regression tests for the standalone Doctor console lifetime."""
from __future__ import annotations

import io
import json

import pytest

from dropen3.system import doctor_cli


class FakeTerminal(io.StringIO):
    def isatty(self) -> bool:
        return True


class FakePipe(io.StringIO):
    def isatty(self) -> bool:
        return False


@pytest.mark.parametrize(
    ("frozen", "terminal", "json_mode", "no_pause", "force", "expected"),
    [
        (True, True, False, False, False, True),
        (True, False, False, False, False, False),
        (False, True, False, False, False, False),
        (False, True, False, False, True, True),
        (True, True, False, True, False, False),
        (True, True, True, False, False, False),
        (True, True, True, False, True, False),
    ],
)
def test_pause_policy(frozen, terminal, json_mode, no_pause, force, expected):
    stream = FakeTerminal() if terminal else FakePipe()
    assert doctor_cli.should_pause(
        frozen=frozen,
        input_stream=stream,
        machine_mode=json_mode,
        no_pause=no_pause,
        force_pause=force,
    ) is expected


def test_readline_keeps_window_visible_until_enter():
    stream = FakeTerminal("\n")
    output = io.StringIO()
    doctor_cli.wait_for_exit(input_stream=stream, output_stream=output)
    assert "Press Enter" in output.getvalue()
    assert stream.tell() == 1


def test_fatal_error_is_reported_and_still_pauses(monkeypatch, capsys):
    from dropen3.system import doctor

    def fail():
        raise RuntimeError("synthetic dependency failure")

    wait_calls = []
    monkeypatch.setattr(doctor, "collect_diagnostics", fail)
    monkeypatch.setattr(doctor_cli, "should_pause", lambda **kwargs: True)
    monkeypatch.setattr(doctor_cli, "wait_for_exit", lambda: wait_calls.append(True))
    assert doctor_cli.run_doctor() == 2
    assert wait_calls == [True]
    captured = capsys.readouterr()
    assert "FATAL ERROR" in captured.err
    assert "synthetic dependency failure" in captured.err


def test_json_mode_is_valid_and_never_pauses(monkeypatch, capsys):
    from dropen3.system import doctor

    monkeypatch.setattr(doctor, "collect_diagnostics", lambda: {
        "application": "Dropen3", "summary": {"PASS": 1, "WARN": 0, "FAIL": 0}, "checks": []
    })
    monkeypatch.setattr(doctor_cli, "should_pause", lambda **kwargs: False)
    monkeypatch.setattr(doctor_cli, "wait_for_exit", lambda: pytest.fail("Unexpected pause"))
    assert doctor_cli.run_doctor(as_json=True) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["application"] == "Dropen3"


def test_explicit_no_pause_with_report_write(monkeypatch, tmp_path):
    from dropen3.__main__ import main
    from dropen3.system import doctor

    monkeypatch.setattr(doctor, "collect_diagnostics", lambda: {
        "application": "Dropen3", "summary": {"PASS": 1, "WARN": 0, "FAIL": 0},
        "checks": [{"check": "Synthetic", "status": "PASS", "detail": "ok", "action": ""}],
    })
    saved = tmp_path / "status.txt"
    assert main(["doctor", "--no-pause", "--output", str(saved)]) == 0
    assert "Synthetic" in saved.read_text(encoding="utf-8")
