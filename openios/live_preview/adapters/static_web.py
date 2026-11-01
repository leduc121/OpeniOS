"""Adapter for static web projects and generic HTML/CSS/JavaScript."""

from __future__ import annotations

import sys
from pathlib import Path
from openios.live_preview.adapters.base import BaseFrameworkAdapter
from openios.live_preview.core.models import FrameworkType, ProjectInfo
from openios.live_preview.core.process_manager import ProcessManager
from openios.live_preview.core.project import ProjectManager


class StaticWebAdapter(BaseFrameworkAdapter):
    """Serves static directory using local http.server or project scripts."""

    @property
    def framework_type(self) -> FrameworkType:
        return FrameworkType.STATIC_WEB

    @property
    def display_name(self) -> str:
        return "Static Web"

    @property
    def supports_hmr(self) -> bool:
        return False

    def detect(self, project_path: Path) -> bool:
        return (project_path / "index.html").is_file()

    def validate(self, project_path: Path) -> tuple[bool, str]:
        if not (project_path / "index.html").is_file():
            return False, "Missing index.html in directory root."
        return True, "Static web directory ready to serve."

    def start(self, project: ProjectInfo, process_mgr: ProcessManager) -> bool:
        pkg = ProjectManager.load_package_json(project.path)
        if pkg and project.dev_script and project.dev_script in pkg.get("scripts", {}):
            pm = project.package_manager or "npm"
            cmd = [pm, "run", project.dev_script]
        else:
            # Fall back to safe Python http.server bound only to 127.0.0.1
            port = project.custom_port or 8000
            cmd = [
                sys.executable,
                "-m",
                "http.server",
                str(port),
                "--bind",
                "127.0.0.1",
            ]

        return process_mgr.start_process(
            command=cmd,
            cwd=project.path,
            fallback_port=8000,
        )
