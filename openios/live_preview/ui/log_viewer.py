"""Collapsible console log viewer displaying dev-server stdout and stderr."""

from __future__ import annotations

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Pango, GLib


class LogViewer(Gtk.Box):
    """Monospace log drawer capturing real-time dev server outputs and diagnostic errors."""

    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.set_size_request(-1, 160)
        self.get_style_context().add_class("log-drawer")

        # Header with title and controls
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        header.set_margin_start(10)
        header.set_margin_end(10)
        header.set_margin_top(6)
        header.set_margin_bottom(6)

        title = Gtk.Label(label="<b>Dev Server Console Output</b>")
        title.set_use_markup(True)
        header.pack_start(title, False, False, 0)

        self.btn_clear = Gtk.Button(label="Clear")
        self.btn_clear.connect("clicked", lambda b: self.clear())
        header.pack_end(self.btn_clear, False, False, 0)

        self.pack_start(header, False, False, 0)

        # Scrolled Text view
        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        self.text_view = Gtk.TextView()
        self.text_view.set_editable(False)
        self.text_view.set_cursor_visible(False)
        self.text_view.set_wrap_mode(Gtk.WrapMode.CHAR)
        self.text_view.override_font(Pango.FontDescription("monospace 9"))
        self.text_view.get_style_context().add_class("console-text")

        self.buffer = self.text_view.get_buffer()
        self.scrolled.add(self.text_view)
        self.pack_start(self.scrolled, True, True, 0)

    def append_log(self, text: str) -> None:
        def _do_append() -> bool:
            end_iter = self.buffer.get_end_iter()
            self.buffer.insert(end_iter, text + "\n")
            # Auto scroll to bottom
            adj = self.scrolled.get_vadjustment()
            if adj:
                adj.set_value(adj.get_upper() - adj.get_page_size())
            return False

        GLib.idle_add(_do_append)

    def clear(self) -> None:
        self.buffer.set_text("")
