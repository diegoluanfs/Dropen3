"""Composition root for the graphical application.

Each mixin groups one research workflow; cross-workflow commands access the
same application state through ``self``. The core provides shared initialization.
"""
import customtkinter as ctk
from dropen3.analysis.hysteresis import HysteresisAnalysisMixin
from dropen3.analysis.impact import ImpactAnalysisMixin
from dropen3.analysis.plotting import PlottingMixin
from dropen3.analysis.spray import SprayAnalysisMixin
from dropen3.analysis.static import StaticAnalysisMixin
from dropen3.analysis.video_tools import VideoToolsMixin
from dropen3.ui.core import ApplicationCore
from dropen3.ui.export import ExportMixin
from dropen3.ui.home import HomeMixin
from dropen3.ui.settings import SettingsMixin
from dropen3.ui.viewer import ViewerMixin


class Dropen3App(ApplicationCore, HomeMixin, SettingsMixin, ViewerMixin,
                 ExportMixin, StaticAnalysisMixin, HysteresisAnalysisMixin,
                 ImpactAnalysisMixin, SprayAnalysisMixin, PlottingMixin,
                 VideoToolsMixin, ctk.CTk):
    """Dropen3 analysis application with separated scientific workflows."""
