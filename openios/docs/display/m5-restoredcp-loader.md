# M5 T8120 RestoreDCP loader contract

## Status: PARTIAL — binary layout is verified; authenticated load contract is still unknown

## Inputs and preservation

The analysis uses only the ignored, read-only M4 extraction of the official
iPhone15,3 iOS 26.6 (`23G71`) IPSW.  Neither payload is tracked in Git,
copied into a patch, or modified.

| Component | Image4 payload SHA-256 | Unwrapped SHA-256 |
| --- | --- | --- |
| DCP | `11e6cc7a8b044dde5130b7fd66611c16308aff91a669413120b486eca621a5ec` | `d1ee036566ebe4177f64f50e218b15309eb68ca2809b337bf548e066d6ed631c` |
| RestoreDCP | `4079636f7c9e375f65f737205219f6f7f00c8fb6ac77b8081dbd2a747aeba7ba` | `dc65531b4d38b009a06a6bf639227f14dd76380aa956ec5fc275030d63edf3a5` |

BuildManifest marks both components personalized.  It marks `RestoreDCP` as
loaded by iBoot and normal `DCP` as not loaded by iBoot.  This makes
RestoreDCP the relevant payload for the restore environment, without proving
that the present QEMU boot path receives an authorized personalized ticket.

## Reproducible Mach-O inspection

The dependency-free tool below parses only Mach-O headers/load commands; it
does not alter the image:

```sh
openios/tools/display/inspect_restoredcp_macho.py \
  openios/firmware/research/iphone15-3-26.6-m4/unwrapped/iphone15dcp_restore.bin
```

Both payloads are 64-bit arm64e (`CPU_TYPE_ARM64`, arm64e subtype) Mach-O
`MH_PRELOAD` executables with `MH_PIE`, eight load commands, and an
`LC_UNIXTHREAD` entry state.  The recorded PC and SP are zero, so PC is
relative to a loader-selected base rather than a usable guest-physical entry
address.  There is no `LC_MAIN` and no internal `LC_CODE_SIGNATURE` command.
Absence of that command does **not** establish that firmware authentication is
absent: the IMG4 container, manifest, and iBoot personalization remain outside
the unwrapped Mach-O.

### RestoreDCP segments

| Segment | VM address | VM/file size | File offset | protections |
| --- | ---: | ---: | ---: | --- |
| `__TEXT` | `0x0` | `0x3c9000` | `0x1000` | r-x |
| `__DATA` | `0x3c9000` | `0x216000` | `0x3ca000` | rw- |
| `__OS_LOG` | `0x5df000` | `0x25000` | `0x5e0000` | rw- |
| `__DATA_CONST` | `0x604000` | `0x0` | `0x605000` | rw- |

Normal DCP has the same segment structure with a slightly different text/data
boundary.  RestoreDCP contains direct T8120/RTKit evidence including
`pmgr_t8120.cpp`, `RTKit-3255.160.4.release`, `disp0-epic`,
`dcpexpert-epic`, and `DCPExpertT8120`.

## Loader contract: evidence versus unknowns

| Step | Evidence | Status |
| --- | --- | --- |
| choose RestoreDCP for restore boot | BuildManifest `IsLoadedByiBoot=true` | verified |
| authenticate/personalize IMG4 | manifest says personalized | required; ticket/flow unknown in QEMU |
| choose physical load base | `LC_UNIXTHREAD` PC is relative zero | unknown |
| map Mach-O segments with stated protections | parsed segments | layout verified; mapping owner unknown |
| publish runtime `segment-ranges` | static D74AP DT lacks them | unknown |
| configure DCP DART stream 5 | DT gives mapper, page size and VM window | required; QEMU model absent |
| reset/start ASC and service interrupts | DT gives two DCP regions/four IRQs; m1n1 gives architecture | exact T8120 operation sequence unknown |
| negotiate RTKit/AFK/EPIC | strings and m1n1 architecture | required; no guest handshake observed |

The Asahi m1n1 DCP path remains useful primary implementation evidence for
ordering: set up DART mappings, map firmware segments, initialize ASC, then
negotiate RTKit and AFK/EPIC.  It is not a T8120 register specification.
See [m1n1 DCP](https://github.com/AsahiLinux/m1n1/blob/33c235dda271a2fc48abd9cceea4df27bfaebed4/src/dcp.c)
and [ASC](https://github.com/AsahiLinux/m1n1/blob/33c235dda271a2fc48abd9cceea4df27bfaebed4/src/asc.c).

## Engineering consequence

There is insufficient evidence to implement a loader or mailbox device.  A
safe next artifact is a loader-contract capture that obtains the actual
runtime DCP load address, segment mappings, and ASC initialization accesses
from the boot path.  Only after that capture may an opt-in QEMU device map
firmware memory or model a first mailbox state.  No proprietary firmware is
redistributed by this repository.
