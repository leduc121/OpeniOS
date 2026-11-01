"""Sleek native desktop simulator toolbar."""

from __future__ import annotations

from typing import Callable, Optional

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from openios.live_preview.core.models import BackendType, Orientation, ServerState
from openios.live_preview.devices.registry import device_registry


class SimulatorToolbar(Gtk.HeaderBar):
    """Modern headerbar toolbar providing simulator controls."""

    def __init__(
        self,
        on_open_project: Callable[[], None],
        on_toggle_run: Callable[[], None],
        on_reload: Callable[[], None],
        on_toggle_orientation: Callable[[], None],
        on_device_changed: Callable[[str], None],
        on_zoom_changed: Callable[[float], None],
        on_backend_changed: Callable[[BackendType], None],
        on_toggle_logs: Callable[[], None],
    ) -> None:
        super().__init__()
        self.set_show_close_button(True)
        self.set_title("OpeniOS Simulator")
        self.set_subtitle("iPhone 14 Pro Max · Live Preview")

        self._on_open_project = on_open_project
        self._on_toggle_run = on_toggle_run
        self._on_reload = on_reload
        self._on_toggle_orientation = on_toggle_orientation
        self._on_device_changed = on_device_changed
        self._on_zoom_changed = on_zoom_changed
        self._on_backend_changed = on_backend_changed
        self._on_toggle_logs = on_toggle_logs

        self._build_ui()

    def _build_ui(self) -> None:
        # Left side: Project actions
        self.btn_open = Gtk.Button(label="📁 Open Project")
        self.btn_open.set_tooltip_text("Select local project directory (React/Vite, Expo, Flutter, Static)")
        self.btn_open.connect("clicked", lambda b: self._on_open_project())
        self.pack_start(self.btn_open)

        # Run / Stop toggle button
        self.btn_run = Gtk.Button(label="▶ Run")
        self.btn_run.get_style_context().add_class("suggested-action")
        self.btn_run.set_tooltip_text("Start project dev server")
        self.btn_run.connect("clicked", lambda b: self._on_toggle_run())
        self.pack_start(self.btn_run)

        # Reload button
        self.btn_reload = Gtk.Button(label="🔄 Reload")
        self.btn_reload.set_tooltip_text("Reload webview contents")
        self.btn_reload.connect("clicked", lambda b: self._on_reload())
        self.pack_start(self.btn_reload)

        # Right side: Device & View controls

        # Backend selector dropdown
        self.combo_backend = Gtk.ComboBoxText()
        self.combo_backend.append(BackendType.LIVE_PREVIEW.value, "🌐 Live Preview")
        self.combo_backend.append(BackendType.NATIVE_EMULATOR.value, "⚙ QEMU Native")
        self.combo_backend.set_active_id(BackendType.LIVE_PREVIEW.value)
        self.combo_backend.set_tooltip_text("Switch between Web Live Preview and QEMU-SPTM Native Emulator")
        self.combo_backend.connect("changed", self._on_backend_combo_changed)
        self.pack_end(self.combo_backend)

        # Logs toggle
        self.btn_logs = Gtk.Button(label="📋 Logs")
        self.btn_logs.set_tooltip_text("Toggle dev-server output log drawer")
        self.btn_logs.connect("clicked", lambda b: self._on_toggle_logs())
        self.pack_end(self.btn_logs)

        # Rotate orientation
        self.btn_rotate = Gtk.Button(label="↻ Rotate")
        self.btn_rotate.set_tooltip_text("Switch Portrait / Landscape")
        self.btn_rotate.connect("clicked", lambda b: self._on_toggle_orientation())
        self.pack_end(self.btn_rotate)

        # Zoom level selector
        self.combo_zoom = Gtk.ComboBoxText()
        self.combo_zoom.append("0.5", "50%")
        self.combo_zoom.append("0.75", "75%")
        self.combo_zoom.append("0.85", "85%")
        self.combo_zoom.append("1.0", "100%")
        self.combo_zoom.set_active_id("0.85")
        self.combo_zoom.set_tooltip_text("Window viewport scale factor")
        self.combo_zoom.connect("changed", self._on_zoom_combo_changed)
        self.pack_end(self.combo_zoom)

        # Device model selector
        self.combo_device = Gtk.ComboBoxText()
        for profile in device_registry.all_profiles():
            self.combo_device.append(profile.id, profile.name)
        self.combo_device.set_active_id("iphone-14-pro-max")
        self.combo_device.set_tooltip_text("Select iPhone model preset")
        self.combo_device.connect("changed", self._on_device_combo_changed)
        self.pack_end(self.combo_device)

    def _on_device_combo_changed(self, combo: Gtk.ComboBoxText) -> None:
        device_id = combo.get_active_id()
        if device_id:
            profile = device_registry.get(device_id)
            if profile:
                self.set_subtitle(f"{profile.name} · Live Preview")
            self._on_device_changed(device_id)

    def _on_zoom_combo_changed(self, combo: Gtk.ComboBoxText) -> None:
        val = combo.get_active_id()
        if val:
            try:
                self._on_zoom_changed(float(val))
            except ValueError:
                pass

    def _on_backend_combo_changed(self, combo: Gtk.ComboBoxText) -> None:
        val = combo.get_active_id()
        if val:
            self._on_backend_changed(BackendType(val))

    def update_server_state(self, state: ServerState, project_name: Optional[str] = None) -> None:
        if state == ServerState.READY:
            self.btn_run.set_label("⏹ Stop")
            self.btn_run.get_style_context().remove_class("suggested-action")
            self.btn_run.get_style_context().add_class("destructive-action")
            if project_name:
                self.set_subtitle(f"{project_name} · Connected (Live)")
        elif state == ServerState.STARTING:
            self.btn_run.set_label("⏳ Starting...")
            self.btn_run.set_sensitive(False)
        else:
            self.btn_run.set_label("▶ Run")
            self.btn_run.set_sensitive(True)
            self.btn_run.get_style_context().remove_class("destructive-action")
            self.btn_run.get_style_context().add_class("suggested-action")
            if project_name:
                self.set_subtitle(f"{project_name} · Stopped")
