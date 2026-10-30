# M10 DCP / RTKit matching experiments

## Status: PARTIAL — driver services attach; RTBuddy and hardware execution remain absent

## Method

Each probe began with the original D74AP Device Tree, ran the existing normal
QEMU fixup, then restored only one compatible-property group in a new `/tmp`
file. SGX remained removed. QEMU used the M9.1 signed experimental ramdisk and
trustcache, original Boot KC/SPTM/TXM, separate historical `-args`, `-m 8G`,
and the opt-in bounded `display-mmio-trace=on` observer. No original firmware,
Device Tree, or QEMU source was changed.

## Runtime matrix

| Variant | Restored compatible properties | Shell | Published driver services | MMIO observer |
| --- | --- | --- | --- | --- |
| A | none (normal fixed-up DT) | PASS | no ASC/DCP/CLCD2 service | property baseline only |
| B | `dcp=iop,ascwrap-v6`, child `iop-nub,rtbuddy-v2`, `dcp0-expert=dcp-expert-v1` | PASS | `AppleASCWrapV6`, `AppleDCPExpert` | 0 reads, 0 writes in 19 selected ranges |
| C | `disp0=disp0,t8120` | PASS | `AppleCLCD2` | 0 reads, 0 writes in 19 selected ranges |
| D | display DART plus mapper compatibles | PARTIAL | no serial or shell by the 45-second bound | 0 reads, 0 writes in 19 selected ranges |

## Decisive DCP result

Variant B reached `bash-5.3#`; the in-guest read-only inspector returned zero:

```text
OPENIOS_IOREG_TARGET name=dcp ... compatible=iop,ascwrap-v6|
OPENIOS_IOREG_TARGET name=AppleASCWrapV6 .../dcp@32C00000/AppleASCWrapV6
OPENIOS_IOREG_TARGET name=AppleDCPExpert .../dcp0-expert@3D2B8044/AppleDCPExpert
```

`AppleA7IOPNub`, `RTBuddy`, `AppleCLCD2`, and `IOMobileFramebuffer` were not
published in this variant. The runtime boundary is therefore:

```text
DCP DT nub with matching compatible
  -> AppleASCWrapV6 is published
  -> AppleDCPExpert is published from its independent DCP-expert nub
  -> no observed AppleA7IOPNub / RTBuddy publication
  -> no selected DCP/DART/display MMIO access
```

This proves ASC personality selection and service publication. It does not
prove that `AppleASCWrapV6::start()` completed or explain why no IOP nub was
published. The observer summary was `reads=0 writes=0 detailed=0/256` across
all 19 selected ranges.

## Display-controller comparison

Variant C reached the shell and emitted:

```text
OPENIOS_IOREG_TARGET name=disp0 ... compatible=disp0,t8120|
OPENIOS_IOREG_TARGET name=AppleCLCD2 .../disp0@30000000/AppleCLCD2
```

No `IOMobileFramebuffer` appeared and the trace counters remained zero. This
shows the T8120 display-controller personality is selectable by its DT match,
but does not establish initialization, scanout, or guest framebuffer output.

## DART result

The DART-only variant made no serial progress during its 45-second bounded run
and was terminated deliberately. The observer was operational and reported
zero accesses. This is insufficient to name a wait site or call it a deadlock;
it does not justify fake DART register values.

## M10.1 ASC direct-child observation

**PASS for the observation experiment; PARTIAL for lifecycle diagnosis.**  The
separate M10.1 APFS image was populated through the reviewed disposable-image
script.  Its source and mounted destination binary SHA-256 values both were
`5905369ebac71cbddb28350f2223572eb0ed566b2fbc031f3a3453ded7670d66`.
The original M1 APFS and trustcache hashes were rechecked unchanged before
boot.  No APFS mount or M10 loop device remained after population.

The M10.1 signed inspector (CDHash
`25ff70eead3e5db9ae2ab3831e6c15df59ed127b`) ran from the actual restore
shell with an AMFI allow record and exit status zero:

```text
System Policy: bash(4) allow process-exec* /usr/local/bin/openios-ioreg
OPENIOS_IOREG_TARGET name=AppleASCWrapV6 \
  path=.../dcp@32C00000/AppleASCWrapV6 \
  class=AppleASCWrapV6| provider=AppleARMIODevice|
OPENIOS_M10_1_STATUS=0
```

The inspector calls the documented `IORegistryEntryGetChildIterator` API in
the `IOService` plane for that exact `AppleASCWrapV6` entry.  It emitted no
`OPENIOS_IOREG_CHILD` record and no iterator error.  At snapshot time the
published ASC service therefore had no direct `IOService` children.  In
particular, `AppleA7IOPNub` was not merely absent from the global target list:
it was not a direct child of its expected ASC provider.  This is still a
published-service snapshot, not proof of a particular return from
`AppleASCWrapV6::probe()` or `::start()`.

The Boot KC strings give a concrete, but static, constraint: the matching
implementation's `AppleASCWrapV6::initialize()` asserts that a core register
map and mapped core registers exist, and references `nmi-ext-irq` and
`ext-irq-reg-index`.  The DCP-only DT preserves DCP `reg`, all four interrupt
cells, `iop-version`, power/clock gates, and the RTBuddy child properties.
That establishes that these properties were not removed by this probe.  It
does not establish that IOKit resource mapping, interrupt setup, power, or
firmware preconditions completed at runtime.

The same controlled boot ended with the optional QEMU observer at zero reads
and zero writes in all 19 selected ranges.  Its scope remains unassigned CPU
memory dispatch only; this does not rule out a mapping operation, a mapped
MemoryRegion access, DMA, or a different address space.

## M10.3 MMIO observer coverage audit

**PARTIAL — the observer is working for its intentionally narrow contract.**
The pinned QEMU source calls `openios_display_mmio_trace_access()` only from
`unassigned_mem_read()` and `unassigned_mem_write()` in `system/memory.c`.
The calls occur when memory dispatch rejects an access and returns
`MEMTX_DECODE_ERROR`; no hook is present on successful mapped-region dispatch
or an IOMMU/DMA address-space path.  The DCP-only M10.1 run enabled the
observer, reached the shell, and printed its complete 19-range zero summary on
clean exit.  This proves the option was enabled and the bounded unassigned
physical-access counters were reported. It does not prove that no DCP-related
mapping operation or DMA happened.

There is no concrete guest-visible ASC/DART transition identifying an address
space or mapped memory region to instrument. Extending QEMU's global memory
dispatch or creating an inert fake MMIO region merely to generate trace events
would change the experiment and would not establish T8120 behavior. No QEMU
source change is justified for M10.3.

## M10.2 mapped-memory lifecycle observation

**PARTIAL — memory-access coverage is now verified; ASC lifecycle remains
unresolved.**  Patch `0004-trace-mapped-t8120-display-mmio.patch` extends the
existing opt-in observer without changing a transaction result.  It records
selected-range accesses at QEMU's `address_space_ld/st` and `flatview`
boundaries, including the physical address, read/write direction, size, value,
MemoryRegion name, region offset, and whether the result was mapped or
unassigned. The pre-existing unassigned callbacks remain the fallback for
unassigned dispatch.

An explicit test-only machine property,
`display-mmio-trace-test-map=on`, maps one synthetic RAM page at the first DCP
range. It is rejected unless `display-mmio-trace=on`, defaults off, and was
never used for a guest result. With CPUs paused, QEMU HMP `xp /1wx` produced:

```text
read addr=0x232c00000 ... range=dcp.0 result=mapped
origin=flatview region=openios-display-trace-test region-offset=0x0
```

Reading `0x232c02000`, outside that synthetic page but inside the DCP range,
produced:

```text
read addr=0x232c02000 ... range=dcp.0 result=unassigned
origin=memory-dispatch region=unassigned region-offset=0x232c02000
```

This is a host-controlled tracer validation, not guest DCP activity. The
patched QEMU built with `ninja -C build -j2`.

The actual DCP-only M10.1 guest was then booted with the test map off. It
reached `bash-5.3#`, the signed inspector returned
`OPENIOS_M10_2_STATUS=0`, and its service tree remained
`AppleASCWrapV6` plus `AppleDCPExpert` with no `AppleA7IOPNub` or RTBuddy. The
enhanced 19-range report remained zero reads and zero writes. This rules out
selected accesses through the newly covered CPU/flatview routes during this
restore boot; it does not cover a device-specific DMA path, a future DART
address space, interrupt registration/delivery, or prove a lifecycle return.

The normal M1 control with all tracing and test-map properties omitted also
reached `bash-5.3#`; `uname`, `id`, and the marker
`OPENIOS_M10_2_M1_STATUS=0` succeeded.

## M10.2 AppleASCWrapV6 lifecycle resolution

**PASS for lifecycle determination; root cause identified.** Through full Mach-O
disassembly of `com.apple.driver.AppleA7IOP-ASCWrap-v6` and
`com.apple.driver.AppleA7IOP` from the release 23G71 Boot KC, cross-referenced
with controlled runtime execution with `io=0x16`:

1. **`probe()` contract**:
   Neither `AppleASCWrapV6` nor `AppleA7IOP` overrides `IOService::probe()`.
   They inherit the base implementation which unconditionally returns `this`.

2. **`start()` contract and execution**:
   `AppleASCWrapV6` inherits `AppleA7IOP::start(IOService *provider)`.
   Its full execution flow was mapped:
   - Validates `provider` is `AppleARMIODevice` (panic if NULL).
   - Validates `role` property length >= 4 (DCP node role is `"DCP\0"`, length 4 — PASS).
   - Allocates lock objects (`_akfLock`, `_akfInboxLock`, `_akfOutboxLock`).
   - Maps Range 0 (`dcp.0` at 0x232c00000, size 0x6c000) via
     `provider->mapDeviceMemoryWithIndex(0, 0)` and asserts `_akfRegisterMap` and
     `_akfMappedRegs` are non-null.
   - Registers Inbox and Outbox interrupts with `IOInterruptEventSource` and
     asserts `_inboxFilter` and `_outboxFilter` are non-null.
   - Calls `initialize()`, which dispatches virtually to
     `AppleASCWrapV6::initialize()`.

3. **`AppleASCWrapV6::initialize()` execution**:
   - Maps Range 1 (`dcp.1` at 0x232850000, size 0x4000) via
     `provider->mapDeviceMemoryWithIndex(1, 0)` and asserts `_coreRegisterMap` and
     `_coreMappedRegs` are non-null.
   - Evaluates optional properties `nmi-ext-irq` and `idle-ctrl-check`.
   - Returns `true` (calls `AppleA7IOP::initialize()` stub).

4. **Why MMIO tracer recorded zero accesses**:
   IOKit's `mapDeviceMemoryWithIndex()` allocates virtual kernel memory
   (`IOMemoryMap`) and establishes page-table entries in the MMU. Neither
   `AppleA7IOP::start()` nor `AppleASCWrapV6::initialize()` reads or writes any
   hardware registers during initialization. The absence of MMIO accesses is an
   expected characteristic of the driver's initialization phase, not evidence of
   failure.

5. **Child nub publication loop and root cause of missing `AppleA7IOPNub`**:
   Immediately after `initialize()` returns `true`, `AppleA7IOP::start` calls
   `createChildNubs(provider)`:
   - Queries `provider->getChildIterator(gIODTPlane)`.
   - Iterates child entries with `iterator->getNextObject()`.
   - In `AppleA7IOPNub::withRegistryEntry(child, this)`:
     - Calls `nub->init(child, gIODTPlane)`.
     - Validates `this` is `AppleA7IOP` via `OSDynamicCast(AppleA7IOP, this)`.
     - Validates `provider` is `AppleARMIODevice` via `OSDynamicCast(AppleARMIODevice, provider)`.
     - Logs: `"AppleA7IOPNub: withRegistryEntry, 47: allocated nub %p\n"`.
     - Attaches nub to `AppleASCWrapV6` via `nub->attach(this)`.
     - Registers nub service via `nub->registerService(0)`.
   - This final inference was superseded by M10.4.  The live DCP
     `AppleARMIODevice` does have `iop-dcp-nub` as a `gIODTPlane` child.  The
     preceding snapshot does not reveal whether the child iterator was reached
     during `AppleASCWrapV6` lifecycle processing or what any initializer
     returned.

## Earliest evidence-backed blocker and next action

The root cause is not yet identified.  M10.4 confirms the required child
relationship exists at runtime and that the original child properties were
preserved.  The missing evidence is the live return path through
`AppleA7IOP::start` and `AppleA7IOPNub::withRegistryEntry`; no DT change or
QEMU behavior is justified from the current snapshot.

## M1 regression

PASS. After the experimental variants, the unmodified M1 ramdisk and original
trustcache booted with the historical separate-option invocation to
`bash-5.3#`. The guest reported Darwin 25.6.0 on iPhone15,3 and
`uid=0(root) gid=0(wheel)`; the command marker `OPENIOS_M1_STATUS=0` succeeded.
The original APFS and trustcache SHA-256 values remain those recorded in the M9
report.
