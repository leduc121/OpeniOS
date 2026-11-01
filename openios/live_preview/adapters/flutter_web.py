"""Adapter for Flutter Web applications with local web-server target."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from openios.live_preview.adapters.base import BaseFrameworkAdapter
from openios.live_preview.core.models import FrameworkType, ProjectInfo
from openios.live_preview.core.process_manager import ProcessManager


class FlutterWebAdapter(BaseFrameworkAdapter):
    """Handles Flutter Web projects via Flutter's web-server device mode."""

    @property
    def framework_type(self) -> FrameworkType:
        return FrameworkType.FLUTTER_WEB

    @property
    def display_name(self) -> str:
        return "Flutter Web"

    @property
    def supports_hmr(self) -> bool:
        # Flutter web-server mode provides hot restart and incremental compile;
        # full state-preserving HMR depends on Flutter DevTools/debug transport.
        return False

    @staticmethod
    def find_flutter_bin() -> str:
        """Find flutter executable in system PATH or standard developer locations."""
        which_flutter = shutil.which("flutter")
        if which_flutter:
            return which_flutter
        dev_flutter = Path.home() / "develop/flutter/bin/flutter"
        if dev_flutter.is_file() and os.access(dev_flutter, os.X_OK):
            return str(dev_flutter)
        return "flutter"

    def detect(self, project_path: Path) -> bool:
        return (project_path / "pubspec.yaml").is_file()

    def validate(self, project_path: Path) -> tuple[bool, str]:
        if not (project_path / "pubspec.yaml").is_file():
            return False, "Missing pubspec.yaml in project root."

        flutter_bin = self.find_flutter_bin()
        if not shutil.which(flutter_bin) and not Path(flutter_bin).is_file():
            return False, "Flutter SDK not found. Please install Flutter or add it to PATH."

        # Check if web platform is enabled
        if not (project_path / "web").is_dir():
            return False, "Flutter web directory missing. Run 'flutter create --platforms web .' first."

        return True, "Valid Flutter Web project ready to launch."

    def start(self, project: ProjectInfo, process_mgr: ProcessManager) -> bool:
        from openios.live_preview.core.process_manager import find_available_port
        flutter_bin = self.find_flutter_bin()
        port = find_available_port(project.custom_port or 8088)

        # flutter run -d web-server --web-port <port> --web-hostname 127.0.0.1
        cmd = [
            flutter_bin,
            "run",
            "-d",
            "web-server",
            "--web-port",
            str(port),
            "--web-hostname",
            "127.0.0.1",
        ]

        return process_mgr.start_process(
            command=cmd,
            cwd=project.path,
            fallback_port=port,
        )

    def reload(self, process_mgr: ProcessManager) -> None:
        """Trigger Flutter incremental compile / hot reload via 'r\n' key command."""
        process_mgr.send_input("r\n")
