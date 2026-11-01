"""Project descriptor and path verification."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional
from openios.live_preview.core.models import FrameworkType, ProjectInfo


class ProjectManager:
    """Handles local project directory validation, config loading, and metadata."""

    @staticmethod
    def load_package_json(project_dir: Path) -> Optional[dict[str, Any]]:
        pkg_path = project_dir / "package.json"
        if not pkg_path.is_file():
            return None
        try:
            with open(pkg_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    @staticmethod
    def detect_package_manager(project_dir: Path) -> str:
        """Inspect lockfiles to choose npm, pnpm, yarn, or bun."""
        if (project_dir / "pnpm-lock.yaml").is_file():
            return "pnpm"
        if (project_dir / "yarn.lock").is_file():
            return "yarn"
        if (project_dir / "bun.lockb").is_file() or (project_dir / "bun.lock").is_file():
            return "bun"
        return "npm"

    @classmethod
    def inspect(cls, directory: Path) -> Optional[ProjectInfo]:
        """Validate directory and return structured project info if supported."""
        dir_path = directory.resolve()
        if not dir_path.is_dir():
            return None

        from openios.live_preview.core.framework_detector import FrameworkDetector
        return FrameworkDetector.detect(dir_path)
