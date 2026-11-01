"""Accurate Apple iPhone device display presets and geometry profiles."""

from __future__ import annotations

from openios.live_preview.core.models import (
    DeviceProfile,
    DynamicIslandSpec,
    HomeIndicatorSpec,
    SafeAreaInsets,
)

# Reference B Target Profile: iPhone 12 Pro Max with Apple Notch
IPHONE_12_PRO_MAX = DeviceProfile(
    id="iphone-12-pro-max",
    name="iPhone 12 Pro Max",
    logical_width=428,
    logical_height=926,
    scale_factor=3.0,
    screen_corner_radius=44,
    bezel_thickness=11,
    safe_area_portrait=SafeAreaInsets(top=47, bottom=34, left=0, right=0),
    safe_area_landscape=SafeAreaInsets(top=0, bottom=21, left=47, right=47),
    dynamic_island=DynamicIslandSpec(width=124, height=36, top_offset=12, corner_radius=18),
    home_indicator=HomeIndicatorSpec(width=134, height=5, bottom_offset=8, corner_radius=2.5),
    cutout_type="notch",
    notch_width=160,
    notch_height=28,
    notch_corner_radius=11,
    chassis_color="#18191c",
    accent_color="#2c2d32",
)

IPHONE_14_PRO_MAX = DeviceProfile(
    id="iphone-14-pro-max",
    name="iPhone 14 Pro Max",
    logical_width=430,
    logical_height=932,
    scale_factor=3.0,
    screen_corner_radius=52,
    bezel_thickness=11,
    safe_area_portrait=SafeAreaInsets(top=59, bottom=34, left=0, right=0),
    safe_area_landscape=SafeAreaInsets(top=0, bottom=21, left=59, right=59),
    dynamic_island=DynamicIslandSpec(width=124, height=36, top_offset=12, corner_radius=18),
    home_indicator=HomeIndicatorSpec(width=134, height=5, bottom_offset=8, corner_radius=2.5),
    cutout_type="island",
    chassis_color="#18191c",
    accent_color="#2c2d32",
)

IPHONE_15 = DeviceProfile(
    id="iphone-15",
    name="iPhone 15",
    logical_width=393,
    logical_height=852,
    scale_factor=3.0,
    screen_corner_radius=47,
    bezel_thickness=11,
    safe_area_portrait=SafeAreaInsets(top=59, bottom=34, left=0, right=0),
    safe_area_landscape=SafeAreaInsets(top=0, bottom=21, left=59, right=59),
    dynamic_island=DynamicIslandSpec(width=124, height=36, top_offset=12, corner_radius=18),
    home_indicator=HomeIndicatorSpec(width=134, height=5, bottom_offset=8, corner_radius=2.5),
    cutout_type="island",
    chassis_color="#18191c",
    accent_color="#2c2d32",
)

IPHONE_15_PRO_MAX = DeviceProfile(
    id="iphone-15-pro-max",
    name="iPhone 15 Pro Max",
    logical_width=430,
    logical_height=932,
    scale_factor=3.0,
    screen_corner_radius=52,
    bezel_thickness=10,
    safe_area_portrait=SafeAreaInsets(top=59, bottom=34, left=0, right=0),
    safe_area_landscape=SafeAreaInsets(top=0, bottom=21, left=59, right=59),
    dynamic_island=DynamicIslandSpec(width=124, height=36, top_offset=12, corner_radius=18),
    home_indicator=HomeIndicatorSpec(width=134, height=5, bottom_offset=8, corner_radius=2.5),
    cutout_type="island",
    chassis_color="#18191c",
    accent_color="#2c2d32",
)

DEFAULT_DEVICE_ID = "iphone-12-pro-max"
