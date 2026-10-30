# M6 RestoreDCP boot contract refinement

## Result: PARTIAL — validated image layout; no authenticated execution contract

`inspect_restoredcp_macho.py` now verifies every `LC_SEGMENT_64` file range and
that nonempty segment file ranges do not overlap.  On the matching 23G71
RestoreDCP payload it reports `segment_layout_valid: true`.

| Property | Verified result |
| --- | --- |
| image | `iphone15dcp_restore.bin`, SHA-256 `dc65531b4d38b009a06a6bf639227f14dd76380aa956ec5fc275030d63edf3a5` |
| architecture | arm64e Mach-O, `MH_PRELOAD`, PIE |
| entry representation | `LC_UNIXTHREAD`, arm64 thread-state flavor 6/count 68; PC/SP `0x0` relative to load base |
| segments | `__TEXT`, `__DATA`, `__OS_LOG`, `__DATA_CONST`; all checked ranges valid |
| internal Mach-O code signature | no `LC_CODE_SIGNATURE` |
| manifest | RestoreDCP is personalized and `IsLoadedByiBoot=true` |

The parsed segment VM offsets describe an image-relative layout, not guest
physical addresses.  A loader must select a base and provide the mappings that
make the relative entry PC meaningful.

## Known prerequisites and unknowns

| Contract part | Evidence | M6 conclusion |
| --- | --- | --- |
| image selection | BuildManifest designates RestoreDCP for iBoot | confirmed static input |
| authorization | personalized Image4 component | exact ticket/verification state unknown |
| physical base | no static `segment-ranges`; PC is zero-relative | unknown |
| firmware mapping | validated relative Mach-O segments | mapping owner/address unknown |
| DART | DCP mapper stream 5, 16 KiB pages and VM window are DT properties | QEMU implementation absent; AP/IOP direction unknown |
| ASC | DCP DT supplies two register regions/four IRQs | reset sequence/initial register values unknown |
| RTKit | firmware strings and m1n1 document architectural use | no handshake/memory negotiation observed |

The mainline/open-source architecture still supports the order DART setup →
firmware segments → ASC → RTKit → AFK/EPIC.  It supplies no authorization to
invent T8120 base addresses, mappings, mailbox values or endpoint replies.

## Next capture requirement

Capture one authenticated boot-path observation that identifies RestoreDCP
physical base, mapped segment ranges, and the first DCP ASC access.  Without
it, an opt-in QEMU loader would be an unverified firmware-placement emulator.
