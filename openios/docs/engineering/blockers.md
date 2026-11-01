# OpeniOS engineering blockers

## B-001 — ASC service wait for DCP IOMapperID dependency

- Milestone: M10.3 / M10.8
- Status: RESOLVED — service wait condition identified and satisfied; AppleA7IOP resumed; AppleA7IOPNub allocated; RTBuddy matched and started.
- Resolution Evidence:
  1. Exact wait function: `IOService::waitForMatchingService(OSDictionary *matching, uint64_t timeout)` at unslid `0xfffffff00a4bf3b4` (slid `0xfffffff02a4bf3b4`), invoked from `AppleA7IOP` mapper helper at `0xfffffff02a5081fc`.
  2. Matching dictionary dumped via GDB:
     ```
     {
       "IOPropertyMatch": {
         "IOMapperID": OSData<0xad 0x00 0x00 0x00>
       }
     }
     ```
     where `0xad` is the `iommu-parent` phandle of DCP (`AppleARMIODevice` at `0xffffffe5ee0fe740`).
  3. Timeout: `x1 = 0xffffffffffffffff` (`UINT64_MAX` / -1), resulting in indefinite wait on `lck_mtx_sleep`.
  4. Publishing service: `IODARTMapper::start` reads `AAPL,phandle` (or `iommu-id`) from `mapper-dcp`, sets `IOMapperID = phandle` on itself, and invokes `registerService()`.
  5. DART boot divergence diagnosed: SPTM `t8110dart_bootstrap_instance` panics if Device Tree nodes with `compatible = "dart,t8110"` lack the `dart-id` property (requires `u32`, 4 bytes, `< 256`). Re-encoded `random-seed` must also remain exact 256-byte binary `bytes`.
  6. Runtime verification: Restoring `dart-dcp` with `dart-id = "u32:0x0"` and `mapper-dcp` allowed `AppleA7IOP` to resume, hit `createChildNubs`, construct `AppleA7IOPNub`, and match `RTBuddy`:
     ```
     AppleA7IOPNub: withRegistryEntry, 47: allocated nub <ptr>
     RTBuddy(DCP): start(<ptr>) - (Jul 11 2026@16:29:46)
     ```

## B-003 — RTBuddy startup triggers exception causing fault handler loop overrun

- Milestone: M10.8 / M10.9
- Status: RESOLVED — primary exception intercepted, root cause diagnosed, minimal QEMU MMIO mapping implemented, RTBuddy::start verified returning 1 (true), and full bash boot succeeded with zero panic.
- Resolution Evidence:
  1. Primary exception captured via GDB automation (`openios/tools/display/capture_primary_exception.py`):
     - Faulting PC (`ELR_EL1`): `0xfffffff02853aedc` (unslid `0xfffffff00853aedc`) inside `AppleDCPExpert::start` / PMGR scratch setup.
     - Faulting Virtual Address (`FAR_EL1`): `0xffffffeb5ecd0044` (unslid `0xffffffeb3ecd0044`).
     - Physical Address (`GPA`): `0x23d2b8044`.
     - Syndrome (`ESR_EL1`): `0x96000050` (`EC=0x25` Data Abort EL1, `IL=1`, `ISS=0x50` -> `DFSC=0x10` Synchronous External abort on write).
     - Faulting Instruction: `str w12, [x13]` copying `pmgr-scratch-value-on` words to `dcp0-expert` MMIO Range 0 (`0x23d2b8044`).
  2. Root cause:
     - `dcp0-expert` register ranges (`0x23d2b8044` len 0xc, `0x23d008000` len 0x4) were unmapped in QEMU `darwin.c`.
     - QEMU returned `MEMTX_DECODE_ERROR` on write to unassigned MMIO, generating a synchronous external data abort.
     - The hardware error reporting path in `sleh_synchronous` (`0xfffffff009f7f3f4`) traversed past a 7-element error-table (`0xfffffff007ac9e48`) into adjacent string pointers, executing `blraa` on unaligned address `0xfffffff02705c51a`, which created the secondary PC alignment panic.
  3. Minimum justified correction:
     - Added `init_dcp_expert()` in QEMU `hw/arm/darwin.c` to dynamically map zeroed RAM for `dcp0-expert` ranges when `compatible = "dcp-expert-v1"` is present in the Device Tree.
     - Built QEMU with `-j2` cleanly.
  4. Verification:
     - GDB trapped `RTBuddy::start` return at `0xfffffff029b3d7f8`: confirmed `w0 = 1` (`true`).
     - Live guest booted cleanly to `bash-5.3#` in 23.5s with zero panics.
     - `openios-ioreg` confirmed:
       - `AppleASCWrapV6` matched on `dcp@32C00000` (provider `AppleARMIODevice`)
       - `iop-dcp-nub` registered as child of `AppleASCWrapV6` (`compatible=iop-nub,rtbuddy-v2|`)
       - `AppleDCPExpert` matched on `dcp0-expert@3D2B8044` (provider `AppleARMIODevice`)
       - `dart-dcp@3130C000` matched (`compatible=dart,t8110|`)
  5. Regression:
     - Baseline M1 boot passed in 23.6s with exit code 0 (`M1_REGRESSION_PASS`).
     - Original firmware checksums remain unchanged.

## B-002 — Current tracer has no DMA/IOVA coverage guarantee

- Milestone: M10.2
- Status: PARTIAL
- Symptom: current observer reports zero selected accesses in all M10 variants.
- Evidence: patch 0004 records bounded selected CPU/flatview mapped accesses
  and the unassigned fallback. Its synthetic test map verifies both routes.
  The M10 DCP-only trace still reports zero selected transactions.
- Reproduction: pass `-M darwin,display-mmio-trace=on`; exit QEMU to receive
  the range summary.
- Hypothesis: zero rules out selected transactions through those instrumented
  CPU/flatview routes. It does not cover DMA through a future DART/IOMMU
  address space.
- Missing prerequisite: a guest-visible ASC/DART transition or a demonstrably
  mapped device whose accesses warrant a broader dispatch/DMA trace.
- Next investigation: do not broaden QEMU logging speculatively; first obtain
  the M10.1 lifecycle state that would select a concrete address space.

## B-004 — Multi-DART bootstrap collision in SPTM

- Milestone: M11 / M12
- Status: RESOLVED — distinct DART IDs mapped; multi-DART probe booted cleanly; AppleCLCD2 registered under disp0.
- Resolution Evidence:
  1. Root cause: SPTM indexes DART controllers via `dart-id` (`u32 < 256`). When `darts` was enabled in `make_display_probe_dtree.py`, all controllers (`dart-dcp`, `dart-disp0`, `dart-dispgrt`) received default `dart-id = 0`, creating collision and bootstrap failure.
  2. Correction: Updated `make_display_probe_dtree.py` to assign distinct IDs:
     - `dart-dcp`: `u32:0x0`
     - `dart-disp0`: `u32:0x1`
     - `dart-dispgrt`: `u32:0x2`
  3. Verification:
     - Booted with `/tmp/openios-m11-darts.dtree`: exit code 0 (`DARTS_PROBE_SUCCESS`).
     - Booted with `/tmp/openios-m12-disp0.dtree`: exit code 0 (`DISP0_PROBE_SUCCESS`).
     - `openios-ioreg` confirmed:
       - `AppleCLCD2` registered under `disp0@30000000` (class `AppleCLCD2`, provider `AppleARMIODevice`).
       - `dart-disp0@31304000` and `dart-dispgrt@31350000` registered (compatible `dart,t8110|`).
  4. Regression: Baseline M1 boot passed in 20.7s with exit code 0 (`M1_REGRESSION_PASS`).

## B-005 — Launchd diversion to restore mode and missing userspace assets

- Milestone: M13
- Status: RESOLVED (DIAGNOSED & ASSETS VERIFIED) — exact trigger diagnosed in launchd disassembly; official System/Cryptex APFS images, LaunchDaemons, trustcaches, and SpringBoard/backboardd verified.
- Evidence & Diagnostics:
  1. Launchd trigger: Disassembly of `/sbin/launchd` at `0x10004ece8` revealed `strstr(bootargs, "rd=md0")` matches the ramdisk boot argument, executing `strb w8, [x25, #0x4e3]` to set the restore mode flag. At `0x100018408`, `launchd` announces `"Restore environment starting."`, skips multi-user services, and restricts execution to `/System/Library/LaunchDaemons/` (where only `com.jprx.bash.plist` was provided).
  2. Missing dependencies identified:
     - System service database: `/System/Library/xpc/launchd.plist` (2.2 MB, 691 daemons, Version 7) absent from restore ramdisk.
     - Dynamic linker cache: `dyld_shared_cache_arm64e` absent from restore ramdisk; required by all full system executables.
  3. Verified assets:
     - Decrypted System APFS volume: `094-95332-083.dmg` (9.1 GB, contains `System/Library/xpc/launchd.plist` and 628 launch daemons).
     - Decrypted Cryptex System volume: `094-97212-084.dmg` (5.2 GB, contains `dyld_shared_cache_arm64e`).
     - Official System TrustCache (`094-95332-083.dmg.aea.trustcache`) unwrapped to 3,534 verified CDHashes, matching both `SpringBoard` (`b3455a9f...`) and `backboardd` (`8814de15...`).
  4. In-guest verification: `/usr/sbin/hdik` attached and functional (exit code 0); `/sbin/mount` confirmed APFS root on `/dev/md0`.

