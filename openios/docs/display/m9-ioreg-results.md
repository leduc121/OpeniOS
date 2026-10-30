# M9 read-only IORegistry probe

## Status: PASS — read-only IORegistry snapshot captured in the guest

M8.2 established a real signed-Mach-O guest execution path.  M9 avoids the
existing `ioreg` binary because it imports ncurses; this is a small, read-only
IOService-plane enumerator, not a substitute display driver or DCP emulator.

## Verified runtime closure

The disposable M8.2 APFS already contains the matching iOS 26.6 IOKit runtime,
CoreFoundation, and the direct IOKit dependencies (`libenergytrace`, `libz`,
`libbsm`, `libobjc`, `libicucore`, Foundation, and CoreServicesInternal).  It
does **not** contain `/usr/lib/libncurses.5.4.dylib`, which is why the stock
`ioreg` fails before it can query the registry.

The matching Cryptex shared-cache catalogue includes all four install names:

```text
/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation
/System/Library/Frameworks/IOKit.framework/Versions/A/IOKit
/usr/lib/libSystem.B.dylib
/usr/lib/libncurses.5.4.dylib
```

It is not necessary to extract or inject a cache library for the M9 program:
the program does not use ncurses and directly imports only IOKit and libSystem.

`llvm-objdump` on the 23G71 IOKit binary confirmed all used exports:
`IORegistryCreateIterator`, `IOIteratorNext`, `IORegistryEntryGetNameInPlane`,
`IORegistryEntryGetPath`, and `IOObjectRelease`.  The iterator definition and
`kIORegistryIterateRecursively=0x1` come from Apple’s source-available
`IOKitLib.h`.

## Built diagnostic

`openios/tools/display/m9_ioreg.c` walks the published `IOService` plane and
emits only exact-name matches for the display chain:

```text
AppleASCWrapV6 AppleA7IOPNub RTBuddy AppleDCPExpert AppleCLCD2
IOMobileFramebuffer dart-disp0 dart-dcp dart-dispgrt dcp disp0
```

It prints paths for any matching published service, then exits.  It neither
opens a user client nor writes a registry property.  Consequently, even a
successful snapshot can establish publication and relationships only; it
cannot by itself prove personality selection, `probe`, or `start`.

The host build command is:

```sh
openios/tools/display/build_m9_ioreg.sh /tmp/openios-m9-ioreg-build
```

The verified build output has:

```text
identifier: com.openios.m9.ioreg
CDHash: 38653f1d687ac7f314df5e3dff93448990816a27
trustcache: version 1, 468 entries, hash present
Mach-O dependencies: IOKit.framework/Versions/A/IOKit, /usr/lib/libSystem.B.dylib
```

## M9 guest execution

The user-authorized population script completed on the disposable M9 image.
It recorded `/dev/loop31`, inserted a byte-identical probe, then unmounted and
detached it.  No APFS mount or loop device remained afterwards.  The generated
trustcache is version 1 with 468 entries and contains the probe CDHash.

The known-good legacy invocation booted the actual guest with the M9 ramdisk
and trustcache, preserving the original Boot KC, SPTM, TXM, normal fixed-up
Device Tree, memory size, and boot arguments.  The guest reached `bash-5.3#`.
Its actual serial transcript is:

```text
System Policy: bash(4) allow process-exec* /usr/local/bin/openios-ioreg
OPENIOS_IOREG_BEGIN
OPENIOS_IOREG_TARGET name=dcp path=IOService:/AppleARMPE/arm-io@10F00000/AppleT812xIO/dcp@32C00000
OPENIOS_IOREG_TARGET name=disp0 path=IOService:/AppleARMPE/arm-io@10F00000/AppleT812xIO/disp0@30000000
OPENIOS_IOREG_TARGET name=dart-dcp path=IOService:/AppleARMPE/arm-io@10F00000/AppleT812xIO/dart-dcp@3130C000
OPENIOS_IOREG_TARGET name=dart-disp0 path=IOService:/AppleARMPE/arm-io@10F00000/AppleT812xIO/dart-disp0@31304000
OPENIOS_IOREG_TARGET name=dart-dispgrt path=IOService:/AppleARMPE/arm-io@10F00000/AppleT812xIO/dart-dispgrt@31350000
OPENIOS_IOREG_DONE targets=nonzero entries=nonzero
OPENIOS_IOREG_STATUS=0
```

There was no dyld error, trustcache rejection, or AMFI rejection.  The probe
reported the expected Device Tree nubs and their direct provider paths.  It did
not report `AppleASCWrapV6`, `AppleA7IOPNub`, `RTBuddy`, `AppleDCPExpert`,
`AppleCLCD2`, or `IOMobileFramebuffer` anywhere in the published IOService
tree.

This is evidence of **service publication only**.  The normal M1 Device Tree
fixup deliberately removes the unsupported DCP/display matching compatibles,
so this normal-boot result is not evidence that AppleASCWrapV6 was considered
or rejected.  It does establish that no display driver service is already
published beneath these nubs in the working restore configuration.

## Follow-up property probe

The initial program was extended to use the source-backed, deprecated
`IORegistryEntryGetProperty` API to print each selected nub's raw `compatible`
property.  This will directly confirm which compatible values survive the
normal QEMU Device Tree fixup, without serializing CF properties or writing to
the registry.  Its host-side build is reproducible and passed with:

```text
identifier: com.openios.m9.ioreg
CDHash: 3a9c82a8a4fec2fcfc9795a1240cb7759ca9e4bb
trustcache: version 1, 468 entries, hash present
```

It required a distinct disposable image/trustcache pair because the executable
and its CDHash changed.  M9.1 population completed and the guest returned zero.
In the normal fixed-up machine, each selected DT nub returned
`compatible=<unavailable>`; this is direct runtime evidence that the fixup
removes the matching property.

## Experimental image and authorization boundary

Prepared, ignored assets are:

```text
openios/firmware/linux/experiments/m9-ioreg-20261029/ramdisk-shell-m9.apfs
openios/firmware/linux/experiments/m9-ioreg-20261029/ramdisk-m9-ioreg.tc
openios/firmware/linux/experiments/m9-ioreg-20261029/openios-ioreg
```

Before modification the new APFS copy has SHA-256
`78f6dd207f3d074387cb3197b7c98dd75c994a6738ce0d22084abfbfe609ade1`.
The probe binary SHA-256 is
`7414d7f3e8f2a4b7aa0592647ca4cdf3cbc90e84cf1e574903a10c36f83b1a3e`.

`openios/tools/display/m9_mount_ioreg_image.sh` was deliberately root-only and
refused any image whose pre-insertion hash differed.  It mounted only volume 0
of the disposable image, installed the already signed byte-identical binary,
then unmounted and detached the exact loop device.

The M9/M9.1 runs used the proven legacy QEMU form, changing only `-ramdisk`
and `-tc`, then ran:

```text
/usr/local/bin/openios-ioreg; echo OPENIOS_IOREG_STATUS=$?
```

## Baseline safety

The known-good M1 assets remain unchanged:

```text
cf39a91c5f7cce04ad27bd2fde6161e038d5f30af81672305b55938c3c0e115f  ramdisk-shell-v5.apfs
4d0df820489a76aa7dcc630b63ae6701589cc1637d0bfd526ea07f35dbe5b8a6  ramdisk-v5.tc
```

## Earliest evidence-backed display blocker

The earliest runtime boundary is now stronger than the prior serial-only
observation: AppleARMPE publishes the display/DCP/DART nodes, but the working
fixed-up restore configuration has no published ASC, RTBuddy, DCP expert,
CLCD2, or mobile-framebuffer services.  This does **not** identify a hardware
register failure; DCP matching is intentionally suppressed by the normal
Device Tree fixup.  No QEMU DCP, DART, RTKit, GPU, or framebuffer behavior was
added.

## Next action

M9.1 is complete.  The controlled compatible-property results and the next
runtime boundary are recorded in `m10-dcp-rtkit-results.md`.
