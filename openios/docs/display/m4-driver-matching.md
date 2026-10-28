# M4 driver-matching diagnostics

## Outcome

The restored DCP and display Device Tree nodes do enter the live IORegistry,
but the expected driver services do not attach.  With XNU's supported
`io=0xffff` diagnostic mask, the serial log shows registration of `dcp`,
`dcp0-expert`, `disp0`, `dart-dcp`, `dart-disp0`, and `dart-dispgrt`.  It does
not show `AppleASCWrapV6`, `RTBuddy`, `RTBuddyEndpointService`,
`AppleDCPExpert`, `AppleT8110DART`, or `AppleCLCD2` registering beneath them.

No selected display MMIO access occurred.  The immediate blocker is therefore
personality attachment/provider construction before DCP firmware execution,
not a missing display-register response.

## Reproducible inspection

The Boot KC's embedded prelink plist can be inspected without modifying it:

```sh
openios/tools/display/inspect_bootkc_display.py \
  openios/firmware/linux/iphone15-3-26.6/boot/bootkc
```

The tool found all eight queried display bundles.  Relevant versions are:

| Bundle | Version | Required provider or match |
| --- | --- | --- |
| AppleA7IOP-ASCWrap-v6 | 1.0.2 | `AppleARMIODevice`, IOName `iop,ascwrap-v6` |
| RTBuddy | 1.0.0 | `AppleA7IOPNub`, IOName `iop-nub,rtbuddy-v2` |
| AppleDCP | 1 | `AppleARMIODevice`, IOName `dcp-expert-v1`; later RTBuddy endpoints |
| AppleT8110DART | 1 | `AppleARMIODevice`, IOName `dart,t8110` |
| AppleMobileDispH15P-DCP | 140.0 | `AppleARMIODevice`, IOName `disp0,t8120`; later DCP endpoint 24 |
| IOMobileGraphicsFamily | 343.0.0 | library dependency |
| IOMobileGraphicsFamily-DCP | 343.0.0 | library dependency |
| AGXG15P | 353.14 | `gpu,t8120` personalities; intentionally not enabled |

Executable and personality presence is static evidence only.  The runtime log
is the authority for whether a service attached.

## Provider chain

The embedded personalities establish the following chain:

```text
AppleARMIODevice(dcp, compatible=iop,ascwrap-v6)
  -> AppleASCWrapV6 / AppleA7IOPNub(iop-dcp-nub)
     -> RTBuddy
        -> RTBuddyService
           -> RTBuddyEndpointService instances
              -> AppleDCP endpoint clients and AppleDCPLinkServiceSoC

AppleARMIODevice(dcp0-expert, compatible=dcp-expert-v1)
  -> AppleDCPExpert

AppleARMIODevice(disp0, compatible=disp0,t8120)
  -> AppleCLCD2

AppleARMIODevice(dart-*, compatible=dart,t8110)
  -> AppleT8110DART
```

AppleDCP links against AppleARMPlatform, AppleFirmwareKit, RTBuddy, and IOKit.
AppleCLCD2 additionally links against IOSlaveProcessor, RTBuddy,
IOMobileGraphicsFamily, IOMobileGraphicsFamily-DCP, IOSurface, IOAVFamily,
AppleM2ScalerCSCDriver, and AppleSEPManager.  Satisfying only IONameMatch is
therefore insufficient for an operational display stack.

## Runtime experiment

The input firmware was unchanged.  A generated Device Tree copy restored the
DCP ASC wrapper, RTBuddy nub, and DCP expert compatible properties.  The boot
used:

```text
rd=md0 serial=3 -v -noprogress wdt=-1 wlan-olyhal-abort io=0xffff
```

The important serial records were:

```text
Registering: IOService:/AppleARMPE/arm-io@10F00000/AppleT812xIO/dcp@32C00000
Registering: ../AppleARMPE/arm-io@10F00000/AppleT812xIO/dcp0-expert@3D2B8044
Registering: ../AppleARMPE/arm-io@10F00000/AppleT812xIO/disp0@30000000
Registering: ../AppleARMPE/arm-io@10F00000/AppleT812xIO/dart-dcp@3130C000
Registering: ../AppleARMPE/arm-io@10F00000/AppleT812xIO/dart-disp0@31304000
Registering: ../AppleARMPE/arm-io@10F00000/AppleT812xIO/dart-dispgrt@31350000
```

There was no corresponding registration of the driver classes listed above.
The bounded observer ended with `reads=0 writes=0`.  The debug mask greatly
increases serial traffic; this 60-second diagnostic was intentionally bounded
and is not classified as a boot regression test.

## DART-only result

The earlier DART-only probe restored `dart,t8110` and mapper compatibles and
produced no serial output before a 45-second timeout.  It also produced zero
selected MMIO accesses.  This is a negative bounded observation, not proof of
a deadlock.  Possible explanations include slower pre-console matching,
waiting for a provider/resource, or activity outside the selected ranges.
Determining which applies requires service matching/stack evidence, not a fake
DART response.

## Matching DCP firmware evidence

The matching full IPSW materially narrows the firmware question.  Its
BuildManifest selects:

| Component | Archive member | IM4P SHA-256 | Unwrapped SHA-256 |
| --- | --- | --- | --- |
| DCP | `Firmware/dcp/iphone15dcp.im4p` | `11e6cc7a8b044dde5130b7fd66611c16308aff91a669413120b486eca621a5ec` | `d1ee036566ebe4177f64f50e218b15309eb68ca2809b337bf548e066d6ed631c` |
| RestoreDCP | `Firmware/dcp/iphone15dcp_restore.im4p` | `4079636f7c9e375f65f737205219f6f7f00c8fb6ac77b8081dbd2a747aeba7ba` | `dc65531b4d38b009a06a6bf639227f14dd76380aa956ec5fc275030d63edf3a5` |

Both unwrap as arm64e Mach-O preload executables.  The normal payload contains
`RTKit-3255.160.4.release`, `pmgr_t8120.cpp`, `disp0-service`,
`dcpexpert-service`, `system-epic`, and `disp0-epic`.  These are direct T8120
firmware artifacts, not an inference from T8030 or a host test image.

The manifest marks both components `Personalize=true`; `RestoreDCP` is loaded
by iBoot and normal `DCP` is not.  Thus the remaining gap is not locating a
firmware binary.  It is reproducing the selected image's personalization,
memory placement, effective runtime Device Tree segment mappings, DART setup,
ASC start, and RTKit negotiation without inventing success responses.

## DCP hardware evidence and limits

The D74AP tree gives these concrete ASC properties:

- DCP register regions at physical `0x232c00000` (size `0x6c000`) and
  `0x232850000` (size `0x4000`), with four interrupts.
- `clock-gates` and `power-gates` value `0x184`.
- `iommu-parent` points to the DCP mapper; its stream is 5.
- `dcp0-expert` requires force-wakeup, PMGR scratch, remote power state, and
  two additional PMGR-related register regions.
- Display DART stream 0 and PIODMA stream 4 use 16 KiB pages; DCP DART uses
  stream 5 and a VM base of `0x10000000000`.

At inspected `m1n1` revision
`33c235dda271a2fc48abd9cceea4df27bfaebed4`, the ASC implementation uses CPU
control offset `0x44`, mailbox control offsets `0x110/0x114`, and FIFO offsets
`0x800` through `0x838` relative to the ASC mailbox base.  Its DCP path first
configures both DARTs, maps firmware segments, initializes the ASC, negotiates
RTKit versions 11–12, and then starts AFK/EPIC.  See the primary implementation
in [`asc.c`](https://github.com/AsahiLinux/m1n1/blob/33c235dda271a2fc48abd9cceea4df27bfaebed4/src/asc.c),
[`dcp.c`](https://github.com/AsahiLinux/m1n1/blob/33c235dda271a2fc48abd9cceea4df27bfaebed4/src/dcp.c), and
[`rtkit.c`](https://github.com/AsahiLinux/m1n1/blob/33c235dda271a2fc48abd9cceea4df27bfaebed4/src/rtkit.c).

The `m1n1` DCP experiment explicitly monitors the same `0x23130c000` DCP-DART
and `0x231c00000` mailbox neighborhood found in the D74AP inventory.  This is
useful correlation, but it still does not prove that all register semantics or
firmware protocols are identical on T8120.

The static D74AP tree currently lacks DCP `segment-ranges`; its RTBuddy child
also carries `no-firmware-service`, `quiesced`, and `user-power-managed`.
These facts are consistent with iBoot loading the personalized RestoreDCP and
supplying runtime state which the static tree alone does not contain.  The
firmware image is now evidence-backed, but its guest-physical placement and
boot contract are not.  Implementing mailbox success values at this point
would still be speculative, so no QEMU hardware model was added in M4.

## Next diagnostic

The next experiment should reconstruct the RestoreDCP load contract from the
personalized boot chain: Mach-O segment placement, runtime Device Tree
`segment-ranges`, DART mappings, and ASC reset/mailbox state.  In parallel,
capture the effective IOCatalogue entry and IOName set for the live `dcp` nub
to explain why `AppleASCWrapV6` does not attach.  The first acceptance point is
creation of `AppleA7IOPNub`, followed by an observed RTKit handshake; only then
should additional ASC mailbox behavior be implemented.
