"""GUI-controller state regression without a graphical display or camera hardware."""
from __future__ import annotations
from dropen3.analysis.combined import CombinedAnalysisMixin


class FakeCapture:
    def __init__(self):
        self.released = False

    def release(self):
        self.released = True


class FakeLabel:
    def __init__(self):
        self.message = None

    def configure(self, *, text):
        self.message = text


class FakeApplication(CombinedAnalysisMixin):
    def __init__(self):
        self.current_mode = 'SPRAY_IMPACT'
        self.analysis_active = True
        self.vel_active = True
        self.cap_vel = FakeCapture()
        self.combined_after_id = None
        self.combined_session = object()
        self.combined_summary = None
        self.lbl_status = FakeLabel()
        self.callbacks = {}
        self.cancelled = []

    def after(self, milliseconds, callback):
        key = len(self.callbacks) + 1
        self.callbacks[key] = callback
        return key

    def after_cancel(self, key):
        self.cancelled.append(key)
        self.callbacks.pop(key, None)


def test_no_duplicate_frame_callback():
    app = FakeApplication()
    app._schedule_combined_next()
    first = app.combined_after_id
    app._schedule_combined_next()
    assert first == app.combined_after_id
    assert len(app.callbacks) == 1


def test_pause_prevents_scheduling_and_preserves_capture():
    app = FakeApplication()
    app._schedule_combined_next()
    callback = app.combined_after_id
    app.pause_combined_analysis()
    assert callback in app.cancelled
    assert app.combined_after_id is None
    assert not app.analysis_active
    assert not app.cap_vel.released
    app._schedule_combined_next()
    assert not app.callbacks


def test_resume_from_pause_schedules_once():
    app = FakeApplication()
    app.pause_combined_analysis()
    app.resume_combined_analysis()
    assert app.analysis_active and app.vel_active
    assert len(app.callbacks) == 1


def test_stop_releases_capture_and_cancels_callback():
    app = FakeApplication()
    app._schedule_combined_next()
    app.stop_combined_analysis()
    assert app.cap_vel is None
    assert not app.analysis_active
    assert len(app.callbacks) == 0
    assert app.cancelled == [1]


def test_resume_without_session_does_nothing():
    app = FakeApplication()
    app.combined_session = None
    app.pause_combined_analysis()
    app.resume_combined_analysis()
    assert not app.analysis_active
    assert not app.callbacks


def test_completed_session_is_not_resumed_automatically():
    app = FakeApplication()
    app.combined_summary = object()
    app.restart_combined_analysis = lambda: setattr(app, 'restarted', True)
    app.resume_combined_analysis()
    assert app.restarted


def test_no_steps_are_run_after_pause():
    app = FakeApplication()
    app.pause_combined_analysis()
    app._combined_frame_step()
    assert app.combined_after_id is None


def test_finish_without_session_does_not_crash():
    app = FakeApplication()
    app.combined_session = None
    assert app.finish_combined_analysis() is None


def test_combined_step_finishes_at_end_of_recording():
    import cv2
    import numpy as np
    from dropen3.science.combined import Baseline, CombinedConfig
    from dropen3.science.metrics import LiquidProperties
    from dropen3.analysis.combined_core import CombinedSession

    base = np.full((120, 180, 3), 255, dtype=np.uint8)
    video = []
    for y in (25, 40, 60, 78):
        image = base.copy()
        cv2.circle(image, (70, y), 12, (0, 0, 0), -1)
        video.append(image)

    class FakeVideo(FakeCapture):
        def __init__(self, images):
            super().__init__()
            self.images = list(images)
            self.position = 0

        def isOpened(self):
            return not self.released

        def read(self):
            if self.position >= len(self.images):
                return False, None
            image = self.images[self.position].copy()
            self.position += 1
            return True, image

    class FakeTree:
        def __init__(self):
            self.rows = []

        def insert(self, parent, position, values):
            self.rows.append(values)

    class FakeProgress:
        def __init__(self):
            self.value = None

        def set(self, value):
            self.value = value

    app = FakeApplication()
    app.cap_vel = FakeVideo(video)
    app.combined_session = CombinedSession(
        CombinedConfig(1000, 0.01, LiquidProperties(1000, .001, .072),
                       min_primary_area_px2=20, primary_threshold=10),
        Baseline((0, 90), (179, 90)), base, 0,
    )
    app.combined_frame_index = 0
    app.combined_total_frames = len(video)
    app.tree = FakeTree()
    app.combined_progress_bar = FakeProgress()
    app._configure_combined_columns = lambda clear=True: app.tree.rows.clear() if clear else None
    app._set_combined_progress = lambda value: app.combined_progress_bar.set(value)
    app.display_frame = lambda image, update_original: None
    for _ in video:
        app._combined_frame_step()
        assert app.combined_frame_index <= app.combined_total_frames
    app._combined_frame_step()  # Exhausting capture calls finalize.
    assert app.combined_summary is not None
    assert app.combined_summary.first_contact_frame == 3
    assert len(app.tree.rows) == len(video)
    assert app.combined_progress_bar.value == 1
    assert app.cap_vel is None
    assert not app.analysis_active


def _load_home_module(monkeypatch):
    import importlib.util
    import sys
    import types
    from pathlib import Path
    monkeypatch.setitem(sys.modules, 'customtkinter', types.ModuleType('customtkinter'))
    source = Path(__file__).parents[1] / 'src' / 'dropen3' / 'ui' / 'home.py'
    spec = importlib.util.spec_from_file_location('test_combined_home_module', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.HomeMixin


def test_switching_mode_releases_active_combined_reader(monkeypatch):
    HomeMixin = _load_home_module(monkeypatch)
    # A mode transition must release old callbacks and the video handle.
    class ModeTransition(HomeMixin, FakeApplication):
        pass
    changing = ModeTransition()
    changing._schedule_combined_next()
    # Intercept GUI construction after session cleanup.
    class Sentinel(Exception):
        pass

    class FakeContainer:
        def winfo_children(self):
            raise Sentinel()

    changing.menu_container = FakeContainer()
    import pytest
    with pytest.raises(Sentinel):
        changing.show_sub_menu('WCA')
    assert changing.cap_vel is None
    assert changing.combined_session is None
    assert changing.combined_after_id is None
    assert changing.current_mode == 'WCA'


def test_switching_to_same_mode_preserves_combined_analysis(monkeypatch):
    HomeMixin = _load_home_module(monkeypatch)
    class ModeTransition(HomeMixin, FakeApplication):
        pass
    app = ModeTransition()
    app._schedule_combined_next()
    class Sentinel(Exception):
        pass
    class FakeContainer:
        def winfo_children(self):
            raise Sentinel()
    app.menu_container = FakeContainer()
    import pytest
    with pytest.raises(Sentinel):
        app.show_sub_menu('SPRAY_IMPACT')
    assert app.cap_vel is not None
    assert app.combined_session is not None
    assert len(app.callbacks) == 1
