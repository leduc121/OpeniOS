# OpeniOS continuation checkpoint

## Verified state

- Branch: `openios/display-research`; no commit, push, or merge was made.
- QEMU-SPTM: 11.1.0, pinned nested revision
  `bad6336fb24211f8c4e8e946c259bd5b12417340`.
- M1: original iOS 26.6/D74AP boot reaches `bash-5.3#`; the latest regression
  reported Darwin 25.6.0, iPhone15,3, and root uid.
- M8.2/M9/M9.1: signed host-built Mach-O runs in the guest with AMFI approval.
- M10/M10.2: DCP-compatible restoration publishes AppleASCWrapV6 and
  AppleDCPExpert; disp0 restoration publishes AppleCLCD2. The M10.1 direct
  `IOService` child query found zero children beneath AppleASCWrapV6. No
  RTBuddy, mobile framebuffer, or selected unassigned MMIO access was
  observed.
- M10.2 extends the observer over selected mapped CPU/flatview accesses and
  validates it with an opt-in synthetic mapping. The real DCP-only guest still
  recorded zero selected transactions through those paths.

## Latest successful guest commands

```text
# M1 baseline execution:
python3 openios/tools/display/guest_exec.py --dtree openios/firmware/linux/iphone15-3-26.6/boot/dtree --tc openios/firmware/linux/work/ramdisk-v5.tc --ramdisk openios/firmware/linux/work/ramdisk-shell-v5.apfs --cmd "echo HELLO_FROM_GUEST"
# Result: bash-5.3# prompt reached in 21s, output "HELLO_FROM_GUEST", exit code 0.

# M10.1 IORegistry inspector:
/usr/local/bin/openios-ioreg
# Result: exit code 0, OPENIOS_STAGE_A_DONE, verified AppleASCWrapV6 and AppleDCPExpert.
```

## Transport Recovery and Hardening

The previous stalled execution cycle was diagnosed and fixed:
- Root cause: `guest_exec.py` used `echo CMD_FINI_""_SHED=$?` which matched the terminal echo on PTY before command completion, and had unbounded wait loops when background tasks competed for PTY.
- Fix:
  1. Concurrency protection via `/tmp/openios_guest_exec.lock` with `fcntl.flock(LOCK_EX | LOCK_NB)`.
  2. Completion detection uses timestamped `printf '__%s:%d__\n' {tag} $?` after disabling terminal echo.  The previously committed `%%d` spelling emitted a literal `%d` and was corrected in M10.4; a non-zero guest `false` command now reports exit status 1.
  3. QEMU process polling on every iteration reporting actual exit status, PID, elapsed time, and stdout/stderr immediately.

## M10.9 Achievements — Primary Exception Resolved & RTBuddy Verified

M10.9 completely resolved blocker B-003 and validated RTBuddy initialization:

1. **Phase A & B (Capture Primary Exception & Fault Analysis)**:
   - Automated GDB supervisor (`capture_primary_exception.py` + `gdb_capture_worker.py`) trapped the primary synchronous exception before secondary handler corruption.
   - Faulting PC (`ELR_EL1`): `0xfffffff02853aedc` (unslid `0xfffffff00853aedc`) inside `AppleDCPExpert`.
   - Faulting Virtual Address (`FAR_EL1`): `0xffffffeb5ecd0044` (unslid `0xffffffeb3ecd0044`).
   - Physical Address (`GPA`): `0x23d2b8044` (`dcp0-expert` MMIO Range 0).
   - Syndrome (`ESR_EL1`): `0x96000050` (`EC=0x25` Data Abort EL1, `IL=1`, `ISS=0x50` -> `DFSC=0x10` Synchronous External abort on write).
   - Root cause: `AppleDCPExpert` writes PMGR scratch register values (`pmgr-scratch-value-on`) during co-processor power-on. The `dcp0-expert` ranges (`0x23d2b8044` len 0xc, `0x23d008000` len 0x4) were unmapped in QEMU `darwin.c`, returning `MEMTX_DECODE_ERROR`.
   - Secondary panic explained: `sleh_synchronous` dispatched to hardware error logging (`0xfffffff009f7f3f4`), which overran a 7-element dispatch table at `0xfffffff007ac9e48` and executed `blraa` on unaligned string pointer `0xfffffff02705c51a`, causing the PC alignment panic.

2. **Phase C (DART Setup Revalidation)**:
   - `dart-dcp` with `dart-id = "u32:0x0"` and exact 256-byte `random-seed` was confirmed valid and conflict-free for the standalone DCP controller.
   - SPTM requirement: each active `compatible = "dart,t8110"` node must have a unique `dart-id` (`u32 < 256`) to initialize its internal `state->dart_id` structures. Multiple active DARTs must not share `dart-id = 0`.

3. **Phase D (Minimal Justified Correction)**:
   - Added `init_dcp_expert(dt_root, iobase)` in `third_party/darwin-vm/qemu-sptm/hw/arm/darwin.c` to dynamically allocate zeroed memory for `dcp0-expert` ranges whenever `compatible = "dcp-expert-v1"` is present in the Device Tree.
   - Built cleanly with `ninja -C third_party/darwin-vm/qemu-sptm/build -j2`.

4. **Phase E (Verification & Diagnostics)**:
   - GDB trapped `RTBuddy::start` return at `0xfffffff029b3d7f8`: confirmed `w0 = 1` (`true`).
   - Live guest booted to `bash-5.3#` in ~23 seconds with zero panics.
   - `openios-ioreg` confirmed:
     - `AppleASCWrapV6` registered on `dcp@32C00000` (provider `AppleARMIODevice`).
     - `iop-dcp-nub` registered as child in `IOService` (`compatible=iop-nub,rtbuddy-v2|`).
     - `AppleDCPExpert` registered on `dcp0-expert@3D2B8044`.
     - `dart-dcp@3130C000` registered (`compatible=dart,t8110|`).
   - M1 regression: baseline boot passed with exit code 0 (`M1_REGRESSION_PASS`), original firmware checksums remain identical.

## M11/M12 Achievements — Multi-DART Resolution & AppleCLCD2 Registration

1. **Multi-DART Bootstrap (SPTM Dart-ID Mapping)**:
   - Root cause of multi-DART boot failure identified: SPTM indexes DART instances via `dart-id` property (`u32 < 256`). When `make_display_probe_dtree.py` previously restored `darts`, all instances (`dart-dcp`, `dart-disp0`, `dart-dispgrt`) received default `dart-id = 0`, colliding inside SPTM instance table.
   - Fix: Updated `openios/tools/display/make_display_probe_dtree.py` to assign distinct `dart-id` properties:
     - `dart-dcp`: `dart-id = "u32:0x0"`
     - `dart-disp0`: `dart-id = "u32:0x1"`
     - `dart-dispgrt`: `dart-id = "u32:0x2"`
   - Bounded guest verification: Guest booted cleanly with `/tmp/openios-m11-darts.dtree` in 20.6s with exit code 0 (`DARTS_PROBE_SUCCESS`).

2. **AppleCLCD2 Registration & Display Stack (`disp0`)**:
   - Restored `disp0` (`compatible = "disp0,t8120"`) alongside `dcp` and `darts` (`/tmp/openios-m12-disp0.dtree`).
   - Guest booted cleanly in 20.5s with zero panics (`DISP0_PROBE_SUCCESS`).
   - `openios-ioreg` confirmed live publication in `IOService` plane:
     - `disp0@30000000` registered with `compatible = disp0,t8120|`.
     - `AppleCLCD2` registered as service provider under `disp0@30000000` (`class = AppleCLCD2`, `provider = AppleARMIODevice`).
     - `dart-disp0@31304000` and `dart-dispgrt@31350000` registered (`compatible = dart,t8110|`).
     - `AppleASCWrapV6` registered on `dcp@32C00000` with child `iop-dcp-nub`.
     - `AppleDCPExpert` registered on `dcp0-expert@3D2B8044`.

## M13 Userspace Audit — Launchd Boot Mode & Dependency Graph

1. **Root Cause: Why the Restore Ramdisk Boots to Bash**:
   - Disassembly of `/sbin/launchd` at `0x10004ece0`-`0x10004ed34` revealed exact mechanism:
     - `launchd` queries `kern.bootargs` via `sysctlbyname`.
     - Explicit check: `strstr(bootargs, "rd=md0")` matches the ramdisk boot argument.
     - On match, `launchd` executes `strb w8, [x25, #0x4e3]` (sets restore environment flag = 1).
     - At `0x100018408`, `launchd` checks this flag, logs `"Restore environment starting."`, and enters restore mode.
     - In restore mode, `launchd` bypasses normal multi-user initialization, ignores system daemons, and searches only `/System/Library/LaunchDaemons/` (where only `com.jprx.bash.plist` resides).
   - In addition, the restore ramdisk lacks `/System/Library/xpc/launchd.plist` (2.2 MB system service database) and `dyld_shared_cache_arm64e`, causing full system executables (`ioreg`, `backboardd`, `SpringBoard`) to abort on launch with `no such file, no dyld cache`.

2. **Official Full-System Asset Inventory & Verification**:
   - Decrypted System APFS volume: `openios/firmware/research/iphone15-3-26.6-m4/filesystem-inventory/main-aea/094-95332-083.dmg` (9.1 GB, 215,536 files).
   - Decrypted Cryptex System volume: `openios/firmware/research/iphone15-3-26.6-m4/filesystem-inventory/cryptex-system/094-97212-084.dmg` (5.2 GB, contains `dyld_shared_cache_arm64e` and subcaches).
   - Official System TrustCache unwrapped: `094-95332-083.dmg.aea.trustcache` contains 3,534 valid Apple CDHashes.
   - Official Cryptex TrustCache unwrapped: `094-97212-084.dmg.aea.trustcache` contains 115 valid Apple CDHashes.
   - Real binary signatures verified against System TrustCache:
     - `SpringBoard` (`System/Library/CoreServices/SpringBoard.app/SpringBoard`, arm64e Mach-O): `CDHash = b3455a9f875243e5d1b6a10894b7894d1d34dfec` -> **MATCHED**.
     - `backboardd` (`usr/libexec/backboardd`, arm64e Mach-O): `CDHash = 8814de153d7b611dad7908b3d9ba97797ffc036f` -> **MATCHED**.
   - Live guest capabilities verified:
     - `/usr/sbin/hdik` attached and operational in guest (exit code 0).
     - `/sbin/mount` operational on APFS `/dev/md0`.

## Regression and safety

The original M1 hashes remain:

```text
cf39a91c5f7cce04ad27bd2fde6161e038d5f30af81672305b55938c3c0e115f  ramdisk-shell-v5.apfs
4d0df820489a76aa7dcc630b63ae6701589cc1637d0bfd526ea07f35dbe5b8a6  ramdisk-v5.tc
```

Baseline M1 boot verified: reached bash prompt in ~20.7s, exit code 0 (`M1_REGRESSION_PASS`).


