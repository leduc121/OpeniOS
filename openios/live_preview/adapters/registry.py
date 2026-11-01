"""Registry and factory for framework adapters."""

from __future__ import annotations

from pathlib import Path
from typing import Optional
from openios.live_preview.adapters.base import BaseFrameworkAdapter
from openios.live_preview.adapters.expo_web import ExpoWebAdapter
from openios.live_preview.adapters.flutter_web import FlutterWebAdapter
from openios.live_preview.adapters.static_web import StaticWebAdapter
from openios.live_preview.adapters.vite_react import ViteReactAdapter
from openios.live_preview.core.models import FrameworkType, ProjectInfo


class AdapterRegistry:
    """Manages supported framework adapters in priority order."""

    def __init__(self) -> None:
        self._adapters: list[BaseFrameworkAdapter] = [
            ViteReactAdapter(),
            ExpoWebAdapter(),
            FlutterWebAdapter(),
            StaticWebAdapter(),
        ]

    def find_adapter(self, project: ProjectInfo) -> Optional[BaseFrameworkAdapter]:
        # Match by explicit framework type first
        for adapter in self._adapters:
            if adapter.framework_type == project.framework:
                return adapter

        # Fallback: check detect() on path
        for adapter in self._adapters:
            if adapter.detect(project.path):
                return adapter

        return None

    def find_for_path(self, project_path: Path) -> Optional[BaseFrameworkAdapter]:
        for adapter in self._adapters:
            if adapter.detect(project_path):
                return adapter
        return None


adapter_registry = AdapterRegistry()
