#!/usr/bin/env python3
"""Print a read-only, dependency-free summary of a 64-bit Mach-O DCP image."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys


MH_MAGIC_64 = 0xFEEDFACF
LC_SEGMENT_64 = 0x19
LC_CODE_SIGNATURE = 0x1D
LC_MAIN = 0x80000028
LC_UNIXTHREAD = 0x5


def name(raw: bytes) -> str:
    return raw.split(b"\0", 1)[0].decode("ascii", "replace")


def inspect(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    if len(data) < 32:
        raise ValueError("file is shorter than a Mach-O 64 header")
    magic, cpu_type, cpu_subtype, file_type, ncmds, sizeofcmds, flags, reserved = (
        struct.unpack_from("<IiiIIIII", data)
    )
    if magic != MH_MAGIC_64:
        raise ValueError(f"not little-endian Mach-O 64: magic={magic:#x}")
    if 32 + sizeofcmds > len(data):
        raise ValueError("load-command region exceeds file")

    result: dict[str, object] = {
        "path": str(path),
        "sha256": hashlib.sha256(data).hexdigest(),
        "size": len(data),
        "cpu_type": cpu_type,
        "cpu_subtype": cpu_subtype,
        "file_type": file_type,
        "ncmds": ncmds,
        "sizeofcmds": sizeofcmds,
        "flags": flags,
        "reserved": reserved,
        "segments": [],
        "code_signature": None,
        "entry_point": None,
        "has_unixthread": False,
        "other_load_commands": [],
    }
    offset = 32
    for _ in range(ncmds):
        if offset + 8 > len(data):
            raise ValueError("truncated load command")
        command, command_size = struct.unpack_from("<II", data, offset)
        if command_size < 8 or offset + command_size > len(data):
            raise ValueError("invalid load-command size")
        if command == LC_SEGMENT_64:
            if command_size < 72:
                raise ValueError("truncated LC_SEGMENT_64")
            raw = struct.unpack_from("<II16sQQQQiiII", data, offset)
            _, _, segname, vmaddr, vmsize, fileoff, filesize, maxprot, initprot, nsects, segflags = raw
            result["segments"].append({
                "name": name(segname),
                "vmaddr": f"{vmaddr:#x}",
                "vmsize": f"{vmsize:#x}",
                "fileoff": f"{fileoff:#x}",
                "filesize": f"{filesize:#x}",
                "maxprot": maxprot,
                "initprot": initprot,
                "nsects": nsects,
                "flags": segflags,
            })
        elif command == LC_CODE_SIGNATURE:
            if command_size < 16:
                raise ValueError("truncated LC_CODE_SIGNATURE")
            _, _, dataoff, datasize = struct.unpack_from("<IIII", data, offset)
            result["code_signature"] = {
                "fileoff": f"{dataoff:#x}",
                "size": f"{datasize:#x}",
                "within_file": dataoff + datasize <= len(data),
            }
        elif command == LC_MAIN:
            if command_size < 24:
                raise ValueError("truncated LC_MAIN")
            _, _, entryoff, stacksize = struct.unpack_from("<IIQQ", data, offset)
            result["entry_point"] = {
                "kind": "LC_MAIN",
                "fileoff": f"{entryoff:#x}",
                "stacksize": f"{stacksize:#x}",
            }
        elif command == LC_UNIXTHREAD:
            result["has_unixthread"] = True
            # arm64_thread_state64 has x[29], fp, lr, sp, pc, cpsr and pad.
            # The command starts with a flavor/count pair before that state.
            if command_size >= 16 + 272:
                flavor, count = struct.unpack_from("<II", data, offset + 8)
                state = offset + 16
                sp, pc = struct.unpack_from("<QQ", data, state + 256)
                result["entry_point"] = {
                    "kind": "LC_UNIXTHREAD",
                    "flavor": flavor,
                    "count": count,
                    "pc": f"{pc:#x}",
                    "sp": f"{sp:#x}",
                }
        else:
            result["other_load_commands"].append({
                "command": f"{command:#x}", "size": command_size
            })
        offset += command_size
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(inspect(args.image), indent=2, sort_keys=True))
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
