# OpeniOS accelerated display sprint report

## Executive result

This sprint preserved the M1 root shell, the M2.2 host diagnostic console, and
the M2.3a bounded MMIO observer. It also added an opt-in research device that
copies XRGB8888 pixels from guest physical RAM into a QEMU DisplaySurface.

The new path produced a verified 320x180 four-color screendump from bytes in
guest RAM. This is a controlled guest-memory-driven diagnostic, not output
from an iOS display driver. The iOS restore boot still generated no observed
accesses to the selected display MMIO ranges, and no iOS/SpringBoard pixels
were observed.

## Baseline and source preservation

The parent branch is `openios/display-research`. QEMU-SPTM 11.1.0 remains at
`bad6336fb24211f8c4e8e946c259bd5b12417340`. At sprint start the parent tree
was clean at the committed M2.3a baseline, while the ignored nested QEMU tree
contained the changes represented by patches 0001 and 0002.

Patch 0003 now preserves the guest-memory framebuffer. The application script
was tested twice on a detached clean worktree: all three patches applied on
the first run and the second run correctly reported that the series was
already applied. No reset, clean, firmware write, or stable-branch change was
performed.

Apply the complete series with:

```sh
openios/tools/qemu/apply-sptm-patches.sh
```

## Display MMIO findings

The optional `display-mmio-trace=on` observer remains in QEMU's unassigned
memory dispatch. It does not install fake register ranges or change the
pre-existing unassigned read behavior. It covers 19 Device Tree-derived
physical ranges belonging to `disp0`, `dcp`, `dart-disp0`, `dart-dcp`,
`dart-dispgrt`, `scaler0`, and `gfx-asc` and limits detailed output to 256
records while retaining aggregate counters.

With the known-good M1 boot arguments, the combined test
`test-display=on,display-mmio-trace=on` reached `bash-5.3#`. The final trace was:

```text
openios-display-mmio: summary reads=0 writes=0 detailed=0/256
```

Every one of the 19 per-range counters was zero. Earlier M2.3a testing proved
the observer operational by using the QEMU monitor to read `0x230000000`,
which produced one `disp0.0` record. Therefore the current result means no
matching unassigned access was observed during this restore boot; it does not
mean tracing was inactive.

`AppleARMBacklight` did start, but reported `no backlight enable function` and
`no backlight update function`. That activity did not result in a selected
display MMIO access.

## T8030 versus T8120 compatibility matrix

The Inferno implementation is useful as architectural reference, but its
register behavior is not evidence of T8120 compatibility.

| Area | Inferno T8030 implementation | D74AP/T8120 evidence | Decision |
| --- | --- | --- | --- |
| QEMU console and pixman presentation | Uses a QEMU graphics console and pixman images | Host APIs are platform-independent | Reuse the API pattern |
| Frame acquisition | Reads configured layer data through a DART-backed DMA AddressSpace | T8120 has DART mappers, but mappings and stream behavior are not yet observed | Reuse only after T8120 DART evidence |
| Pixel formats | Implements inferred BGRA/ARGB bit patterns and rejects compression | No T8120 format register writes were observed; AGX commonly uses compressed surfaces | Do not assume these encodings |
| Pipe registers | DisplayTarget5 blocks around control/genpipe/blend offsets | T8120 `disp0` exposes seven regions totaling a different topology | Incompatible/unknown until traced |
| MMIO mapping | Maps one DisplayPipe region using the first `disp0` entry | T8120 has seven `disp0` regions | Do not map T8030 layout blindly |
| Interrupts | Creates nine DisplayPipe IRQ outputs | T8120 also lists nine `disp0` IRQs, but meanings/order are unverified | Count matches; semantics unknown |
| DART | Uses one `mapper-disp0` | T8120 lists `mapper-disp0` reg 0 and `mapper-disp0-piodma` reg 4, plus separate DCP and display-GRT DARTs | T8030 wiring is insufficient |
| DCP | DisplayPipe path does not emulate the T8120 DCP/RTKit stack | T8120 has a separate DCP node, two MMIO regions, four IRQs and `mapper-dcp` reg 5 | Major missing dependency |
| GPU | Not a substitute for AGX command processing | Boot KC contains AGX G15P and RTBuddy identities; `gfx-asc` is not emulated | Major missing dependency |
| Boot splash | Can draw emulator branding independent of guest pixels | No evidence that it represents T8120/iOS output | Never use as guest-graphics proof |

## Guest-memory framebuffer proof of concept

`openios-guest-fb` is a standalone QOM display device. It has no MMIO region,
interrupt, Apple register model, DART, or firmware protocol. Its properties are
`addr`, `width`, `height`, and `stride`; defaults are 320x180 XRGB8888. On a
display refresh it copies each visible row from the configured guest physical
address into a QEMU-owned surface. Dimensions, stride, and address overflow
are validated, and read failures are rate-limited to one diagnostic until a
subsequent successful refresh.

The reproducible smoke test loads a four-quadrant XRGB buffer into RAM on the
generic `virt` machine, captures a monitor screendump, and checks four pixels:

```sh
openios/tools/display/test_guest_fb.sh
```

Result:

```text
PASS: guest RAM produced the expected 320x180 four-color screendump
```

The captured pixels were red `(255,32,32)`, green `(32,255,64)`, blue
`(32,64,255)`, and yellow `(255,224,32)` at the expected coordinates. The PPM
was 320x180 and had SHA-256
`ad1d7f2151a16b3470356f098c63e414d3403283b9e91f464cef1a187281e7c3`.

Evidence levels are deliberately separated:

1. `openios-test-display`: host-generated static diagnostic pattern.
2. `openios-guest-fb`: verified bytes copied from guest physical RAM, seeded
   by the test loader rather than an Apple driver.
3. Actual iOS display output: not achieved and not claimed.

## iOS display-stack readiness

The boot KC contains identifiers and strings for AppleDCP, AppleDCPDPTXProxy,
AppleM2ScalerCSC, AGXG15P, AGX firmware/RTBuddy, AppleCLCD2,
AppleARMBacklight, IOMobileFramebuffer, and related classes. Presence in the
kernel collection does not prove matching, successful start, firmware boot,
or framebuffer production.

The APFS restore ramdisk contains IOMobileFramebuffer and MiniDisplay private
frameworks, but its active `System/Library/LaunchDaemons` directory contains
only `com.jprx.bash.plist`. Nine original restore daemons were moved to
`LaunchDaemons.old`; none is SpringBoard, backboardd, or WindowServer. No such
graphical process was found in the ramdisk listing. The boot log confirms that
launchd starts the Bash service and then exposes the root prompt.

Current blockers are therefore:

- no graphical userspace or SpringBoard/backboardd launch path in the active
  restore environment;
- no T8120 DCP ASC/RTKit firmware transport or DCP protocol implementation;
- no display DART translation path for the multiple T8120 mappers;
- no verified T8120 DisplayPipe register layout, pixel format, timing, or IRQ
  semantics;
- no AGX G15P/GPU firmware execution or compressed-surface handling;
- no guest-produced framebuffer address/stride/format handoff to QEMU.

Firmware and ramdisk inputs were inspected read-only and were not modified.
The release SHA-256 checks for `ramdisk-shell-v5.apfs` and `ramdisk-v5.tc`
passed.

## Build and regression tests

The configured build retains `--disable-werror` because GCC 15 reports the
pre-existing `apple_aic.c` enum-pointer `sscanf` warning. No warning was
suppressed in source. The build used no more than two jobs:

```sh
cd third_party/darwin-vm/qemu-sptm/build
../configure --target-list=aarch64-softmmu --disable-pvg --disable-werror
ninja -j2 qemu-system-aarch64
```

Results:

- QEMU-SPTM 11.1.0 build: pass.
- `openios-guest-fb,help`: pass; all four properties listed.
- Guest-memory framebuffer test: pass with verified pixels.
- Existing 960x540 host test-pattern screendump: pass.
- M1, tracing off and test display off: reached `bash-5.3#`.
- M1, tracing on and test display on: reached `bash-5.3#`; zero selected MMIO
  reads/writes; serial console remained functional.
- Patch apply on clean pinned QEMU and idempotency check: pass.

The working M1 invocation requires the previously verified boot arguments:

```text
rd=md0 serial=3 -v -noprogress wdt=-1 wlan-olyhal-abort
```

Using the newer QEMU source default argument string instead caused the guest's
`recount_track_cpu_kind` integrity check to panic in repeated trials. Restoring
the known M1 argument string returned the boot to `bash-5.3#`. This is a boot
configuration distinction, not evidence of a display-device regression.

## Changed files

Parent OpeniOS repository, currently uncommitted:

- `openios/patches/qemu-sptm/0003-openios-guest-memory-framebuffer.patch`
- `openios/patches/qemu-sptm/series`
- `openios/tools/display/test_guest_fb.sh`
- `openios/docs/display/sprint-report.md`

Ignored nested QEMU tree, reproduced by patch 0003:

- `hw/display/openios-guest-fb.c`
- `hw/display/meson.build`

## Recommended next stage

Use a fuller, legally available iOS boot environment to observe service
matching and DCP/AGX startup while retaining bounded dispatch tracing. First
capture a guest-originated framebuffer descriptor or DART mapping. Then feed
that verified address, dimensions, stride, and format into the research
console before implementing register responses. Only after real T8120 writes
are captured should a minimal DART/DCP or DisplayPipe model be proposed.
