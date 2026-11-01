"""Compact macOS-style floating simulator titlebar with pixel-perfect traffic lights."""

from __future__ import annotations

import math
from typing import Callable, Optional

import cairo
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, Gtk, Pango


class TrafficLights(Gtk.DrawingArea):
    """Custom Cairo-drawn macOS traffic-light window controls (Close, Minimize, Expand)."""

    def __init__(
        self,
        on_close: Callable[[], None],
        on_minimize: Callable[[], None],
        on_expand: Callable[[], None],
    ) -> None:
        super().__init__()
        self.set_size_request(56, 20)
        self.on_close = on_close
        self.on_minimize = on_minimize
        self.on_expand = on_expand
        self.hovered_btn: Optional[int] = None  # 0: close, 1: min, 2: expand

        self.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.POINTER_MOTION_MASK
            | Gdk.EventMask.LEAVE_NOTIFY_MASK
        )
        self.connect("draw", self._on_draw)
        self.connect("motion-notify-event", self._on_motion)
        self.connect("leave-notify-event", self._on_leave)
        self.connect("button-press-event", self._on_button_press)

    def _on_draw(self, widget: Gtk.Widget, cr: cairo.Context) -> bool:
        # 3 macOS traffic light circles
        # Center positions: (8, 10), (26, 10), (44, 10); radius: 5.5
        btns = [
            (8, 10, (1.0, 0.37, 0.34), (0.88, 0.27, 0.24)),   # Red (Close)
            (26, 10, (1.0, 0.74, 0.18), (0.87, 0.63, 0.15)),  # Yellow (Minimize)
            (44, 10, (0.15, 0.79, 0.25), (0.10, 0.67, 0.16)),  # Green (Expand)
        ]

        for i, (cx, cy, fill_rgb, stroke_rgb) in enumerate(btns):
            cr.arc(cx, cy, 5.5, 0, 2 * math.pi)
            cr.set_source_rgb(*fill_rgb)
            cr.fill_preserve()
            cr.set_source_rgb(*stroke_rgb)
            cr.set_line_width(0.75)
            cr.stroke()

            # If hovered, draw subtle macOS symbol
            if self.hovered_btn == i:
                cr.set_source_rgba(0.2, 0.1, 0.1, 0.7)
                cr.set_line_width(1.2)
                if i == 0:  # ×
                    cr.move_to(cx - 2.5, cy - 2.5)
                    cr.line_to(cx + 2.5, cy + 2.5)
                    cr.move_to(cx + 2.5, cy - 2.5)
                    cr.line_to(cx - 2.5, cy + 2.5)
                    cr.stroke()
                elif i == 1:  # −
                    cr.move_to(cx - 3, cy)
                    cr.line_to(cx + 3, cy)
                    cr.stroke()
                elif i == 2:  # +
                    cr.move_to(cx - 2.5, cy)
                    cr.line_to(cx + 2.5, cy)
                    cr.move_to(cx, cy - 2.5)
                    cr.line_to(cx, cy + 2.5)
                    cr.stroke()

        return True

    def _on_motion(self, widget: Gtk.Widget, event: Gdk.EventMotion) -> bool:
        x = event.x
        old_hover = self.hovered_btn
        if x < 18:
            self.hovered_btn = 0
            self.set_tooltip_text("Close (Ctrl+Q)")
        elif x < 36:
            self.hovered_btn = 1
            self.set_tooltip_text("Minimize")
        elif x < 54:
            self.hovered_btn = 2
            self.set_tooltip_text("Expand / Restore (F11)")
        else:
            self.hovered_btn = None
            self.set_tooltip_text(None)

        if old_hover != self.hovered_btn:
            self.queue_draw()
        return True

    def _on_leave(self, widget: Gtk.Widget, event: Gdk.EventCrossing) -> bool:
        self.hovered_btn = None
        self.queue_draw()
        return True

    def _on_button_press(self, widget: Gtk.Widget, event: Gdk.EventButton) -> bool:
        if event.button == 1:
            x = event.x
            if x < 18:
                self.on_close()
            elif x < 36:
                self.on_minimize()
            elif x < 54:
                self.on_expand()
            return True
        return False


class CompactTitlebar(Gtk.EventBox):
    """Sleek floating titlebar matching Apple's Simulator window header."""

    def __init__(
        self,
        window: Gtk.Window,
        on_close: Callable[[], None],
        on_minimize: Callable[[], None],
        on_toggle_expand: Callable[[], None],
        on_home: Callable[[], None],
        on_screenshot: Callable[[], None],
        on_rotate: Callable[[], None],
        on_open_menu: Callable[[Optional[Gdk.EventButton]], None],
    ) -> None:
        super().__init__()
        self.window = window
        self._on_close = on_close
        self._on_minimize = on_minimize
        self._on_toggle_expand = on_toggle_expand
        self._on_home = on_home
        self._on_screenshot = on_screenshot
        self._on_rotate = on_rotate
        self._on_open_menu = on_open_menu

        self.set_visible_window(False)
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.connect("button-press-event", self._on_button_press)

        self._build_ui()

    def _build_ui(self) -> None:
        self.bar_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.bar_box.get_style_context().add_class("compact-titlebar")

        # 1. Left: Three macOS traffic-light controls
        self.traffic_lights = TrafficLights(
            on_close=self._on_close,
            on_minimize=self._on_minimize,
            on_expand=self._on_toggle_expand,
        )
        self.traffic_lights.set_valign(Gtk.Align.CENTER)
        self.bar_box.pack_start(self.traffic_lights, False, False, 2)

        # 2. Center: Device Title and Connection Status
        title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        title_box.set_halign(Gtk.Align.CENTER)
        title_box.set_valign(Gtk.Align.CENTER)

        self.label_title = Gtk.Label(label="iPhone 12 Pro Max")
        self.label_title.get_style_context().add_class("titlebar-title")
        self.label_title.set_ellipsize(Pango.EllipsizeMode.END)
        self.label_title.set_max_width_chars(16)
        title_box.pack_start(self.label_title, False, False, 0)

        self.label_status = Gtk.Label(label="– 14.3")
        self.label_status.get_style_context().add_class("titlebar-status")
        self.label_status.set_ellipsize(Pango.EllipsizeMode.END)
        self.label_status.set_max_width_chars(14)
        title_box.pack_start(self.label_status, False, False, 0)

        self.bar_box.pack_start(title_box, True, True, 0)

        # 3. Right: Minimal utility icons matching reference image
        tool_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        tool_box.set_valign(Gtk.Align.CENTER)

        # Home icon
        self.btn_home = Gtk.Button(label="⌂")
        self.btn_home.get_style_context().add_class("titlebar-icon-btn")
        self.btn_home.set_tooltip_text("Welcome / Home")
        self.btn_home.connect("clicked", lambda b: self._on_home())
        tool_box.pack_start(self.btn_home, False, False, 0)

        # Screenshot icon
        self.btn_snap = Gtk.Button(label="📷")
        self.btn_snap.get_style_context().add_class("titlebar-icon-btn")
        self.btn_snap.set_tooltip_text("Capture Screenshot (Ctrl+S)")
        self.btn_snap.connect("clicked", lambda b: self._on_screenshot())
        tool_box.pack_start(self.btn_snap, False, False, 0)

        # Rotate icon
        self.btn_rotate = Gtk.Button(label="↻")
        self.btn_rotate.get_style_context().add_class("titlebar-icon-btn")
        self.btn_rotate.set_tooltip_text("Rotate Device (Ctrl+Shift+R)")
        self.btn_rotate.connect("clicked", lambda b: self._on_rotate())
        tool_box.pack_start(self.btn_rotate, False, False, 0)

        # Menu icon
        self.btn_menu = Gtk.Button(label="⋮")
        self.btn_menu.get_style_context().add_class("titlebar-icon-btn")
        self.btn_menu.set_tooltip_text("Options Menu (Right-Click)")
        self.btn_menu.connect("clicked", lambda b: self._on_open_menu(None))
        tool_box.pack_start(self.btn_menu, False, False, 0)

        self.bar_box.pack_end(tool_box, False, False, 0)
        self.add(self.bar_box)

    def set_title_info(self, device_name: str, status_text: str) -> None:
        self.label_title.set_text(device_name)
        self.label_status.set_text(f"– {status_text}")

    def _on_button_press(self, widget: Gtk.Widget, event: Gdk.EventButton) -> bool:
        if event.button == 1:
            # Native window dragging on Wayland / X11
            self.window.begin_move_drag(
                event.button,
                int(event.x_root),
                int(event.y_root),
                event.time,
            )
            return True
        elif event.button == 3:
            self._on_open_menu(event)
            return True
        return False
