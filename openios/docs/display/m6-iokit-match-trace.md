# M6 AppleASCWrapV6 IOKit matching trace

## Result: PARTIAL — static eligibility confirmed; runtime lifecycle remains unobservable in the restore image

## Static personality comparison

The active iOS 26.6 Boot KC contains
`com.apple.driver.AppleA7IOP-ASCWrap-v6` version 1.0.2.  Its `AppleASCWrapV6`
personality has:

| Personality field | Value | DCP DT evidence |
| --- | --- | --- |
| `IOProviderClass` | `AppleARMIODevice` | AppleARMPE publishes the DCP DT node as a service |
| `IONameMatch` | `iop,ascwrap-v6`, `iop,ascwrap-v7` | original D74AP DCP has `compatible=iop,ascwrap-v6` |
| `IOPropertyMatch` | absent | no additional property constraint in the personality |
| bundle libraries | AppleA7IOP, AppleARMPlatform, IOSlaveProcessor | statically present in the Boot KC dependency metadata |

The DCP-only generated DT starts from `dtree.original`, applies normal QEMU
fixup, then restores only `dcp`, `iop-dcp-nub`, and `dcp0-expert` compatible
properties.  It preserves DCP MMIO ranges, interrupts, `iop-version=1`, power
and clock gates, IOMMU parent, RTBuddy child flags, and all other source
properties.  SGX remains removed.

Therefore AppleASCWrapV6 is statically eligible to be considered for the live
DCP provider.  This is not proof that an in-memory IOCatalogue match occurred,
that its executable was linked, or that `probe`/`start` ran.

## Runtime method and evidence

The bounded DCP-only run used a generated `/tmp` DT, known-good M1 boot
arguments, `display-mmio-trace=on`, and `io=0xffff`.  It logged publication of:

```text
.../AppleT812xIO/dcp@32C00000
.../AppleT812xIO/dcp0-expert@3D2B8044
.../AppleT812xIO/disp0@30000000
.../AppleT812xIO/dart-dcp@3130C000
.../AppleT812xIO/dart-disp0@31304000
.../AppleT812xIO/dart-dispgrt@31350000
```

It did not log an AppleASCWrapV6, AppleA7IOPNub, RTBuddy, AppleDCPExpert, or
AppleCLCD2 registration.  The QEMU observer printed `reads=0 writes=0` for all
19 selected DCP/DART/display ranges.  The run was terminated by its 100-second
timeout before shell startup.

This establishes only an observable boundary after provider publication and
before a visible ASC service registration/selected access.  It does not say
whether matching was rejected, a kext failed to load, or probe/start waited on
a resource.  `io=0xffff` is deliberately classified as high-volume and
perturbing: it is not used as a successful lifecycle trace.

## Read-only registry alternatives

The restore APFS contains `/usr/sbin/ioreg`, but executing it in a normal M1
boot fails because `/usr/lib/libncurses.5.4.dylib` and a usable dyld cache are
absent.  `kextstat`, `grep`, and an equivalent static query tool are absent.
This is raw runtime evidence that the minimal restore userspace cannot inspect
IORegistry; it is not evidence against DCP matching.

Apple's source-available XNU includes `IOCatalogue.cpp` and `IOKitDebug.cpp`,
but that establishes an implementation facility rather than a guarantee that
the release 23G71 kernel exposes a compatible boot argument or enough logging.
No signed-kernel patch was attempted.

## Driver lifecycle table

| Stage | AppleASCWrapV6 | RTBuddy | AppleDCP/CLCD2 |
| --- | --- | --- | --- |
| personality available statically | yes | yes | yes |
| provider nub published | DCP published | child compatible present | DCP expert/disp nubs published |
| runtime catalogue match | unknown | unknown | unknown |
| probe entered/result | unknown | unknown | unknown |
| start entered/result | unknown | unknown | unknown |
| selected MMIO access | none observed | none observed | none observed |

## Smallest next step

The next evidence-backed improvement is an opt-in, log-only kernel match hook
for this exact personality/provider pair—only if a safe source-compatible
instrumentation build becomes available.  It must report candidate,
provider-class/name and probe result without changing matching.  Until then,
the earliest confirmed blocker is insufficient runtime observability, not a
specified DCP register behavior.
