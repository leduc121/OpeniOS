# Feasibility notes (Milestone 0) - DRAFT

Only items marked VERIFIED were checked against source or real output.

## Host
- VERIFIED: AMD Ryzen 5 5500U (6C/12T), x86-64, Ubuntu, 14 GiB RAM, 4 GiB swap.
- VERIFIED: no ARM64 hardware virtualization; guest runs under QEMU TCG (slow).

## Upstream state
- VERIFIED (source): Inferno has hw/arm/apple-silicon/{t8030.c, s8000.c}; no T8120 file.
- CLAIMED (darwin-vm README, not yet reproduced here): A16/t8120 boots to a root shell
  on iOS 26.6/27.0 using its own fork, qemu-sptm. No screen/GUI/SpringBoard.
- CLAIMED (Inferno-iOS README): iPhone 11 guest on iOS 14 shows SpringBoard.
- VERIFIED (darwin-vm scripts): firmware preparation uses macOS-only tools (hdiutil, codesign).

## Open questions
- Does darwin-vm work for iPhone15,3 (iPhone 14 Pro Max), not only iPhone15,4?
- Can ramdisk preparation be done on Linux (APFS write access, code signing)?
- Can a graphical guest be reached on A16 (display controller, GPU dependency)?

## Build status
- Inferno baseline: NOT YET BUILT
- qemu-sptm baseline: NOT YET BUILT
