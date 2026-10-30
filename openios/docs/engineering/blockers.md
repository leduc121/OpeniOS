# OpeniOS engineering blockers

## B-001 — ASC service stops before IOP nub publication

- Milestone: M10.3
- Status: BLOCKED — runtime lifecycle branch unobserved; no DT property defect demonstrated
- Symptom: restoring `iop,ascwrap-v6` publishes `AppleASCWrapV6`, but neither
  `AppleA7IOPNub` nor `RTBuddy` appears in the IOService snapshot.
- Evidence:
  1. M10.4 runtime `openios-ioreg` proves the DCP `AppleARMIODevice` that
     provides AppleASCWrapV6 DOES have `iop-dcp-nub` (IOService) as a child in
     `gIODTPlane`.
  2. Static analysis of `AppleA7IOP::start` and `AppleA7IOP::createChildNubs` confirms
     `createChildNubs` is called and executes `0xfffffff00a4a4068(provider, 2, 0)`:
     `IORegistryIterator::iterateOver(provider, gIODTPlane, 0)` collects non-ignored
     children.
  3. `AppleA7IOPNub::withRegistryEntry` allocates the nub and calls
     `nub->init(child, gIODTPlane)`.  Its initializer at
     `0xfffffff0080d87b0` delegates initialization; the method contains no
     direct `device_type`, `reg`, or `role` comparison.
  4. In `withRegistryEntry`, it verifies `provider` against `AppleARMIODevice::gMetaClass`.
- Confirmed constraint: the original and restored DCP nub carry the same
  relevant properties.  The actual failure may be before child iteration,
  within the delegated initializer, provider validation, or another lifecycle
  branch; the current guest observation cannot distinguish these.
- Reproduction: boot Stage A ramdisk with `/tmp/test-dcp.dtree` and run
  `/usr/local/bin/openios-ioreg`.
- Next investigation: use a separately signed, source-matched experimental
  Boot KC to log only child iteration and `withRegistryEntry` return values.
  Do not modify the DT or implement QEMU behavior before that evidence exists.

## B-002 — Current tracer has no DMA/IOVA coverage guarantee

- Milestone: M10.2
- Status: PARTIAL
- Symptom: current observer reports zero selected accesses in all M10 variants.
- Evidence: `system/memory.c` invokes the observer only from
  `unassigned_mem_read()` and `unassigned_mem_write()`. It records bounded
  physical transactions that reached QEMU's unassigned region.
- Reproduction: pass `-M darwin,display-mmio-trace=on`; exit QEMU to receive
  the range summary.
- Hypothesis: zero proves no selected **unassigned physical** transaction. It
  does not by itself cover accesses handled by a mapped MemoryRegion or DMA
  through a future DART/IOMMU address space.
- Missing prerequisite: a guest-visible ASC/DART transition or a demonstrably
  mapped device whose accesses warrant a broader dispatch/DMA trace.
- Next investigation: do not broaden QEMU logging speculatively; first obtain
  the M10.1 lifecycle state that would select a concrete address space.
