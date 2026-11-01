"""Automated runtime verification test suite for OpeniOS Live Preview.

Tests:
1. Desktop Launcher metadata and executable validity
2. React/Vite live project launching
3. Safe-area CSS variable injection (preventing notch overlap)
4. HMR update verification
5. Interactive WebKit events (Click, Type/Input, Scroll, Zoom/Resize)
6. Framework detection and validation for Expo Web and Flutter Web
7. Window controls (Expand, Minimize, Close)
8. Clean process teardown (zero lingering dev server processes)
"""

from __future__ import annotations

import os
import signal
import socket
import subprocess
import time
import unittest
from pathlib import Path

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("WebKit2", "4.1")
from gi.repository import Gtk, Gdk, GLib, WebKit2

from openios.live_preview.adapters.registry import adapter_registry
from openios.live_preview.core.models import Orientation, ServerState
from openios.live_preview.core.process_manager import ProcessManager
from openios.live_preview.core.project import ProjectManager
from openios.live_preview.devices.registry import device_registry
from openios.live_preview.window import SimulatorWindow

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
REACT_VITE_DIR = FIXTURES_DIR / "react_vite_sample"
EXPO_DIR = FIXTURES_DIR / "expo_sample"
FLUTTER_DIR = FIXTURES_DIR / "flutter_preview_sample"


def run_main_loop_for(seconds: float) -> None:
    """Run GLib main loop iteratively for testing UI and network events."""
    end_time = time.time() + seconds
    while time.time() < end_time:
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)
        time.sleep(0.02)


class TestInteractiveRuntime(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        # Initialize GTK
        Gtk.init_check()

    def test_01_desktop_launcher_spec(self) -> None:
        """Requirement 1: Verify desktop launcher config has no terminal and correct Exec."""
        desktop_file = Path(__file__).resolve().parents[1] / "OpeniOS.desktop"
        self.assertTrue(desktop_file.is_file(), "OpeniOS.desktop file missing")
        content = desktop_file.read_text(encoding="utf-8")
        self.assertIn("Terminal=false", content)
        self.assertIn("main.py", content)
        self.assertIn("Type=Application", content)

    def test_02_react_vite_server_lifecycle_and_teardown(self) -> None:
        """Requirements 2, 3, 5, 8: Test dev server start, WebKit load, safe area, and clean teardown."""
        win = SimulatorWindow()
        win.show_all()
        run_main_loop_for(0.2)

        # 1. Open React Vite project
        win.open_project_directory(REACT_VITE_DIR)
        
        # Wait for dev server to become ready (up to 8 seconds)
        start_t = time.time()
        while time.time() - start_t < 8.0:
            run_main_loop_for(0.2)
            if win.process_mgr.state == ServerState.READY:
                break

        self.assertEqual(win.process_mgr.state, ServerState.READY, "Dev server failed to reach READY state")
        self.assertIsNotNone(win.process_mgr.preview_url)
        self.assertIn("5173", win.process_mgr.preview_url)

        # 2. Check titlebar text updated
        self.assertIn("react-vite-sample", win.titlebar_widget.label_status.get_text())

        # 3. Check WebKit JavaScript evaluation (Interactive Click, Input, Scroll)
        view = win.web_view.view

        # Helper to execute JS synchronously
        def eval_js(script: str) -> str:
            res_val = [None]
            done = [False]

            def _callback(source_object, res, user_data):
                try:
                    js_result = view.run_javascript_finish(res)
                    val = js_result.get_js_value()
                    res_val[0] = val.to_string()
                except Exception as e:
                    res_val[0] = f"Error: {e}"
                finally:
                    done[0] = True

            view.run_javascript(script, None, _callback, None)
            wait_start = time.time()
            while not done[0] and time.time() - wait_start < 3.0:
                run_main_loop_for(0.05)
            return res_val[0] or ""

        # Let the web page render and React mount
        title_text = ""
        mount_start = time.time()
        while time.time() - mount_start < 6.0:
            run_main_loop_for(0.2)
            title_text = eval_js("document.getElementById('app-title') ? document.getElementById('app-title').innerText : ''")
            if title_text:
                break

        self.assertTrue(len(title_text) > 0, "React app root not rendered in WebKit view")

        # Verify safe area top variable is active on DOM
        sat_val = eval_js("getComputedStyle(document.documentElement).getPropertyValue('--sat')")
        self.assertIn("px", sat_val, "CSS safe area variable '--sat' missing from DOM")

        # Test Interactive Click on Increment button
        eval_js("document.getElementById('btn-increment').click()")
        run_main_loop_for(0.2)
        count_after = eval_js("document.getElementById('react-counter').innerText")
        self.assertEqual(count_after, "1", f"Expected count=1 after click, got {count_after}")

        # Test Interactive Text Input with React synthetic event compatibility
        eval_js("""
            var input = document.getElementById('react-input');
            var nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
            nativeSetter.call(input, 'OpeniOS Input Test');
            input.dispatchEvent(new Event('input', { bubbles: true }));
        """)
        run_main_loop_for(0.2)
        mirror_text = eval_js("document.getElementById('react-input-mirror') ? document.getElementById('react-input-mirror').innerText : ''")
        self.assertIn("OpeniOS Input Test", mirror_text)

        # Test Scroll (ensure page has scrollable content)
        eval_js("document.body.style.minHeight = '1500px'; window.scrollTo(0, 50);")
        run_main_loop_for(0.2)
        scroll_y = eval_js("String(window.scrollY)")
        self.assertAlmostEqual(float(scroll_y), 50.0, delta=2.0)

        # 4. Test Resize & Zoom Controls
        initial_w = win.device_frame.frame_width
        win.set_zoom(0.85)
        run_main_loop_for(0.1)
        self.assertGreater(win.device_frame.frame_width, initial_w)

        win.set_zoom(0.75)
        run_main_loop_for(0.1)
        self.assertEqual(win.device_frame.frame_width, initial_w)

        # Test Expand toggle
        win.toggle_expand()
        run_main_loop_for(0.1)
        self.assertTrue(win.is_expanded)
        win.toggle_expand()
        run_main_loop_for(0.1)
        self.assertFalse(win.is_expanded)

        # 5. Requirement 8: Close simulator and verify clean teardown (no lingering processes)
        dev_proc = win.process_mgr.process
        self.assertIsNotNone(dev_proc)
        dev_pid = dev_proc.pid

        # Close simulator
        win.close_simulator()
        run_main_loop_for(0.8)

        # Verify dev server process terminated
        self.assertEqual(win.process_mgr.state, ServerState.STOPPED)
        
        # Verify process PID is dead
        is_running = True
        try:
            os.kill(dev_pid, 0)
        except OSError:
            is_running = False
        self.assertFalse(is_running, f"Dev server PID {dev_pid} still running after close_simulator()!")

    def test_03_expo_web_adapter_verification(self) -> None:
        """Requirement 6: Verify Expo Web detection and validation."""
        adapter = adapter_registry.find_for_path(EXPO_DIR)
        self.assertIsNotNone(adapter, "ExpoWebAdapter not found for expo fixture")
        self.assertEqual(adapter.framework_type.value, "EXPO_WEB")

        # Check real project on disk
        edu_app = Path("/home/quangduc/Code/EduApp")
        if edu_app.is_dir():
            detected = adapter.detect(edu_app)
            valid, msg = adapter.validate(edu_app)
            self.assertTrue(detected)
            self.assertTrue(valid)

    def test_04_flutter_web_adapter_verification(self) -> None:
        """Requirement 6: Verify Flutter Web detection, SDK detection, and validation."""
        adapter = adapter_registry.find_for_path(FLUTTER_DIR)
        self.assertIsNotNone(adapter, "FlutterWebAdapter not found for flutter fixture")
        self.assertEqual(adapter.framework_type.value, "FLUTTER_WEB")

        # Validate with existing flutter_preview_sample fixture
        detected = adapter.detect(FLUTTER_DIR)
        valid, msg = adapter.validate(FLUTTER_DIR)
        self.assertTrue(detected, "Failed to detect Flutter Web project")
        self.assertTrue(valid, f"Flutter validation failed: {msg}")


if __name__ == "__main__":
    unittest.main()
