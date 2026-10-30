# M7 targeted AppleASCWrapV6 lifecycle diagnosis

## Concise diagnosis

**Result: observation is insufficient to distinguish candidate matching,
driver loading, probe, start, or ASC initialization.**  The earliest confirmed
runtime boundary is unchanged: AppleARMPE publishes the DCP provider, but no
AppleASCWrapV6 service registration or selected ASC/DART/display MMIO access
is observed in the bounded DCP-only probe.  There is no trustworthy lifecycle
instrumentation in the current restore environment to narrow that boundary.

No DCP, DART, GPU, mailbox, firmware, or kernel behavior was implemented.

## Least-invasive observation evaluation

| Method | Result | Evidence / limitation |
| --- | --- | --- |
| normal serial boot | usable for provider publication | DCP, DCP expert, display and DART DT services register in the DCP-only probe |
| `io=0xffff` | rejected as lifecycle diagnostic | logs provider publication but not a candidate/probe result; DCP-only guest misses shell by its 100-second bound; 0 selected accesses |
| root-shell `ioreg` | unavailable | `/usr/sbin/ioreg` fails to load `/usr/lib/libncurses.5.4.dylib`; ramdisk has no usable dyld cache |
| existing command-line support | unavailable | `kextstat`, `grep`, and a compatible static registry query path are absent from the restore image |
| new userspace query tool | blocked | no arm64e iOS toolchain/signing/trust path, and adding a binary would alter the known-good root asset |
| kernel IOCatalogue hook | blocked | no source-matched, safely rebuildable/signed 23G71 Boot KC or verified experimental boot path; known-good Boot KC must not be changed |

Apple's source-available XNU contains IOCatalogue and IOKit debug code, but
this establishes neither that iOS 26.6 release Boot KC accepts a particular
debug bit nor that it logs matching/probe outcomes.  It is therefore not used
as runtime evidence.  The source references are `IOCatalogue.cpp` and
`IOKitDebug.h` in the Apple XNU distribution; M6 records the exact links.

## Static eligibility versus runtime evidence

`AppleASCWrapV6` is statically eligible: its Boot KC personality requires
`AppleARMIODevice` and `IONameMatch=iop,ascwrap-v6`; the original D74AP DCP DT
node has that compatible string, and the generated DCP-only probe restores it
without changing other DCP properties.  There is no `IOPropertyMatch` in the
personality.

Runtime evidence ends after publication of the provider nub.  The following
outcomes all remain **unknown**, not failed:

1. no candidate selected;
2. candidate selected but executable unavailable;
3. loaded driver rejects `probe`;
4. successful probe with failing/waiting `start`;
5. successful start that fails at ASC hardware initialization.

The 100-second probe is a negative bounded test, not evidence of deadlock.
The observer's zero access count only proves no selected unassigned-memory
access occurred; it cannot report accesses that a future mapped device would
handle.

## Raw evidence references

- Static personality: run
  `openios/tools/display/inspect_bootkc_display.py openios/firmware/linux/iphone15-3-26.6/boot/bootkc`.
- Generated probe: `openios/tools/display/make_display_probe_dtree.py` with
  `--enable dcp`, output under `/tmp/openios-m5-dcp-only.dtree`.
- Runtime serial records and zero-counter summary: M5/M6 command transcripts
  and [M6 IOKit trace](m6-iokit-match-trace.md).
- Root-shell loader failure: `ioreg` transcript in
  [M6 IOKit trace](m6-iokit-match-trace.md).

## Decision gate and smallest next action

Stop emulator extension here.  The smallest evidence-backed next action is to
obtain a separately bootable, source-matched, signed experimental kernel/Boot
KC that can emit one log-only IOCatalogue candidate/match/probe record for
`AppleASCWrapV6` on the DCP provider.  Until that asset and authorization path
exist, no safe QEMU change can identify the earliest lifecycle failure.

## Regression

The post-M6 known-good M1 invocation with the normal fixed-up DT,
`test-display=off`, `display-mmio-trace=off`, and preserved arguments
`rd=md0 serial=3 -v -noprogress wdt=-1 wlan-olyhal-abort` reached `bash-5.3#`.
M7 changed no boot asset or QEMU source.
