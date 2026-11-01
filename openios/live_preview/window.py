"""Main floating iPhone desktop simulator window."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import cairo
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk

from openios.live_preview.adapters.base import BaseFrameworkAdapter
from openios.live_preview.adapters.registry import adapter_registry
from openios.live_preview.core.models import (
    BackendType,
    DeviceProfile,
    Orientation,
    ProjectInfo,
    ServerState,
)
from openios.live_preview.core.process_manager import ProcessManager
from openios.live_preview.core.project import ProjectManager
from openios.live_preview.devices.registry import device_registry
from openios.live_preview.preview.webview import SimulatorWebView
from openios.live_preview.ui.compact_titlebar import CompactTitlebar
from openios.live_preview.ui.device_frame import DeviceFrame
from openios.live_preview.ui.logs_dialog import LogsDialog

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
WELCOME_HTML = ASSETS_DIR / "welcome.html"


class SimulatorWindow(Gtk.Window):
    """Floating native iPhone simulator window tightly wrapping device and compact titlebar."""

    def __init__(
        self,
        initial_project_path: Optional[Path] = None,
        initial_zoom: float = 0.75,
        initial_device: Optional[str] = None,
    ) -> None:
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.set_title("OpeniOS Simulator")
        self.set_wmclass("OpeniOS", "OpeniOS")
        self.set_role("OpeniOS-Simulator")
        self.set_type_hint(Gdk.WindowTypeHint.NORMAL)
        self.set_decorated(False)  # Custom compact floating titlebar

        # Enable RGBA transparency on Wayland / X11
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.set_visual(visual)
        self.set_app_paintable(True)
        self.get_style_context().add_class("floating-window")
        self.connect("draw", self._on_window_draw)

        # Core state
        self.backend: BackendType = BackendType.LIVE_PREVIEW
        self.orientation: Orientation = Orientation.PORTRAIT
        self.zoom: float = initial_zoom
        self.pre_expand_zoom: float = initial_zoom
        self.is_expanded: bool = False
        device_id = initial_device or "iphone-12-pro-max"
        self.device_profile: DeviceProfile = device_registry.get_or_default(device_id)
        self.current_project: Optional[ProjectInfo] = None
        self.active_adapter: Optional[BaseFrameworkAdapter] = None

        # Initialize Process Manager
        self.process_mgr = ProcessManager(
            on_log=self._on_process_log,
            on_ready=self._on_server_ready,
            on_state_change=self._on_server_state_change,
        )

        # Separate logs dialog (opened via Ctrl+Shift+L or menu)
        self.logs_dialog = LogsDialog(self, self.process_mgr)

        # Initialize WebView
        self.web_view = SimulatorWebView(
            device=self.device_profile,
            orientation=self.orientation,
            zoom_level=self.zoom,
            on_title_changed=self._on_web_title_changed,
            on_load_finished=self._on_web_load_finished,
            on_load_failed=self._on_web_load_failed,
        )

        # Build UI layout
        self._build_layout()

        # Connect keyboard shortcuts and lifecycle
        self.connect("key-press-event", self._on_key_press)
        self.connect("delete-event", self._on_delete_event)

        # Load default welcome screen
        self._load_welcome()

        # Fit initial window bounds to phone frame
        self._fit_window_to_phone()

        # Load initial project if provided
        if initial_project_path:
            GLib.idle_add(lambda: self.open_project_directory(initial_project_path))

    def _build_layout(self) -> None:
        # Main vertical container tightly wrapping titlebar and phone
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.main_box.set_margin_start(8)
        self.main_box.set_margin_end(8)
        self.main_box.set_margin_top(6)
        self.main_box.set_margin_bottom(8)
        self.main_box.set_halign(Gtk.Align.CENTER)
        self.main_box.set_valign(Gtk.Align.CENTER)

        # Compact macOS-style titlebar with 3 traffic light buttons
        self.titlebar_widget = CompactTitlebar(
            window=self,
            on_close=self.close_simulator,
            on_minimize=self.minimize_simulator,
            on_toggle_expand=self.toggle_expand,
            on_home=self._load_welcome,
            on_screenshot=self.capture_screenshot,
            on_rotate=self.toggle_orientation,
            on_open_menu=self.show_context_menu,
        )
        self.titlebar_widget.set_halign(Gtk.Align.CENTER)
        self.main_box.pack_start(self.titlebar_widget, False, False, 0)

        # iPhone Device Frame
        self.device_frame = DeviceFrame(
            device=self.device_profile,
            web_view=self.web_view,
            orientation=self.orientation,
            zoom=self.zoom,
        )
        self.device_frame.outer_chassis.connect("button-press-event", self._on_chassis_button_press)
        self.main_box.pack_start(self.device_frame, True, True, 0)

        self.add(self.main_box)
        self._update_titlebar_text()

    def _on_window_draw(self, widget: Gtk.Widget, cr: cairo.Context) -> bool:
        """Clear the window surface with full RGBA transparency."""
        cr.save()
        cr.set_operator(cairo.OPERATOR_CLEAR)
        cr.paint()
        cr.restore()
        return False

    def _fit_window_to_phone(self) -> None:
        """Resize the desktop window to tightly hug the phone frame and titlebar."""
        phone_w = self.device_frame.frame_width
        phone_h = self.device_frame.frame_height

        # Compact titlebar width centered above phone
        titlebar_w = min(phone_w, 320)
        self.titlebar_widget.set_size_request(titlebar_w, 32)

        total_w = phone_w + 16
        total_h = 32 + 6 + phone_h + 14

        # Set geometry hints so Wayland / Hyprland strictly clamps floating window bounds
        geom = Gdk.Geometry()
        geom.min_width = total_w
        geom.min_height = total_h
        geom.max_width = total_w
        geom.max_height = total_h
        self.set_geometry_hints(self, geom, Gdk.WindowHints.MIN_SIZE | Gdk.WindowHints.MAX_SIZE)

        self.set_size_request(total_w, total_h)
        self.resize(total_w, total_h)

    def _load_welcome(self) -> None:
        if WELCOME_HTML.is_file():
            self.web_view.load_uri(f"file://{WELCOME_HTML.resolve()}")
        else:
            self.web_view.load_html("<h1>OpeniOS Simulator</h1><p>Ready for project.</p>")
        self._update_titlebar_text()

    def _update_titlebar_text(self) -> None:
        if self.current_project and self.active_adapter:
            status = f"{self.current_project.name} · Live"
        else:
            status = "14.3"
        self.titlebar_widget.set_title_info(self.device_profile.name, status)

    # --- Window Controls: Close, Minimize, Expand ---

    def close_simulator(self) -> None:
        self.stop_preview()
        self.destroy()

    def minimize_simulator(self) -> None:
        self.iconify()

    def toggle_expand(self) -> None:
        """Expand proportionally to fit workspace, or restore back to compact size."""
        if not self.is_expanded:
            self.pre_expand_zoom = self.zoom
            # Calculate maximum proportional scale that fits within monitor height
            display = Gdk.Display.get_default()
            monitor = display.get_primary_monitor() or display.get_monitor(0)
            if monitor:
                monitor_h = monitor.get_geometry().height
            else:
                monitor_h = 1080

            available_h = monitor_h - 140
            _, logical_h = self.device_profile.get_viewport_dimensions(self.orientation)
            max_zoom = max(0.85, min(1.1, available_h / (logical_h + 28)))

            self.set_zoom(max_zoom)
            self.is_expanded = True
        else:
            self.set_zoom(self.pre_expand_zoom)
            self.is_expanded = False

    def toggle_orientation(self) -> None:
        self.orientation = self.orientation.toggle()
        self.device_frame.set_orientation(self.orientation)
        self._fit_window_to_phone()

    def set_zoom(self, zoom: float) -> None:
        self.zoom = max(0.4, min(zoom, 1.8))
        self.device_frame.set_zoom(self.zoom)
        self._fit_window_to_phone()

    def set_device(self, device_id: str) -> None:
        profile = device_registry.get(device_id)
        if profile:
            self.device_profile = profile
            self.device_frame.set_device(profile)
            self._fit_window_to_phone()
            self._update_titlebar_text()

    # --- Project Management & Dev Server ---

    def open_project_dialog(self) -> None:
        dialog = Gtk.FileChooserDialog(
            title="Open Web or Mobile Project",
            parent=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK,
        )

        response = dialog.run()
        selected_path = dialog.get_filename()
        dialog.destroy()

        if response == Gtk.ResponseType.OK and selected_path:
            self.open_project_directory(Path(selected_path))

    def open_project_directory(self, project_path: Path) -> None:
        project = ProjectManager.inspect(project_path)
        if not project:
            self._show_error(
                "Unsupported Project",
                f"No supported framework was detected in:\n{project_path}\n\n"
                "Supported types:\n"
                "• React + Vite\n"
                "• Expo Web\n"
                "• Flutter Web\n"
                "• Static HTML/CSS/JS",
            )
            return

        adapter = adapter_registry.find_adapter(project)
        if not adapter:
            self._show_error(
                "Missing Adapter",
                f"Could not find an adapter for {project.framework.display_name()}.",
            )
            return

        valid, msg = adapter.validate(project.path)
        if not valid:
            self._show_error(f"Cannot Launch {adapter.display_name}", msg)
            return

        self.current_project = project
        self.active_adapter = adapter
        self.start_preview()

    def start_preview(self) -> None:
        if not self.current_project or not self.active_adapter:
            return

        self.titlebar_widget.set_title_info(
            self.device_profile.name,
            f"{self.current_project.name} · Starting...",
        )
        self.active_adapter.start(self.current_project, self.process_mgr)

    def stop_preview(self) -> None:
        if self.active_adapter:
            self.active_adapter.stop(self.process_mgr)
        else:
            self.process_mgr.stop_process()
        self._update_titlebar_text()

    def reload_preview(self) -> None:
        if self.active_adapter:
            self.active_adapter.reload(self.process_mgr)
        self.web_view.reload()

    # --- Screenshot ---

    def capture_screenshot(self) -> None:
        """Capture device screen contents and save to home directory or artifacts."""
        alloc = self.device_frame.get_allocation()
        if alloc.width <= 0 or alloc.height <= 0:
            return

        # Render device frame widget to Cairo image surface
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, alloc.width, alloc.height)
        cr = cairo.Context(surface)
        self.device_frame.draw(cr)

        # Save to Pictures or Code/OpeniOS directory
        pictures_dir = Path.home() / "Pictures"
        if not pictures_dir.is_dir():
            pictures_dir = Path.home()

        import time
        filename = f"openios_sim_{int(time.time())}.png"
        target_path = pictures_dir / filename
        surface.write_to_png(str(target_path))

        # Show brief title confirmation
        self.titlebar_widget.set_title_info(
            self.device_profile.name,
            f"Saved: {filename}",
        )
        GLib.timeout_add_seconds(3, lambda: (self._update_titlebar_text(), False)[1])

    # --- Right-Click Context Menu ---

    def _on_chassis_button_press(self, widget: Gtk.Widget, event: Gdk.EventButton) -> bool:
        if event.button == 3:  # Right-click on bezel
            self.show_context_menu(event)
            return True
        return False

    def show_context_menu(self, event: Optional[Gdk.EventButton]) -> None:
        menu = Gtk.Menu()

        # 1. Open Project
        item_open = Gtk.MenuItem(label="📁  Open Project... (Ctrl+O)")
        item_open.connect("activate", lambda m: self.open_project_dialog())
        menu.append(item_open)

        # 2. Run / Stop
        if self.process_mgr.state == ServerState.READY:
            item_run = Gtk.MenuItem(label="⏹  Stop Dev Server")
            item_run.connect("activate", lambda m: self.stop_preview())
        else:
            item_run = Gtk.MenuItem(label="▶  Start Dev Server")
            item_run.connect("activate", lambda m: self.start_preview() if self.current_project else self.open_project_dialog())
        menu.append(item_run)

        # 3. Reload
        item_reload = Gtk.MenuItem(label="🔄  Reload (Ctrl+R)")
        item_reload.connect("activate", lambda m: self.reload_preview())
        menu.append(item_reload)

        # 4. Rotate
        item_rotate = Gtk.MenuItem(label="↻  Rotate (Ctrl+Shift+R)")
        item_rotate.connect("activate", lambda m: self.toggle_orientation())
        menu.append(item_rotate)

        # 5. Screenshot
        item_snap = Gtk.MenuItem(label="📷  Take Screenshot (Ctrl+S)")
        item_snap.connect("activate", lambda m: self.capture_screenshot())
        menu.append(item_snap)

        menu.append(Gtk.SeparatorMenuItem())

        # 6. Device Preset Submenu
        item_device = Gtk.MenuItem(label="📱  Device Model")
        dev_sub = Gtk.Menu()
        for prof in device_registry.all_profiles():
            label = f"• {prof.name}" if prof.id == self.device_profile.id else f"   {prof.name}"
            sub_item = Gtk.MenuItem(label=label)
            sub_item.connect("activate", lambda m, pid=prof.id: self.set_device(pid))
            dev_sub.append(sub_item)
        item_device.set_submenu(dev_sub)
        menu.append(item_device)

        # 7. Zoom Submenu
        item_zoom = Gtk.MenuItem(label="🔍  Scale")
        zoom_sub = Gtk.Menu()
        zoom_levels = [(0.5, "50%"), (0.67, "67%"), (0.75, "75% (Compact)"), (0.85, "85%"), (1.0, "100% (Native)")]
        for z_val, z_lbl in zoom_levels:
            label = f"• {z_lbl}" if abs(self.zoom - z_val) < 0.04 else f"   {z_lbl}"
            sub_z = Gtk.MenuItem(label=label)
            sub_z.connect("activate", lambda m, val=z_val: self.set_zoom(val))
            zoom_sub.append(sub_z)
        item_zoom.set_submenu(zoom_sub)
        menu.append(item_zoom)

        menu.append(Gtk.SeparatorMenuItem())

        # 8. Dev Server Logs Dialog
        item_logs = Gtk.MenuItem(label="📋  Dev Server Console (Ctrl+Shift+L)")
        item_logs.connect("activate", lambda m: self.logs_dialog.show_all())
        menu.append(item_logs)

        # 9. Native Emulator info
        item_backend = Gtk.MenuItem(label="⚙  Native Emulator (QEMU-SPTM)...")
        item_backend.connect("activate", self._show_native_emulator_modal)
        menu.append(item_backend)

        menu.append(Gtk.SeparatorMenuItem())

        # 10. Quit
        item_quit = Gtk.MenuItem(label="✕  Quit OpeniOS (Ctrl+Q)")
        item_quit.connect("activate", lambda m: self.close_simulator())
        menu.append(item_quit)

        menu.show_all()
        if event:
            menu.popup(None, None, None, None, event.button, event.time)
        else:
            menu.popup(None, None, None, None, 0, Gtk.get_current_event_time())

    def _show_native_emulator_modal(self, menu_item: Gtk.MenuItem) -> None:
        dialog = Gtk.MessageDialog(
            parent=self,
            flags=Gtk.DialogFlags.MODAL,
            type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            message_format="Native Emulator Backend (QEMU-SPTM)",
        )
        dialog.format_secondary_text(
            "The Native Emulator backend targets QEMU-SPTM Darwin guest virtualization (M10.9-M13 checkpoint).\n\n"
            "Current Research Status: Host serial and QMP active; AppleA7IOP/RTBuddy execution verified; "
            "guest iOS SpringBoard framebuffer is not yet published.\n\n"
            "Live Preview remains active for high-speed web application development."
        )
        dialog.run()
        dialog.destroy()

    # --- Keyboard Shortcuts ---

    def _on_key_press(self, widget: Gtk.Widget, event: Gdk.EventKey) -> bool:
        ctrl = bool(event.state & Gdk.ModifierType.CONTROL_MASK)
        shift = bool(event.state & Gdk.ModifierType.SHIFT_MASK)
        kv = event.keyval

        if ctrl and not shift:
            if kv in (ord('o'), ord('O')):
                self.open_project_dialog()
                return True
            elif kv in (ord('r'), ord('R')):
                self.reload_preview()
                return True
            elif kv in (ord('s'), ord('S')):
                self.capture_screenshot()
                return True
            elif kv in (ord('='), ord('+')):
                self.set_zoom(self.zoom + 0.1)
                return True
            elif kv in (ord('-'), ord('_')):
                self.set_zoom(self.zoom - 0.1)
                return True
            elif kv == ord('0'):
                self.set_zoom(0.75)
                return True
            elif kv in (ord('q'), ord('Q'), ord('w'), ord('W')):
                self.close_simulator()
                return True
        elif ctrl and shift:
            if kv in (ord('r'), ord('R')):
                self.toggle_orientation()
                return True
            elif kv in (ord('l'), ord('L')):
                if self.logs_dialog.get_visible():
                    self.logs_dialog.hide()
                else:
                    self.logs_dialog.show_all()
                return True
        elif kv == Gdk.KEY_F11:
            self.toggle_expand()
            return True

        return False

    # --- Callbacks from ProcessManager & WebView ---

    def _on_process_log(self, text: str) -> None:
        self.logs_dialog.append_log(text)

    def _on_server_ready(self, url: str) -> None:
        GLib.idle_add(lambda: self._handle_server_ready(url))

    def _handle_server_ready(self, url: str) -> bool:
        self._update_titlebar_text()
        self.web_view.load_uri(url)
        return False

    def _on_server_state_change(self, state: ServerState) -> None:
        GLib.idle_add(self._update_titlebar_text)

    def _on_web_title_changed(self, title: str) -> None:
        pass

    def _on_web_load_finished(self, uri: str) -> None:
        pass

    def _on_web_load_failed(self, failing_uri: str) -> None:
        self.logs_dialog.append_log(f"[OpeniOS Error] Failed to load URI: {failing_uri}")

    def _show_error(self, title: str, message: str) -> None:
        dialog = Gtk.MessageDialog(
            parent=self,
            flags=Gtk.DialogFlags.MODAL,
            type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.OK,
            message_format=title,
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

    def _on_delete_event(self, widget: Gtk.Widget, event: Gdk.Event) -> bool:
        self.stop_preview()
        return False
