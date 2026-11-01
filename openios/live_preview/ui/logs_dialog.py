"""Standalone console log viewer window."""

from __future__ import annotations

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, GLib, Gtk, Pango

from openios.live_preview.core.process_manager import ProcessManager


class LogsDialog(Gtk.Window):
    """Separate non-intrusive console drawer for dev server logs."""

    def __init__(self, parent: Gtk.Window, process_mgr: ProcessManager) -> None:
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.set_transient_for(parent)
        self.set_title("OpeniOS — Dev Server Console")
        self.set_default_size(640, 340)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        self.get_style_context().add_class("logs-dialog-window")

        self.process_mgr = process_mgr

        # Main box
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_start(10)
        box.set_margin_end(10)
        box.set_margin_top(8)
        box.set_margin_bottom(8)

        # Header bar
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        title = Gtk.Label(label="<b>Dev Server Console Output</b>")
        title.set_use_markup(True)
        header.pack_start(title, False, False, 0)

        btn_copy = Gtk.Button(label="Copy All")
        btn_copy.connect("clicked", self._on_copy_all)
        header.pack_end(btn_copy, False, False, 0)

        btn_clear = Gtk.Button(label="Clear")
        btn_clear.connect("clicked", lambda b: self.buffer.set_text(""))
        header.pack_end(btn_clear, False, False, 0)

        box.pack_start(header, False, False, 0)

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
        box.pack_start(self.scrolled, True, True, 0)

        self.add(box)

        # Populate with existing logs
        if self.process_mgr.logs:
            self.buffer.set_text("\n".join(self.process_mgr.logs) + "\n")

        # Hide instead of destroy on close
        self.connect("delete-event", lambda w, e: self.hide_on_delete())

    def append_log(self, text: str) -> None:
        def _do_append() -> bool:
            end_iter = self.buffer.get_end_iter()
            self.buffer.insert(end_iter, text + "\n")
            adj = self.scrolled.get_vadjustment()
            if adj:
                adj.set_value(adj.get_upper() - adj.get_page_size())
            return False

        GLib.idle_add(_do_append)

    def _on_copy_all(self, button: Gtk.Button) -> None:
        start_iter = self.buffer.get_start_iter()
        end_iter = self.buffer.get_end_iter()
        text = self.buffer.get_text(start_iter, end_iter, True)
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(text, -1)
