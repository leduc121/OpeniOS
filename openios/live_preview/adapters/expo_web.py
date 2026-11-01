"""Adapter for Expo Web development server with Fast Refresh."""

from __future__ import annotations

import shutil
from pathlib import Path
from openios.live_preview.adapters.base import BaseFrameworkAdapter
from openios.live_preview.core.models import FrameworkType, ProjectInfo
from openios.live_preview.core.process_manager import ProcessManager
from openios.live_preview.core.project import ProjectManager


class ExpoWebAdapter(BaseFrameworkAdapter):
    """Handles Expo React Native Web projects with Expo Fast Refresh."""

    @property
    def framework_type(self) -> FrameworkType:
        return FrameworkType.EXPO_WEB

    @property
    def display_name(self) -> str:
        return "Expo Web (Fast Refresh)"

    @property
    def supports_hmr(self) -> bool:
        return True

    def detect(self, project_path: Path) -> bool:
        pkg = ProjectManager.load_package_json(project_path)
        if not pkg:
            return False
        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
        return "expo" in deps

    def validate(self, project_path: Path) -> tuple[bool, str]:
        pkg = ProjectManager.load_package_json(project_path)
        if not pkg:
            return False, "Missing package.json in project root."

        # Check node
        if not shutil.which("node") and not (Path.home() / ".config/nvm/versions/node/v22.23.2/bin/node").exists():
            return False, "Node.js runtime not found."

        # Check node_modules
        if not (project_path / "node_modules").is_dir():
            pm = ProjectManager.detect_package_manager(project_path)
            return False, f"node_modules not found. Please run '{pm} install' first."

        # Check web support package (react-native-web or @expo/metro-runtime)
        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
        if "react-native-web" not in deps:
            return True, "Note: 'react-native-web' is not explicitly listed; Expo may prompt or bundle it automatically."

        return True, "Valid Expo Web project ready to launch."

    def start(self, project: ProjectInfo, process_mgr: ProcessManager) -> bool:
        # Start Expo with web target and localhost binding
        cmd = ["npx", "expo", "start", "--web", "--localhost"]
        return process_mgr.start_process(
            command=cmd,
            cwd=project.path,
            fallback_port=8081,
        )
