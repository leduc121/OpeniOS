"""Automatic framework detector inspecting project files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional
from openios.live_preview.core.models import FrameworkType, ProjectInfo
from openios.live_preview.core.project import ProjectManager


class FrameworkDetector:
    """Detects front-end framework, package manager, and dev server configurations."""

    @classmethod
    def detect(cls, directory: Path) -> Optional[ProjectInfo]:
        dir_path = directory.resolve()
        if not dir_path.is_dir():
            return None

        # Check Flutter (pubspec.yaml)
        pubspec = dir_path / "pubspec.yaml"
        if pubspec.is_file():
            return cls._detect_flutter(dir_path)

        # Check Node-based projects (package.json)
        pkg = ProjectManager.load_package_json(dir_path)
        if pkg:
            return cls._detect_node_project(dir_path, pkg)

        # Check Static HTML
        if (dir_path / "index.html").is_file():
            return ProjectInfo(
                path=dir_path,
                name=dir_path.name,
                framework=FrameworkType.STATIC_WEB,
                entry_file="index.html",
            )

        return None

    @classmethod
    def _detect_node_project(cls, directory: Path, pkg: dict) -> ProjectInfo:
        name = pkg.get("name", directory.name)
        scripts = pkg.get("scripts", {})
        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
        pm = ProjectManager.detect_package_manager(directory)

        # Determine dev script
        dev_script = "dev"
        if "dev" in scripts:
            dev_script = "dev"
        elif "start" in scripts:
            dev_script = "start"
        elif "serve" in scripts:
            dev_script = "serve"

        # 1. Expo
        if "expo" in deps:
            return ProjectInfo(
                path=directory,
                name=name,
                framework=FrameworkType.EXPO_WEB,
                package_manager=pm,
                dev_script=dev_script,
            )

        # 2. Next.js
        if "next" in deps:
            return ProjectInfo(
                path=directory,
                name=name,
                framework=FrameworkType.NEXTJS,
                package_manager=pm,
                dev_script=dev_script,
            )

        # 3. Vite + React
        has_vite = "vite" in deps or any("vite" in s for s in scripts.values())
        has_react = "react" in deps
        if has_vite and has_react:
            return ProjectInfo(
                path=directory,
                name=name,
                framework=FrameworkType.REACT_VITE,
                package_manager=pm,
                dev_script=dev_script,
                config_file="vite.config.ts" if (directory / "vite.config.ts").is_file() else "vite.config.js",
            )

        # 4. Generic Vite (Vue, Svelte, Vanilla)
        if has_vite:
            return ProjectInfo(
                path=directory,
                name=name,
                framework=FrameworkType.GENERIC_VITE,
                package_manager=pm,
                dev_script=dev_script,
            )

        # 5. Generic Web project with scripts
        if "start" in scripts or "dev" in scripts or (directory / "index.html").is_file():
            return ProjectInfo(
                path=directory,
                name=name,
                framework=FrameworkType.STATIC_WEB,
                package_manager=pm,
                dev_script=dev_script,
                entry_file="index.html",
            )

        return ProjectInfo(
            path=directory,
            name=name,
            framework=FrameworkType.UNKNOWN,
            package_manager=pm,
            dev_script=dev_script,
        )

    @classmethod
    def _detect_flutter(cls, directory: Path) -> ProjectInfo:
        # Check project name in pubspec.yaml
        name = directory.name
        try:
            with open(directory / "pubspec.yaml", "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("name:"):
                        name = line.split(":", 1)[1].strip()
                        break
        except Exception:
            pass

        return ProjectInfo(
            path=directory,
            name=name,
            framework=FrameworkType.FLUTTER_WEB,
            entry_file="lib/main.dart",
        )
