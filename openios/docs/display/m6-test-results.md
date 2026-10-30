# M6 test results

## Status

| Phase | Status | Evidence |
| --- | --- | --- |
| A: personality/matching audit | PASS for static eligibility; PARTIAL for runtime | Boot KC personality has direct provider/name match; lifecycle unavailable |
| B: observability | PARTIAL | serial provider publication and QEMU observer work; `io=0xffff` is perturbing; `ioreg` cannot load in restore userspace |
| C: DCP prerequisites | PARTIAL | Mach-O layout validation added; load base, authorization state and mappings unknown |
| D: controlled experiments | PARTIAL | generated DT, 100-second DCP-only bound and M1 baseline retained; no M6 hardware change |
| E: implementation | BLOCKED | no evidence supports DCP/DART/mailbox semantics |

## Commands exercised

```sh
openios/tools/qemu/apply-sptm-patches.sh
python3 -m py_compile openios/tools/display/inspect_restoredcp_macho.py
openios/tools/display/inspect_restoredcp_macho.py \
  openios/firmware/research/iphone15-3-26.6-m4/unwrapped/iphone15dcp_restore.bin
```

The patch series reported already applied at pinned QEMU revision.  The new
inspector passed Python compilation and reports a valid RestoreDCP segment
layout.  Parent and nested-QEMU diff checks were clean before M6 source edits.

The DCP-only generated-DT run intentionally used a timeout and did not qualify
as an M1 regression.  After that experiment, a 70-second run with the normal
fixed-up DT, `test-display=off`, `display-mmio-trace=off`, and the preserved
M1 boot arguments again reached `bash-5.3#`.  The existing `test-display=on`
regression pass remains recorded in M4.  M6 made no QEMU C change, so it did
not require a build; the last verified QEMU build remains `ninja -j2` with
`--disable-werror` for the pre-existing GCC 15 warning.

## Confirmed blockers and hypotheses

- Confirmed: static personality eligibility does not yield visible ASC service
  registration or selected MMIO access in the bounded probe.
- Confirmed: the restore userspace cannot execute its IORegistry client because
  its dyld dependency is unavailable.
- Hypothesis only: AppleASCWrapV6 may be rejected by runtime catalogue
  matching, fail to link, fail `probe`, or wait for a dependency.
- Not attempted: signed-kernel modification, DCP image injection, fabricated
  ASC/DART values, RTKit responses, GPU behavior, or graphical iOS output.

## Next engineering blocker

Acquire a non-perturbing kernel-side match/probe result or a boot-path capture
of RestoreDCP placement and first ASC access.  That one observation determines
whether the next change belongs in kernel observability, iBoot/load plumbing,
or an opt-in QEMU ASC device.
