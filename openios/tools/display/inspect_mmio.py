#!/usr/bin/env python3
import base64
import json
import struct
from pathlib import Path

path = Path("openios/docs/boot/d74ap-patched.json")
data = json.loads(path.read_text())

arm = next(
    item["arm-io"]
    for item in data["device-tree"]["children"]
    if "arm-io" in item
)

ranges_raw = base64.b64decode(arm["ranges"])
if len(ranges_raw) % 8:
    raise ValueError("arm-io/ranges is not uint64-aligned")

ranges = struct.unpack("<" + "Q" * (len(ranges_raw) // 8), ranges_raw)

print("=== ARM-IO ranges ===")
for i, value in enumerate(ranges):
    print(f"ranges[{i}] = 0x{value:016X}")

assert ranges[0] == 0, "Unexpected ARM-IO ranges format"

# Matches IO_RANGE_BASE_OFFSET=1 in QEMU-SPTM darwin.c.
iobase = ranges[1]
print(f"\nARM-IO physical base: 0x{iobase:X}")

targets = (
    "disp0", "dcp", "dart-disp0",
    "dart-dcp", "dart-dispgrt",
    "scaler0", "gfx-asc"
)

print("\n=== Physical MMIO map ===")

for item in arm["children"]:
    for name in targets:
        if name not in item:
            continue

        node = item[name]
        regs = node.get("reg", [])
        if isinstance(regs, dict):
            regs = [regs]

        print(f"\n{name}")

        for index, reg in enumerate(regs):
            if not isinstance(reg, dict):
                continue
            addr = reg.get("addr", 0)
            size = reg.get("size", 0)
            print(
                f"  MMIO[{index}] "
                f"offset=0x{addr:X} "
                f"physical=0x{iobase + addr:X} "
                f"size=0x{size:X}"
            )

        print("  IRQ:", node.get("interrupts", []))
