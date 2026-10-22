"""Test global keyboard navigation without depending on a display server."""
import importlib.util
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def core_module(monkeypatch):
    ctk = types.ModuleType('customtkinter')
    gui = types.ModuleType('dropen3.system.gui')
    gui.show_doctor = lambda _: None
    widgets = types.ModuleType('dropen3.ui.widgets')
    widgets.Tooltip = lambda *args: None
    monkeypatch.setitem(sys.modules, 'customtkinter', ctk)
    monkeypatch.setitem(sys.modules, 'dropen3.system.gui', gui)
    monkeypatch.setitem(sys.modules, 'dropen3.ui.widgets', widgets)
    location = Path(__file__).parents[1] / 'src' / 'dropen3' / 'ui' / 'core.py'
    spec = importlib.util.spec_from_file_location('dropen3_test_core', location)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_navigation_shortcuts_are_installed(core_module):
    keys = []
    app = SimpleNamespace(bind_all=lambda key, callback: keys.append(key), on_frame_key=lambda _: None)
    core_module.ApplicationCore.install_navigation_shortcuts(app)
    assert len(keys) == 6
    assert '<Left>' in keys and '<Right>' in keys
    assert '<KeyPress-a>' in keys and '<KeyPress-d>' in keys


@pytest.mark.parametrize('key,direction', [('Left', 'prev'), ('a', 'prev'),
                                           ('Right', 'next'), ('D', 'next')])
def test_keyboard_moves_one_frame(core_module, key, direction):
    calls = []
    class FakeCapture:
        def isOpened(self):
            return True
    app = SimpleNamespace(cap=FakeCapture(),
                          stop_video=lambda: calls.append('stop'),
                          prev_frame=lambda: calls.append('prev'),
                          next_frame=lambda: calls.append('next'))
    class Widget:
        def winfo_toplevel(self):
            return app
        def winfo_class(self):
            return 'CTkFrame'
    result = core_module.ApplicationCore.on_frame_key(app, SimpleNamespace(widget=Widget(), keysym=key))
    assert result == 'break'
    assert calls == ['stop', direction]


def test_navigation_skips_text_entry(core_module):
    calls = []
    app = SimpleNamespace(cap=SimpleNamespace(isOpened=lambda: True),
                          stop_video=lambda: calls.append('stop'),
                          prev_frame=lambda: calls.append('prev'))
    class Widget:
        def winfo_toplevel(self):
            return app
        def winfo_class(self):
            return 'CTkEntry'
    result = core_module.ApplicationCore.on_frame_key(app, SimpleNamespace(widget=Widget(), keysym='a'))
    assert result is None and not calls
