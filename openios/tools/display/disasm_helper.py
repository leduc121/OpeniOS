#!/usr/bin/env python3
"""Disassemble code directly from bootkc using llvm-mc."""

import struct
import subprocess
import sys
from pathlib import Path

ROOT_SEGMENTS = [
    (0xfffffff007004000, 0x8000, 0x0),
    (0xfffffff00700c000, 0xa84000, 0x8000),
    (0xfffffff007a90000, 0x510000, 0xa8c000),
    (0xfffffff007fa0000, 0x3c000, 0xf9c000),
    (0xfffffff007fdc000, 0x2628000, 0xfd8000),
    (0xfffffff00a604000, 0x8000, 0x3600000),
    (0xfffffff00a60c000, 0x248000, 0x3608000),
    (0xfffffff00a854000, 0x274000, 0x3850000),
    (0xfffffff00aac8000, 0xb4000, 0x3ac4000),
]

def vm_to_fileoff(vmaddr: int) -> int:
    for start, size, fileoff in ROOT_SEGMENTS:
        if start <= vmaddr < start + size:
            return fileoff + (vmaddr - start)
    raise ValueError(f"Address 0x{vmaddr:x} not in known root segments")

def disassemble_range(bootkc_path: Path, start_addr: int, num_instructions: int):
    with open(bootkc_path, "rb") as f:
        fileoff = vm_to_fileoff(start_addr)
        f.seek(fileoff)
        raw_bytes = f.read(num_instructions * 4)

    # Format bytes for llvm-mc: "0xXX 0xXX 0xXX 0xXX\n" per instruction
    hex_lines = []
    for i in range(0, len(raw_bytes), 4):
        chunk = raw_bytes[i:i+4]
        if len(chunk) < 4:
            break
        hex_lines.append(" ".join(f"0x{b:02x}" for b in chunk))

    input_text = "\n".join(hex_lines) + "\n"
    res = subprocess.run(
        ["llvm-mc", "--disassemble", "-triple=arm64e"],
        input=input_text,
        capture_output=True,
        text=True,
    )
    
    asm_lines = [l.strip() for l in res.stdout.strip().split("\n")] if res.stdout.strip() else []
    
    for i, hex_line in enumerate(hex_lines):
        addr = start_addr + i * 4
        asm = asm_lines[i] if i < len(asm_lines) else "<unknown/data>"
        raw = raw_bytes[i*4 : i*4+4]
        raw_hex = "".join(f"{b:02x}" for b in reversed(raw))
        print(f"0x{addr:x}:  {raw_hex:8s}  {asm}")

if __name__ == "__main__":
    bootkc = Path("openios/firmware/linux/iphone15-3-26.6/boot/bootkc")
    addr = int(sys.argv[1], 16) if len(sys.argv) > 1 else 0xfffffff0080d5910
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    disassemble_range(bootkc, addr, count)
