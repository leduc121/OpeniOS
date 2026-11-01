"""Unit tests for device profiles and registry."""

import unittest
from openios.live_preview.core.models import Orientation
from openios.live_preview.devices.registry import device_registry
from openios.live_preview.devices.profiles import (
    IPHONE_14_PRO_MAX,
    IPHONE_15,
    IPHONE_15_PRO_MAX,
)


class TestDeviceProfiles(unittest.TestCase):
    def test_default_device(self) -> None:
        default_dev = device_registry.get_or_default()
        self.assertEqual(default_dev.id, "iphone-12-pro-max")
        self.assertEqual(default_dev.logical_width, 428)
        self.assertEqual(default_dev.logical_height, 926)
        self.assertEqual(default_dev.scale_factor, 3.0)
        self.assertEqual(default_dev.cutout_type, "notch")

    def test_registered_profiles(self) -> None:
        ids = device_registry.list_ids()
        self.assertIn("iphone-12-pro-max", ids)
        self.assertIn("iphone-14-pro-max", ids)
        self.assertIn("iphone-15", ids)
        self.assertIn("iphone-15-pro-max", ids)

    def test_orientation_dimensions(self) -> None:
        dev = IPHONE_14_PRO_MAX
        pw, ph = dev.get_viewport_dimensions(Orientation.PORTRAIT)
        self.assertEqual((pw, ph), (430, 932))

        lw, lh = dev.get_viewport_dimensions(Orientation.LANDSCAPE)
        self.assertEqual((lw, lh), (932, 430))

    def test_safe_areas(self) -> None:
        dev = IPHONE_15
        sa_port = dev.get_safe_area(Orientation.PORTRAIT)
        self.assertEqual(sa_port.top, 59)
        self.assertEqual(sa_port.bottom, 34)

        sa_land = dev.get_safe_area(Orientation.LANDSCAPE)
        self.assertEqual(sa_land.top, 0)
        self.assertEqual(sa_land.left, 59)


if __name__ == "__main__":
    unittest.main()
