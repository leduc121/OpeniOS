#!/usr/bin/env python3
"""Report display-related personalities embedded in an Apple Boot KC."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import plistlib


BUNDLES = (
    "com.apple.driver.AppleA7IOP-ASCWrap-v6",
    "com.apple.driver.RTBuddy",
    "com.apple.driver.AppleDCP",
    "com.apple.driver.AppleT8110DART",
    "com.apple.driver.AppleMobileDispH15P-DCP",
    "com.apple.iokit.IOMobileGraphicsFamily",
    "com.apple.iokit.IOMobileGraphicsFamily-DCP",
    "com.apple.AGXG15P",
)


def prelink_entries(data: bytes) -> list[dict]:
    offset = 0
    while True:
        start = data.find(b"<?xml", offset)
        if start < 0:
            break
        end = data.find(b"</plist>", start)
        if end < 0:
            break
        offset = start + 5
        try:
            value = plistlib.loads(data[start : end + len(b"</plist>")])
        except Exception:
            continue
        if isinstance(value, dict) and isinstance(value.get("_PrelinkInfoDictionary"), list):
            return value["_PrelinkInfoDictionary"]
    raise ValueError("no _PrelinkInfoDictionary plist found")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bootkc", type=Path)
    args = parser.parse_args()

    entries = prelink_entries(args.bootkc.read_bytes())
    by_id = {entry.get("CFBundleIdentifier"): entry for entry in entries}
    result = []
    for bundle_id in BUNDLES:
        entry = by_id.get(bundle_id)
        item = {"bundle": bundle_id, "present": entry is not None}
        if entry is not None:
            item.update(
                {
                    "version": entry.get("CFBundleVersion"),
                    "os_bundle_required": entry.get("OSBundleRequired"),
                    "bundle_path": entry.get("_PrelinkBundlePath"),
                    "libraries": entry.get("OSBundleLibraries", {}),
                    "personalities": entry.get("IOKitPersonalities", {}),
                }
            )
        result.append(item)

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
