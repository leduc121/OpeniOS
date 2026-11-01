"""Base framework adapter interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
from openios.live_preview.core.models import FrameworkType, ProjectInfo
from openios.live_preview.core.process_manager import ProcessManager


class BaseFrameworkAdapter(ABC):
    """Abstract base class for framework live preview dev-server adapters."""

    @property
    @abstractmethod
    def framework_type(self) -> FrameworkType:
        """The framework type handled by this adapter."""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable framework name."""
        pass

    @property
    def supports_hmr(self) -> bool:
        """Whether this adapter natively supports Hot Module Reloading."""
        return True

    @abstractmethod
    def detect(self, project_path: Path) -> bool:
        """Check if this project directory matches this framework."""
        pass

    @abstractmethod
    def validate(self, project_path: Path) -> tuple[bool, str]:
        """Validate dependencies and environment before launching."""
        pass

    @abstractmethod
    def start(self, project: ProjectInfo, process_mgr: ProcessManager) -> bool:
        """Launch the dev server via the process manager."""
        pass

    def reload(self, process_mgr: ProcessManager) -> None:
        """Trigger dev server reload if supported."""
        pass

    def stop(self, process_mgr: ProcessManager) -> None:
        """Stop the running dev server."""
        process_mgr.stop_process()
