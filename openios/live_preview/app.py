"""Application runner for OpeniOS Live Preview Simulator."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, Gio, GLib

from openios.live_preview.window import SimulatorWindow

STYLE_CSS = Path(__file__).resolve().parent / "assets" / "style.css"


class OpenIOSApplication(Gtk.Application):
    """Main Gtk.Application instance managing the desktop lifecycle."""

    def __init__(
        self,
        initial_project: Optional[Path] = None,
        initial_zoom: float = 0.75,
        initial_device: Optional[str] = None,
    ) -> None:
        super().__init__(
            application_id="org.openios.livepreview",
            flags=Gio.ApplicationFlags.NON_UNIQUE,
        )
        self.initial_project = initial_project
        self.initial_zoom = initial_zoom
        self.initial_device = initial_device
        self.window: Optional[SimulatorWindow] = None

    def do_startup(self) -> None:
        Gtk.Application.do_startup(self)
        self._load_styles()

    def _load_styles(self) -> None:
        if STYLE_CSS.is_file():
            try:
                css_provider = Gtk.CssProvider()
                css_provider.load_from_path(str(STYLE_CSS))
                screen = Gdk.Screen.get_default()
                if screen:
                    Gtk.StyleContext.add_provider_for_screen(
                        screen,
                        css_provider,
                        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
                    )
            except Exception as e:
                print(f"[OpeniOS] Warning: failed to load CSS styles: {e}")

    def do_activate(self) -> None:
        if not self.window:
            self.window = SimulatorWindow(
                initial_project_path=self.initial_project,
                initial_zoom=self.initial_zoom,
                initial_device=self.initial_device,
            )
            self.add_window(self.window)
        self.window.show_all()
        self.window.present()
