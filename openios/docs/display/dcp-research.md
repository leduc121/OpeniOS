# DCP, RTKit, DART, and T8120 research (M3)

## Scope and conclusion

Open-source Apple Silicon work provides concrete evidence for the architecture
and portions of the protocol: DCP is an ASC coprocessor, RTKit negotiates
shared memory, AFK/EPIC discovers services, DART supplies I/O virtual address
translation, and a display service accepts mode and surface/swap commands.

That evidence is sufficient to define staged experiments.  It is not proof
that a Mac M1/M2 register layout or every message payload is compatible with
the iPhone T8120 DCP.  OpeniOS should first reproduce the ASC/RTKit transport
and identify the service/version advertised by the actual D74AP firmware.  It
should not copy T8030 DisplayPipe registers or invent successful replies.

## Primary implementation evidence

The inspected Asahi `m1n1` revision was
`33c235dda271a2fc48abd9cceea4df27bfaebed4`.

- [`src/dcp.c`](https://github.com/AsahiLinux/m1n1/blob/33c235dda271a2fc48abd9cceea4df27bfaebed4/src/dcp.c)
  obtains DCP/display DART parameters from ADT, creates firmware segment
  mappings, initializes the ASC, boots RTKit, and then starts AFK/EPIC.
- [`src/rtkit.h`](https://github.com/AsahiLinux/m1n1/blob/33c235dda271a2fc48abd9cceea4df27bfaebed4/src/rtkit.h)
  exposes endpoint messages consisting of an endpoint number and 64-bit
  payload, plus shared-memory map/allocation operations.
- [`src/afk.c`](https://github.com/AsahiLinux/m1n1/blob/33c235dda271a2fc48abd9cceea4df27bfaebed4/src/afk.c)
  implements ring-buffer setup, endpoint startup, service announcement and
  command transport for AFK/EPIC.
- [`src/dcp_iboot.c`](https://github.com/AsahiLinux/m1n1/blob/33c235dda271a2fc48abd9cceea4df27bfaebed4/src/dcp_iboot.c)
  documents one concrete service, `disp0-service`, on endpoint `0x23`, with
  0x4000-byte TX/RX buffers.
- [`proxyclient/experiments/dcp.py`](https://github.com/AsahiLinux/m1n1/blob/33c235dda271a2fc48abd9cceea4df27bfaebed4/proxyclient/experiments/dcp.py)
  initializes both DCP and display DARTs, maps a framebuffer through the
  display DART, and submits it through the DCP swap path.

The Linux Apple mailbox driver documents the underlying ASC hardware as
AP-to-IOP and IOP-to-AP FIFOs carrying a 64-bit message plus 32-bit endpoint:
[`drivers/soc/apple/mailbox.c`](https://github.com/torvalds/linux/blob/master/drivers/soc/apple/mailbox.c).
Asahi's overview likewise describes DCP as a coprocessor protocol built over
RTKit/EPIC rather than a simple framebuffer register block:
[`Display controllers`](https://asahilinux.org/docs/hw/soc/display-controllers/)
and its [RTKit/EPIC progress report](https://asahilinux.org/2026/06/progress-report-7-1/).

## Concrete observed protocol surface

The `m1n1` iBoot-oriented DCP service assigns the following command numbers:

| Command | Number |
| --- | ---: |
| set surface | 1 |
| set power | 2 |
| get hot-plug state | 3 |
| get timing modes | 4 |
| get color modes | 5 |
| set mode | 6 |
| swap begin | 15 |
| swap set layer | 16 |
| swap end | 18 |

These numbers are implementation evidence for the inspected Apple Silicon
firmware family.  OpeniOS must discover the T8120 service and version before
treating them as compatible.  A successful transport handshake, not a
hard-coded success response, is the acceptance criterion.

## Firmware and memory prerequisites

The D74AP Device Tree exposes a DCP ASC wrapper, an RTBuddy nub, DCP firmware
segment metadata, DCP and display DART mappers, shared-memory regions, and
interrupts.  The Boot KC supplies AppleDCP and AppleCLCD2 personalities which
expect those providers.  The normal QEMU fixup strips their compatible
properties because QEMU does not emulate them.

A minimal research implementation therefore needs this order:

1. Map the DCP ASC mailbox registers and IRQs at Device Tree-derived addresses.
2. Load only the DCP firmware segments described by the matching assets; do not
   substitute host-generated firmware state.
3. Implement the RTKit hello/version and shared-memory negotiation actually
   observed from that firmware.
4. Implement enough DCP DART translation for firmware and ring buffers.
5. Discover AFK/EPIC services and record their announced names and versions.
6. Only then model the specific display commands observed from the guest and
   firmware, followed by display-DART surface mapping.

The existing dispatch tracer should remain active around every stage.  A new
stage is justified only by a captured access or protocol transition.

## T8120 compatibility assessment

| Area | Evidence | T8120 status |
| --- | --- | --- |
| ASC mailbox FIFO model | Mainline Linux Apple mailbox driver; ADT ASC wrapper | Architecturally plausible; exact offsets/IRQ wiring must come from D74AP ADT and accesses |
| RTKit endpoint transport | `m1n1` and Apple RTKit ecosystem | Likely required; negotiated version unknown |
| AFK/EPIC service discovery | `m1n1` DCP implementation | Likely required; service names/versions must be observed |
| DCP firmware | D74AP metadata and DCP node exist | Required; loading/boot sequence not yet observed in QEMU |
| DCP DART | D74AP `mapper-dcp` stream 5 | Required; translation behavior unimplemented |
| Display DART | `mapper-disp0` stream 0 and PIODMA stream 4 | Required for surfaces; multi-mapper behavior unknown |
| `disp0-service` endpoint 0x23 | Concrete `m1n1` implementation | Candidate only, not yet verified on T8120 |
| Surface/swap command numbers | Concrete `m1n1` implementation | Candidate only; payload ABI/version unverified |
| T8030 DisplayPipe v4 registers | Inferno reference implementation | Not evidence of T8120 compatibility; do not reuse blindly |
| AGX G15P | Boot KC and original `gpu,t8120` match | Separate major dependency; intentionally disabled in current probes |

## Current experimental evidence

Restoring only the DCP ASC/RTBuddy/expert compatible properties on a generated
Device Tree copy still reached the restore root shell.  It produced no DCP
mailbox/DART/display access in the 19 bounded ranges and no serial evidence of
AppleDCP or RTKit initialization.  Restoring only `disp0,t8120` behaved the
same way.  A DART-only probe did not produce serial output or reach the shell
within 45 seconds, while also producing zero selected MMIO accesses.  That
negative result is consistent with an early provider/resource wait, but does
not locate it.  Together these results establish that matching strings alone
are insufficient; they do not establish that the embedded drivers are
incompatible.

The most likely missing layers are provider publication and power resources,
ASC firmware boot, mapper services, and endpoint discovery.  Runtime IOKit
matching evidence is needed to order these precisely.

## Recommended M3 follow-up

1. Add opt-in diagnostics around IOKit personality matching/provider waits,
   preferably through existing kernel logging controls before changing QEMU.
2. Decode all D74AP DCP firmware segment and mailbox properties and correlate
   them with `m1n1` structures without assigning semantics to unknown fields.
3. Implement a standalone, bounded ASC mailbox trace/shim only when actual
   firmware loading can be reproduced.  Initially log and reject unsupported
   protocol states rather than returning success.
4. Implement DCP DART translation sufficient for firmware/ring shared memory,
   then require a real RTKit hello and service announcement.
5. Keep AGX disabled until IOMobileFramebuffer/DCP reaches a documented wait
   on GPU services.  SpringBoard is a later userspace milestone, not a DCP
   emulator test pattern.

No new QEMU hardware behavior was added during this audit.  The existing host
pattern and guest-RAM diagnostic remain explicitly non-iOS output.
