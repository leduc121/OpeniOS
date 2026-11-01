#!/usr/bin/env python3
"""OpeniOS Live Preview — Native Ubuntu iPhone Simulator Launcher.

Usage:
    ./openios/live_preview/main.py [options] [PROJECT_DIR]

Options:
    --project PATH     Path to local project directory (React/Vite, Expo, Flutter)
    --device ID        Device preset (iphone-14-pro-max, iphone-15, iphone-15-pro-max)
    --zoom SCALE       Scale factor (0.5, 0.75, 0.85, 1.0)
    --help, -h         Show this help message
"""

import argparse
import os
from pathlib import Path
import sys

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Auto-reexec with /usr/bin/python3 if PyGObject (gi) is missing in current Python
try:
    import gi
except ImportError:
    system_python = "/usr/bin/python3"
    if os.path.isfile(system_python) and sys.executable != system_python:
        print(f"[OpeniOS Launcher] Re-executing with system Python ({system_python}) to access GTK bindings...")
        os.execv(system_python, [system_python] + sys.argv)
    else:
        print("[OpeniOS Fatal] PyGObject ('gi') is not installed in Python environment.")
        print("Please install python3-gi: sudo apt install python3-gi gir1.2-webkit2-4.1")
        sys.exit(1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="OpeniOS Live Preview Desktop Application",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "dir",
        nargs="?",
        type=Path,
        help="Optional project directory to launch immediately",
    )
    parser.add_argument(
        "--project",
        type=Path,
        help="Path to project directory",
    )
    parser.add_argument(
        "--device",
        default="iphone-12-pro-max",
        help="Target device profile ID",
    )
    parser.add_argument(
        "--zoom",
        type=float,
        default=0.75,
        help="Initial viewport zoom scale factor",
    )
    parser.add_argument(
        "--test-smoke",
        action="store_true",
        help="Initialize UI in headless test mode, verify components, and exit",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    # Determine project directory if specified
    project_path: Path | None = args.project or args.dir
    if project_path:
        project_path = project_path.resolve()
        if not project_path.is_dir():
            print(f"[OpeniOS Error] Project path '{project_path}' does not exist.")
            sys.exit(1)

    import signal
    from openios.live_preview.core.process_manager import ProcessManager
    from openios.live_preview.app import OpenIOSApplication

    def _sig_handler(sig: int, frame: object) -> None:
        ProcessManager.cleanup_all()
        sys.exit(0)

    try:
        signal.signal(signal.SIGINT, _sig_handler)
        signal.signal(signal.SIGTERM, _sig_handler)
    except Exception:
        pass

    if args.test_smoke:
        print("[OpeniOS Smoke Test] Initializing application components...")
        from openios.live_preview.window import SimulatorWindow
        from openios.live_preview.devices.registry import device_registry
        from openios.live_preview.adapters.registry import adapter_registry

        assert device_registry.get("iphone-12-pro-max") is not None, "Missing iPhone 12 Pro Max profile"
        assert len(adapter_registry._adapters) >= 4, "Missing framework adapters"
        win = SimulatorWindow(initial_project_path=project_path)
        print("[OpeniOS Smoke Test] PASS: Application, window, webview, and device frame initialized successfully.")
        return 0

    app = OpenIOSApplication(
        initial_project=project_path,
        initial_zoom=args.zoom,
        initial_device=args.device,
    )
    try:
        return app.run(None)
    finally:
        ProcessManager.cleanup_all()


if __name__ == "__main__":
    sys.exit(main())
