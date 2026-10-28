# M5 AppleASCWrapV6 matching investigation

## Status: PARTIAL — earliest observable boundary identified; exact rejection is not observable in the restore environment

## Question and method

This investigation asks where the T8120 DCP path stops *before* adding a DCP
emulator.  It compares the Boot KC personality, the original and QEMU-fixed
D74AP Device Trees, and bounded serial/MMIO observations.  The known-good M1
assets were not changed.  Experimental Device Trees are generated under
`/tmp` from `dtree.original`.

```sh
python3 openios/tools/display/make_display_probe_dtree.py \
  openios/firmware/linux/iphone15-3-26.6/boot/dtree.original \
  /tmp/openios-m5-dcp-only.dtree \
  --nvram third_party/darwin-vm/nvram.bin --disable-network --enable dcp
```

## Static match requirements

The Boot KC prelink information reports this personality:

| Item | Value |
| --- | --- |
| bundle | `com.apple.driver.AppleA7IOP-ASCWrap-v6` 1.0.2 |
| class | `AppleASCWrapV6` |
| provider | `AppleARMIODevice` |
| `IONameMatch` | `iop,ascwrap-v6`, `iop,ascwrap-v7` |
| direct library dependencies | AppleA7IOP, AppleARMPlatform, IOSlaveProcessor |

It is inspectable without modifying Boot KC:

```sh
openios/tools/display/inspect_bootkc_display.py \
  openios/firmware/linux/iphone15-3-26.6/boot/bootkc
```

The original D74AP `dcp` node supplies the direct name match
`compatible=iop,ascwrap-v6`; it is an `AppleARMIODevice` when published by
AppleARMPE.  It retains two register regions, four interrupts, `iop-version=1`,
clock/power gates `0x184`, and `iommu-parent=mapper-dcp`.  Its child has
`compatible=iop-nub,rtbuddy-v2`, while the separate `dcp0-expert` has
`compatible=dcp-expert-v1`.

The normal QEMU fixup deletes all three unsupported `compatible` values.  The
DCP-only probe restores only those values; it does not modify the registers,
power properties, IOMMU relation, child flags, firmware, QEMU memory map, or
SGX.  This rules out an accidentally altered DT property as an explanation for
the initial personality lookup.

## Runtime evidence

With `io=0xffff`, the DCP-only probe recorded these registrations:

```text
.../AppleT812xIO/dcp@32C00000
.../AppleT812xIO/dcp0-expert@3D2B8044
.../AppleT812xIO/disp0@30000000
.../AppleT812xIO/dart-dcp@3130C000
.../AppleT812xIO/dart-disp0@31304000
.../AppleT812xIO/dart-dispgrt@31350000
```

The same run did **not** record registration of `AppleASCWrapV6`,
`AppleA7IOPNub`, `RTBuddy`, `AppleDCPExpert`, or `AppleCLCD2`.  The optional
unassigned-memory observer was enabled and ended with zero reads and zero
writes in all 19 selected DCP/DART/display ranges.  The probe did not reach
the root shell before its 100-second timeout.  This is a bounded observation,
not a deadlock claim and not an M1 regression result.

The confirmed boundary is therefore:

```text
AppleARMPE publishes the DCP DT nub
    -> no observed AppleASCWrapV6 service registration
    -> no ASC/DART/display unassigned access
```

This proves neither an IOCatalogue mismatch nor a failed `probe()`/`start()`.
Apple's `io=0xffff` output records registration but not every catalogue-match
rejection.  The earliest *specific* runtime condition still missing is an
observable `AppleASCWrapV6` registration (or a kernel match diagnostic that
reports its rejection).  Returning fabricated ASC values would skip this
unresolved boundary and is not justified.

## Why the normal restore shell cannot close the gap

The ramdisk contains `/usr/sbin/ioreg`, but a direct normal-M1 boot attempt
fails before it can inspect the registry:

```text
dyld: Library not loaded: /usr/lib/libncurses.5.4.dylib
Reason: ... no dyld cache
```

`/sbin/kextstat` and `/usr/bin/grep` are absent.  Thus an IORegistry query from
the shell is not an available source of truth; the failure reflects the minimal
restore filesystem, not absence of DCP services.  Capturing registry data next
requires either an early-kernel logging path or a complete, correctly booted
System/Cryptex userspace.

## DART-only probe

The previous DART-only probe did not print serial output before 45 seconds.
It has no positive MMIO evidence and does not prove a deadlock.  The M5
DCP-only/`io=0xffff` experiment likewise must not be generalized to a DART
failure: it restores no DART compatible property and only demonstrates that
the DCP probe cannot reach an ASC access in that bounded window.

## Next targeted diagnostic

Use a kernel-side, opt-in instrumentation point only if it can log an
IOCatalogue candidate name, provider class, and match/probe result without
changing the returned result.  Its acceptance criterion is one of:

1. a recorded candidate/rejection for `AppleASCWrapV6`; or
2. registration of `AppleASCWrapV6` and a first ASC/DART access.

Until then, the correct M5 implementation is diagnostic only; no QEMU DCP
register or RTKit response was added.
