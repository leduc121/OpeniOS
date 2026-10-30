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

## Current blocker and exact next action

M10.4 corrected the M10.3 child-iterator conclusion.  Static analysis establishes the candidate path, but no lifecycle return has been observed:
1. `AppleASCWrapV6::start` inherits `AppleA7IOP::start`. It maps Range 0/1, sets interrupt handlers, and reaches `0xfffffff0080d6370: bl createChildNubs(provider)`.
2. `createChildNubs` calls `0xfffffff00a4a4068(provider, 2, 0)` which runs `IORegistryIterator::iterateOver(provider, gIODTPlane, 0)`:
   - In `gIODTPlane`, runtime `openios-ioreg` proves the same DCP `AppleARMIODevice` that provides AppleASCWrapV6 has child `iop-dcp-nub`.
   - The iterator filters `AAPL,ignore` and constructs an `OSCollectionIterator`.
3. For each child, `createChildNubs` casts against `IORegistryEntry` and calls `AppleA7IOPNub::withRegistryEntry(child, AppleASCWrapV6)`:
   - `withRegistryEntry` allocates `new AppleA7IOPNub` and calls `nub->init(child, gIODTPlane)` (vtable slot 64, `0xfffffff0080d87b0`).
   - `nub->init` at `0xfffffff0080d87b0` delegates initialization and handles its boolean result; it has no direct `device_type`, `reg`, or `role` comparison.
   - `withRegistryEntry` checks `provider` and verifies its provider object against `AppleARMIODevice::gMetaClass`.
   - If any check returns false/NULL, `withRegistryEntry` releases `nub` and returns NULL.
4. The original and probe DT nubs have identical relevant properties; adding fields would be speculative.  See [M10.4 AppleA7IOPNub publication check](../display/m10.4-a7iop-publication.md).  The next safe action is a separately bootable, source-matched, log-only experimental Boot KC; until then the failure branch and any QEMU correction are unknown.

## Regression and safety

The original M1 hashes remain:

```text
cf39a91c5f7cce04ad27bd2fde6161e038d5f30af81672305b55938c3c0e115f  ramdisk-shell-v5.apfs
4d0df820489a76aa7dcc630b63ae6701589cc1637d0bfd526ea07f35dbe5b8a6  ramdisk-v5.tc
```

No SpringBoard, guest graphics, DCP firmware execution, RTKit transport,
DART translation, GPU emulation, or touch interaction has been demonstrated.

