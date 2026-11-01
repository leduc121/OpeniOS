"""Core data models and enums for OpeniOS Live Preview."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class BackendType(str, Enum):
    """Execution backend selection."""
    LIVE_PREVIEW = "LIVE_PREVIEW"
    NATIVE_EMULATOR = "NATIVE_EMULATOR"

    def label(self) -> str:
        if self == BackendType.LIVE_PREVIEW:
            return "Live Preview (Web Engine)"
        return "Native Emulator (QEMU-SPTM)"

    def description(self) -> str:
        if self == BackendType.LIVE_PREVIEW:
            return "Native Ubuntu window with embedded WebKit engine and dev-server HMR."
        return "Experimental QEMU-SPTM Darwin guest VM (firmware research mode)."


class Orientation(str, Enum):
    PORTRAIT = "PORTRAIT"
    LANDSCAPE = "LANDSCAPE"

    def toggle(self) -> Orientation:
        return Orientation.LANDSCAPE if self == Orientation.PORTRAIT else Orientation.PORTRAIT


class ServerState(str, Enum):
    STOPPED = "STOPPED"
    STARTING = "STARTING"
    READY = "READY"
    ERROR = "ERROR"


class FrameworkType(str, Enum):
    REACT_VITE = "REACT_VITE"
    GENERIC_VITE = "GENERIC_VITE"
    EXPO_WEB = "EXPO_WEB"
    FLUTTER_WEB = "FLUTTER_WEB"
    NEXTJS = "NEXTJS"
    STATIC_WEB = "STATIC_WEB"
    UNKNOWN = "UNKNOWN"

    def display_name(self) -> str:
        names = {
            FrameworkType.REACT_VITE: "React + Vite",
            FrameworkType.GENERIC_VITE: "Vite (Generic)",
            FrameworkType.EXPO_WEB: "Expo Web",
            FrameworkType.FLUTTER_WEB: "Flutter Web",
            FrameworkType.NEXTJS: "Next.js",
            FrameworkType.STATIC_WEB: "Static HTML/CSS/JS",
            FrameworkType.UNKNOWN: "Unknown Project",
        }
        return names.get(self, "Unknown")


@dataclass(frozen=True)
class SafeAreaInsets:
    """Safe area insets in logical viewport points."""
    top: int
    bottom: int
    left: int
    right: int


@dataclass(frozen=True)
class DynamicIslandSpec:
    """Dynamic Island dimensions and position."""
    width: int
    height: int
    top_offset: int
    corner_radius: int


@dataclass(frozen=True)
class HomeIndicatorSpec:
    """Home Indicator dimensions and position."""
    width: int
    height: int
    bottom_offset: int
    corner_radius: int


@dataclass(frozen=True)
class DeviceProfile:
    """Hardware device display profile and geometric characteristics."""
    id: str
    name: str
    logical_width: int
    logical_height: int
    scale_factor: float
    screen_corner_radius: int
    bezel_thickness: int
    safe_area_portrait: SafeAreaInsets
    safe_area_landscape: SafeAreaInsets
    dynamic_island: DynamicIslandSpec
    home_indicator: HomeIndicatorSpec
    cutout_type: str = "notch"  # "notch" or "island"
    notch_width: int = 160
    notch_height: int = 28
    notch_corner_radius: int = 11
    chassis_color: str = "#18191c"  # Dark Graphite
    accent_color: str = "#2c2d32"

    def get_viewport_dimensions(self, orientation: Orientation) -> tuple[int, int]:
        """Return (width, height) in logical points for given orientation."""
        if orientation == Orientation.PORTRAIT:
            return (self.logical_width, self.logical_height)
        return (self.logical_height, self.logical_width)

    def get_safe_area(self, orientation: Orientation) -> SafeAreaInsets:
        if orientation == Orientation.PORTRAIT:
            return self.safe_area_portrait
        return self.safe_area_landscape


@dataclass
class ProjectInfo:
    """Local project metadata detected from directory structure."""
    path: Path
    name: str
    framework: FrameworkType
    package_manager: str = "npm"
    dev_script: str = "dev"
    entry_file: Optional[str] = None
    config_file: Optional[str] = None
    env_vars: dict[str, str] = field(default_factory=dict)
    custom_port: Optional[int] = None
