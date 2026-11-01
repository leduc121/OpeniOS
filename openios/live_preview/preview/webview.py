"""Embedded WebKit browser view configured for realistic iPhone emulation."""

from __future__ import annotations

import os
from typing import Callable, Optional

# Ensure GTK and WebKit versions are required before importing repository
import gi
try:
    gi.require_version("Gtk", "3.0")
    gi.require_version("WebKit2", "4.1")
    from gi.repository import Gtk, Gdk, WebKit2, GLib
except Exception as e:
    raise RuntimeError(f"Failed to load GTK3 / WebKit2 GObject bindings: {e}")

from openios.live_preview.core.models import DeviceProfile, Orientation

IPHONE_USER_AGENT = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1"
)


class SimulatorWebView:
    """Manages an embedded WebKit2 WebView with iPhone mobile profile and viewport emulation."""

    def __init__(
        self,
        device: DeviceProfile,
        orientation: Orientation = Orientation.PORTRAIT,
        zoom_level: float = 1.0,
        on_title_changed: Optional[Callable[[str], None]] = None,
        on_load_finished: Optional[Callable[[str], None]] = None,
        on_load_failed: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.device = device
        self.orientation = orientation
        self.zoom_level = zoom_level
        self._on_title_changed = on_title_changed
        self._on_load_finished = on_load_finished
        self._on_load_failed = on_load_failed
        self._current_url: Optional[str] = None

        self.user_content_mgr = WebKit2.UserContentManager()
        self.view = WebKit2.WebView.new_with_user_content_manager(self.user_content_mgr)

        self._configure_settings()
        self._inject_mobile_emulation()
        self._connect_signals()

    @property
    def widget(self) -> Gtk.Widget:
        return self.view

    def _configure_settings(self) -> None:
        settings = self.view.get_settings()
        settings.set_user_agent(IPHONE_USER_AGENT)
        settings.set_enable_javascript(True)
        settings.set_enable_developer_extras(True)
        settings.set_enable_webgl(True)
        settings.set_javascript_can_open_windows_automatically(True)
        settings.set_enable_smooth_scrolling(True)
        settings.set_allow_file_access_from_file_urls(False)
        settings.set_allow_universal_access_from_file_urls(False)
        self.view.set_background_color(Gdk.RGBA(0, 0, 0, 0))
        self.view.set_zoom_level(self.zoom_level)

    def _inject_mobile_emulation(self) -> None:
        """Inject CSS safe-area variables and mobile viewport reset into all loaded pages."""
        self.user_content_mgr.remove_all_style_sheets()
        safe_area = self.device.get_safe_area(self.orientation)

        css_rules = f"""
        :root {{
            --openios-safe-area-top: {safe_area.top}px;
            --openios-safe-area-bottom: {safe_area.bottom}px;
            --openios-safe-area-left: {safe_area.left}px;
            --openios-safe-area-right: {safe_area.right}px;
            /* iOS standard environment variable fallbacks */
            --sat: {safe_area.top}px;
            --sab: {safe_area.bottom}px;
            --sal: {safe_area.left}px;
            --sar: {safe_area.right}px;
        }}
        /* Prevent desktop horizontal overscroll bounce while preserving vertical scroll */
        html, body {{
            -webkit-tap-highlight-color: transparent;
            touch-action: pan-x pan-y;
        }}
        """

        style_sheet = WebKit2.UserStyleSheet(
            css_rules,
            WebKit2.UserContentInjectedFrames.ALL_FRAMES,
            WebKit2.UserStyleLevel.USER,
            None,
            None,
        )
        self.user_content_mgr.add_style_sheet(style_sheet)

    def _connect_signals(self) -> None:
        self.view.connect("load-changed", self._on_view_load_changed)
        self.view.connect("load-failed", self._on_view_load_failed)
        self.view.connect("notify::title", self._on_view_notify_title)

    def _on_view_load_changed(self, view: WebKit2.WebView, event: WebKit2.LoadEvent) -> None:
        if event == WebKit2.LoadEvent.FINISHED:
            uri = view.get_uri() or ""
            self._current_url = uri
            if self._on_load_finished:
                self._on_load_finished(uri)

    def _on_view_load_failed(
        self,
        view: WebKit2.WebView,
        event: WebKit2.LoadEvent,
        failing_uri: str,
        error: GLib.Error,
    ) -> bool:
        if self._on_load_failed:
            self._on_load_failed(failing_uri)
        return False

    def _on_view_notify_title(self, view: WebKit2.WebView, param_spec: object) -> None:
        title = view.get_title()
        if title and self._on_title_changed:
            self._on_title_changed(title)

    def load_uri(self, uri: str) -> None:
        self._current_url = uri
        self.view.load_uri(uri)

    def load_html(self, html: str, base_uri: str = "http://localhost") -> None:
        self.view.load_html(html, base_uri)

    def reload(self) -> None:
        self.view.reload()

    def set_zoom(self, zoom: float) -> None:
        self.zoom_level = max(0.2, min(zoom, 3.0))
        self.view.set_zoom_level(self.zoom_level)

    def update_profile(self, device: DeviceProfile, orientation: Orientation) -> None:
        self.device = device
        self.orientation = orientation
        self._inject_mobile_emulation()
