# M5 T8120 DCP / RTKit test results

## Phase status

| Phase | Status | Evidence |
| --- | --- | --- |
| A — preserve/verify | PASS | M2–M4 staged; cached diff check passes; QEMU patch series is already applied at pinned revision |
| B — ASC matching | PARTIAL | DCP nub publication verified; no ASC service/MMIO observed; restore userspace cannot run `ioreg` |
| C — RestoreDCP contract | PARTIAL | matching payloads, hashes, architecture, segment layout, and relative entry state verified; authenticated placement/start contract unknown |
| D — minimal implementation | BLOCKED | no evidence permits a non-speculative QEMU DCP response; diagnostic tool added only |
| E — full-system readiness | PARTIAL | M4 verified System/Cryptex binaries and launch policy; System/Preboot/Data runtime group remains unbooted |

## Baseline preservation

Before M5 work, the parent index was updated without a commit or push:

```sh
git switch openios/display-research
git add openios/patches/qemu-sptm/ openios/tools/display/ openios/docs/display/
git diff --cached --check
git diff --cached --stat
```

The staged baseline contains the M2–M4 patch series, tools, and reports.  The
nested QEMU repository remains at
`bad6336fb24211f8c4e8e946c259bd5b12417340`; its working changes are represented
by the parent patch series.  The application check passed:

```sh
openios/tools/qemu/apply-sptm-patches.sh
# QEMU-SPTM patch series already applied.
```

No M1 boot asset, trustcache, IPSW, System image, or nested-QEMU file was
reset, cleaned, overwritten, committed, pushed, or merged.

## Commands and results

| Command/experiment | Result |
| --- | --- |
| `python3 -m py_compile openios/tools/display/inspect_restoredcp_macho.py` | PASS |
| inspect normal and RestoreDCP Mach-O | PASS; parsed 8 load commands and 4 segments each |
| DCP-only generated DT with `io=0xffff`, observer on, 100-second bound | PARTIAL; DCP/dcp0-expert/disp0/DART nubs registered, no ASC/RTBuddy class registration, 0/0 selected accesses, no root shell before timeout |
| normal M1 boot | PASS; reached `bash-5.3#` in M4 regression |
| M1 with `test-display=on` | PASS; reached `bash-5.3#` in M4 regression |
| DART-only 45-second probe | PARTIAL/negative; no serial/root shell before bound, not a deadlock conclusion |

The M5 source change is a read-only Mach-O inspection tool.  No C/QEMU source
changed, so a new QEMU build was neither needed nor claimed.  The last QEMU
build used `ninja -j2` with `--disable-werror`; GCC 15 otherwise stops on the
pre-existing enum-pointer `sscanf` warning in `apple_aic.c`.  No source warning
was suppressed.

## Next concrete blocker

Obtain a runtime observation at the DCP loader boundary: authenticated
RestoreDCP selection, physical segment base/mappings, and the first ASC reset
or mailbox access.  The most valuable prior step is opt-in kernel-side
IOCatalogue match/probe logging for `AppleASCWrapV6`; it must log only and
must not change a matching or MMIO result.  Without this, emulating ASC/DART
or claiming RTKit progress would be speculative.
