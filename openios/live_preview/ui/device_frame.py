"""Device frame widget rendering authentic iPhone chassis, bezel, Dynamic Island, and Home indicator."""

from __future__ import annotations

import math
from typing import Callable, Optional

import cairo
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk

from openios.live_preview.core.models import DeviceProfile, Orientation
from openios.live_preview.preview.webview import SimulatorWebView


def draw_rounded_rect(
    cr: cairo.Context,
    x: float,
    y: float,
    w: float,
    h: float,
    r: float,
) -> None:
    """Draw a path for a rounded rectangle with radius r."""
    r = min(r, w / 2.0, h / 2.0)
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2.0, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2.0)
    cr.arc(x + r, y + h - r, r, math.pi / 2.0, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 3.0 * math.pi / 2.0)
    cr.close_path()


class ClippedScreenContainer(Gtk.Bin):
    """Native GTK container that uses Cairo clipping to constrain child widgets strictly to rounded screen corners."""

    def __init__(self, get_corner_radius: Callable[[], float]) -> None:
        super().__init__()
        self.set_has_window(False)
        self._get_corner_radius = get_corner_radius

    def do_draw(self, cr: cairo.Context) -> bool:
        alloc = self.get_allocation()
        cr.save()
        corner_r = self._get_corner_radius()
        draw_rounded_rect(cr, 0, 0, alloc.width, alloc.height, corner_r)
        cr.clip()
        child = self.get_child()
        if child:
            self.propagate_draw(child, cr)
        cr.restore()
        return True


class DeviceFrame(Gtk.Box):
    """High-fidelity iPhone hardware frame wrapping an interactive embedded WebView."""

    def __init__(
        self,
        device: DeviceProfile,
        web_view: SimulatorWebView,
        orientation: Orientation = Orientation.PORTRAIT,
        zoom: float = 1.0,
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.device = device
        self.web_view = web_view
        self.orientation = orientation
        self.zoom = zoom

        self.set_halign(Gtk.Align.CENTER)
        self.set_valign(Gtk.Align.CENTER)

        # Outer chassis drawing area
        self.chassis_container = Gtk.EventBox()
        self.chassis_container.set_visible_window(False)

        # Screen overlay (hosts clipped WebView + decorations layer)
        self.screen_overlay = Gtk.Overlay()

        # Web view widget wrapped in native Cairo clipping container
        self.web_widget = self.web_view.widget
        self.screen_container = ClippedScreenContainer(
            lambda: self.device.screen_corner_radius * self.zoom
        )
        self.screen_container.add(self.web_widget)
        self.screen_overlay.add(self.screen_container)

        # Pass-through screen decoration layer (Dynamic Island / Notch, Home indicator)
        self.decoration_layer = Gtk.DrawingArea()
        self.decoration_layer.connect("draw", self._on_draw_decorations)
        self.screen_overlay.add_overlay(self.decoration_layer)
        self.screen_overlay.set_overlay_pass_through(self.decoration_layer, True)

        # Main frame layout: chassis draws outer phone, contains screen_overlay
        self.outer_chassis = Gtk.DrawingArea()
        self.outer_chassis.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.outer_chassis.connect("draw", self._on_draw_chassis)

        # Overlay to place screen inside chassis
        self.frame_overlay = Gtk.Overlay()
        self.frame_overlay.add(self.outer_chassis)
        self.frame_overlay.add_overlay(self.screen_overlay)

        self.pack_start(self.frame_overlay, True, True, 0)
        self._update_geometry()

    @property
    def frame_width(self) -> int:
        logical_w, _ = self.device.get_viewport_dimensions(self.orientation)
        vw = int(round(logical_w * self.zoom))
        bezel = int(round(self.device.bezel_thickness * self.zoom))
        pad_x = int(round(6 * self.zoom))
        return vw + (bezel * 2) + (pad_x * 2)

    @property
    def frame_height(self) -> int:
        _, logical_h = self.device.get_viewport_dimensions(self.orientation)
        vh = int(round(logical_h * self.zoom))
        bezel = int(round(self.device.bezel_thickness * self.zoom))
        pad_y = int(round(6 * self.zoom))
        return vh + (bezel * 2) + (pad_y * 2)

    def set_device(self, device: DeviceProfile) -> None:
        self.device = device
        self.web_view.update_profile(self.device, self.orientation)
        self._update_geometry()

    def set_orientation(self, orientation: Orientation) -> None:
        self.orientation = orientation
        self.web_view.update_profile(self.device, self.orientation)
        self._update_geometry()

    def set_zoom(self, zoom: float) -> None:
        self.zoom = max(0.3, min(zoom, 2.0))
        self.web_view.set_zoom(self.zoom)
        self._update_geometry()

    def _update_geometry(self) -> None:
        logical_w, logical_h = self.device.get_viewport_dimensions(self.orientation)
        vw = int(round(logical_w * self.zoom))
        vh = int(round(logical_h * self.zoom))

        bezel = int(round(self.device.bezel_thickness * self.zoom))
        pad_x = int(round(6 * self.zoom))
        pad_y = int(round(6 * self.zoom))

        phone_w = vw + (bezel * 2)
        phone_h = vh + (bezel * 2)
        total_w = phone_w + (pad_x * 2)
        total_h = phone_h + (pad_y * 2)

        self.web_widget.set_size_request(vw, vh)
        self.screen_container.set_size_request(vw, vh)
        self.decoration_layer.set_size_request(vw, vh)
        self.screen_overlay.set_size_request(vw, vh)
        self.screen_overlay.set_halign(Gtk.Align.CENTER)
        self.screen_overlay.set_valign(Gtk.Align.CENTER)
        self.outer_chassis.set_size_request(total_w, total_h)
        self.frame_overlay.set_size_request(total_w, total_h)

        self.queue_draw()

    def _on_draw_chassis(self, widget: Gtk.Widget, cr: cairo.Context) -> bool:
        alloc = widget.get_allocation()
        w = alloc.width
        h = alloc.height
        z = self.zoom

        logical_w, logical_h = self.device.get_viewport_dimensions(self.orientation)
        vw = int(round(logical_w * z))
        vh = int(round(logical_h * z))
        bezel = int(round(self.device.bezel_thickness * z))

        screen_x = (w - vw) // 2
        screen_y = (h - vh) // 2
        phone_x = screen_x - bezel
        phone_y = screen_y - bezel
        phone_w = vw + (bezel * 2)
        phone_h = vh + (bezel * 2)
        corner_r = (self.device.screen_corner_radius + self.device.bezel_thickness) * z

        # 1. Soft realistic drop shadow layers
        cr.save()
        for off_y, alpha in [(2 * z, 0.10), (6 * z, 0.15), (12 * z, 0.22)]:
            draw_rounded_rect(cr, phone_x, phone_y + off_y, phone_w, phone_h, corner_r)
            cr.set_source_rgba(0.0, 0.0, 0.0, alpha)
            cr.fill()
        cr.restore()

        # 2. Side Hardware Buttons (Silent switch, Vol+, Vol-, Power)
        btn_w = 2.6 * z
        if self.orientation == Orientation.PORTRAIT:
            cr.save()
            # Mute switch nub
            draw_rounded_rect(cr, phone_x - btn_w, phone_y + 85 * z, btn_w + 1, 16 * z, 1.25 * z)
            # Volume Up
            draw_rounded_rect(cr, phone_x - btn_w, phone_y + 120 * z, btn_w + 1, 38 * z, 1.25 * z)
            # Volume Down
            draw_rounded_rect(cr, phone_x - btn_w, phone_y + 172 * z, btn_w + 1, 38 * z, 1.25 * z)
            # Power / Side button on right
            draw_rounded_rect(cr, phone_x + phone_w - 1, phone_y + 138 * z, btn_w + 1, 62 * z, 1.25 * z)
            cr.set_source_rgb(0.18, 0.19, 0.21)
            cr.fill_preserve()
            cr.set_line_width(0.75)
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.15)
            cr.stroke()
            cr.restore()

        # 3. Outer Stainless Steel Chassis Band (iPhone 12 Pro Max Graphite)
        draw_rounded_rect(cr, phone_x, phone_y, phone_w, phone_h, corner_r)
        chassis_pat = cairo.LinearGradient(phone_x, phone_y, phone_x, phone_y + phone_h)
        chassis_pat.add_color_stop_rgb(0.0, 0.14, 0.15, 0.17)
        chassis_pat.add_color_stop_rgb(0.5, 0.10, 0.10, 0.12)
        chassis_pat.add_color_stop_rgb(1.0, 0.12, 0.13, 0.15)
        cr.set_source(chassis_pat)
        cr.fill_preserve()

        # 4. Specular outer rim highlight (gives authentic metallic iPhone edge)
        cr.set_line_width(1.0)
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.20)
        cr.stroke()

        # 5. Inner Pitch Black Bezel & Display Backing
        rim_w = max(1.5, 2.5 * z)
        inner_r = max(1.0, corner_r - rim_w)
        draw_rounded_rect(cr, phone_x + rim_w, phone_y + rim_w, phone_w - (rim_w * 2), phone_h - (rim_w * 2), inner_r)
        cr.set_source_rgb(0.0, 0.0, 0.0)
        cr.fill()

        return True

    def _on_draw_decorations(self, widget: Gtk.Widget, cr: cairo.Context) -> bool:
        """Draw authentic Apple Notch / Dynamic Island and Home indicator."""
        alloc = widget.get_allocation()
        vw = alloc.width
        vh = alloc.height
        z = self.zoom

        # 1. Subtle OLED glass seam outline along screen edge
        corner_r = self.device.screen_corner_radius * z
        cr.save()
        draw_rounded_rect(cr, 0.5, 0.5, vw - 1.0, vh - 1.0, corner_r)
        cr.set_line_width(0.75)
        cr.set_source_rgba(0.0, 0.0, 0.0, 0.3)
        cr.stroke()
        cr.restore()

        # 2. Top Cutout: Authentic Apple Notch OR Dynamic Island
        if self.orientation == Orientation.PORTRAIT:
            if getattr(self.device, "cutout_type", "notch") == "notch":
                # Apple Notch Geometry matching Reference B (iPhone 12 Pro Max)
                nw = getattr(self.device, "notch_width", 208) * z
                nh = getattr(self.device, "notch_height", 30) * z
                nr = getattr(self.device, "notch_corner_radius", 10) * z
                tr = 4.0 * z  # smooth top inverse shoulder
                nx = (vw - nw) / 2.0

                cr.save()
                cr.new_path()
                # Start at top edge to the left of the notch
                cr.move_to(nx - tr, 0)
                # Top-left inverse shoulder: from -90° to 0° (increasing -> cr.arc)
                cr.arc(nx - tr, tr, tr, -math.pi / 2.0, 0)
                # Left straight edge
                cr.line_to(nx, nh - nr)
                # Bottom-left corner: from 180° to 90° (decreasing -> cr.arc_negative)
                cr.arc_negative(nx + nr, nh - nr, nr, math.pi, math.pi / 2.0)
                # Bottom straight edge
                cr.line_to(nx + nw - nr, nh)
                # Bottom-right corner: from 90° to 0° (decreasing -> cr.arc_negative)
                cr.arc_negative(nx + nw - nr, nh - nr, nr, math.pi / 2.0, 0)
                # Right straight edge
                cr.line_to(nx + nw, tr)
                # Top-right inverse shoulder: from 180° to 270° (increasing -> cr.arc)
                cr.arc(nx + nw + tr, tr, tr, math.pi, 3.0 * math.pi / 2.0)
                cr.close_path()

                cr.set_source_rgb(0.0, 0.0, 0.0)
                cr.fill()

                # Speaker slit centered near top of notch
                slit_w = 42.0 * z
                slit_h = 2.4 * z
                slit_x = (vw - slit_w) / 2.0
                slit_y = 3.0 * z
                draw_rounded_rect(cr, slit_x, slit_y, slit_w, slit_h, 1.2 * z)
                cr.set_source_rgb(0.12, 0.12, 0.14)
                cr.fill()

                # Front camera optics to the right of speaker
                cam_r = 3.8 * z
                cam_x = nx + nw - 24.0 * z
                cam_y = nh / 2.0
                cr.arc(cam_x, cam_y, cam_r, 0, 2 * math.pi)
                cr.set_source_rgb(0.06, 0.08, 0.12)
                cr.fill()

                # Camera lens reflection highlight
                cr.arc(cam_x - 0.9 * z, cam_y - 0.9 * z, 1.1 * z, 0, 2 * math.pi)
                cr.set_source_rgba(0.3, 0.45, 0.7, 0.5)
                cr.fill()

                # Ambient light sensor to the left of speaker
                sensor_r = 2.4 * z
                sensor_x = nx + 24.0 * z
                sensor_y = nh / 2.0
                cr.arc(sensor_x, sensor_y, sensor_r, 0, 2 * math.pi)
                cr.set_source_rgb(0.04, 0.05, 0.07)
                cr.fill()
                cr.restore()

            else:
                # Dynamic Island pill for 14 Pro / 15 series
                di = self.device.dynamic_island
                di_w = di.width * z
                di_h = di.height * z
                di_x = (vw - di_w) / 2.0
                di_y = di.top_offset * z
                di_r = di.corner_radius * z

                cr.save()
                draw_rounded_rect(cr, di_x, di_y, di_w, di_h, di_r)
                cr.set_source_rgb(0.0, 0.0, 0.0)
                cr.fill()

                cam_r = 4.5 * z
                cam_x = di_x + di_w - 20.0 * z
                cam_y = di_y + (di_h / 2.0)
                cr.arc(cam_x, cam_y, cam_r, 0, 2 * math.pi)
                cr.set_source_rgb(0.06, 0.08, 0.12)
                cr.fill()
                cr.restore()

        # 3. Home indicator bar (centered at bottom)
        hi = self.device.home_indicator
        hi_w = hi.width * z
        hi_h = hi.height * z
        hi_x = (vw - hi_w) / 2.0
        hi_y = vh - (hi.bottom_offset * z) - hi_h
        hi_r = hi.corner_radius * z

        cr.save()
        draw_rounded_rect(cr, hi_x, hi_y, hi_w, hi_h, hi_r)
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.75)
        cr.fill()
        cr.restore()

        return True
