"""Adapter for React + Vite and generic Vite dev servers with native HMR."""

from __future__ import annotations

import shutil
from pathlib import Path
from openios.live_preview.adapters.base import BaseFrameworkAdapter
from openios.live_preview.core.models import FrameworkType, ProjectInfo
from openios.live_preview.core.process_manager import ProcessManager
from openios.live_preview.core.project import ProjectManager


class ViteReactAdapter(BaseFrameworkAdapter):
    """Handles React + Vite and generic Vite projects with out-of-the-box HMR."""

    @property
    def framework_type(self) -> FrameworkType:
        return FrameworkType.REACT_VITE

    @property
    def display_name(self) -> str:
        return "React + Vite (HMR)"

    @property
    def supports_hmr(self) -> bool:
        return True

    def detect(self, project_path: Path) -> bool:
        pkg = ProjectManager.load_package_json(project_path)
        if not pkg:
            return False
        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
        scripts = pkg.get("scripts", {})
        has_vite = "vite" in deps or any("vite" in s for s in scripts.values())
        return has_vite

    def validate(self, project_path: Path) -> tuple[bool, str]:
        pkg = ProjectManager.load_package_json(project_path)
        if not pkg:
            return False, "Missing package.json in project root."

        # Check node installed
        if not shutil.which("node") and not (Path.home() / ".config/nvm/versions/node/v22.23.2/bin/node").exists():
            return False, "Node.js runtime not found in PATH or standard NVM paths."

        # Check node_modules
        if not (project_path / "node_modules").is_dir():
            pm = ProjectManager.detect_package_manager(project_path)
            return False, f"node_modules not found. Please run '{pm} install' in the project directory first."

        return True, "Valid Vite project ready to launch."

    def start(self, project: ProjectInfo, process_mgr: ProcessManager) -> bool:
        pm = project.package_manager or "npm"

        # Safe non-shell command array
        # We pass host 127.0.0.1 to avoid exposing the preview server to the local network
        cmd: list[str]
        if pm == "npm":
            cmd = ["npm", "run", project.dev_script, "--", "--host", "127.0.0.1"]
        elif pm == "pnpm":
            cmd = ["pnpm", "run", project.dev_script, "--host", "127.0.0.1"]
        elif pm == "yarn":
            cmd = ["yarn", "run", project.dev_script, "--host", "127.0.0.1"]
        elif pm == "bun":
            cmd = ["bun", "run", project.dev_script, "--host", "127.0.0.1"]
        else:
            cmd = ["npx", "vite", "--host", "127.0.0.1"]

        return process_mgr.start_process(
            command=cmd,
            cwd=project.path,
            fallback_port=5173,
        )
