"""Registry of available device profiles for OpeniOS Simulator."""

from __future__ import annotations

from typing import Optional
from openios.live_preview.core.models import DeviceProfile
from openios.live_preview.devices.profiles import (
    DEFAULT_DEVICE_ID,
    IPHONE_12_PRO_MAX,
    IPHONE_14_PRO_MAX,
    IPHONE_15,
    IPHONE_15_PRO_MAX,
)


class DeviceRegistry:
    """Manages verified device hardware profiles."""

    def __init__(self) -> None:
        self._profiles: dict[str, DeviceProfile] = {}
        self.register(IPHONE_12_PRO_MAX)
        self.register(IPHONE_14_PRO_MAX)
        self.register(IPHONE_15)
        self.register(IPHONE_15_PRO_MAX)

    def register(self, profile: DeviceProfile) -> None:
        self._profiles[profile.id] = profile

    def get(self, device_id: str) -> Optional[DeviceProfile]:
        return self._profiles.get(device_id)

    def get_or_default(self, device_id: Optional[str] = None) -> DeviceProfile:
        if device_id and device_id in self._profiles:
            return self._profiles[device_id]
        return self._profiles[DEFAULT_DEVICE_ID]

    def all_profiles(self) -> list[DeviceProfile]:
        return list(self._profiles.values())

    def list_ids(self) -> list[str]:
        return list(self._profiles.keys())


# Singleton instance
device_registry = DeviceRegistry()
