# M8 userspace IORegistry observability

## Result: PARTIAL — Ubuntu can build, sign, and trust-cache a minimal Mach-O; APFS insertion remains blocked

## Scope

M8 re-evaluated userspace observation before considering a custom Boot KC. It
did not modify, mount writable, or boot a changed M1 ramdisk or trustcache.
The target remains a read-only view of services published in the IORegistry;
such a snapshot would not by itself prove IOCatalogue candidate selection,
`probe()`, or `start()`.

## Corrected signing conclusion

The earlier M8 conclusion that `ldid` was unavailable was false. It was not on
`PATH`, but the repository contains a working Procursus executable:

```text
third_party/ldid/ldid
Link Identity Editor v2.1.5-procursus7-23-gaf86971
```

The local M1 artifacts remain unchanged: `ramdisk-shell-v5.apfs`,
`ramdisk-v5.tc`, `all_hashes-v5`, and `v5-signing-manifest.tsv`.
`build_tc.py` packages 20-byte CDHashes into a version-1 trustcache; it does
not sign a binary. `ldid -h` supplies the CDHash from the signed Mach-O.

Ubuntu also has Clang, `ld64.lld`, `llvm-objdump`, and `llvm-readobj` from LLVM
21.1.8. `openios/tools/display/build_m8_macho_smoke.sh` verifies the complete
host-side build/sign/hash/package sequence without changing any firmware.

The actual recovery run produced a structurally valid iOS 26.6 Mach-O with
fixed identifier `com.openios.m8.smoke` and the historically required signing
flags:

```text
ldid -Icom.openios.m8.smoke -Cadhoc -S openios-m8-smoke
CodeDirectory ... flags=0x2(adhoc)
CDHash=208619c3ecb34afcedbdda7f5a22fceb48530f47
```

That 20-byte hash was added only to a copied hash list. The generated copied
trustcache passed a structural check (`version=1`, 468 entries, hash present).
This is host-side evidence only; it does not prove AMFI, dyld, or guest runtime
acceptance.

## Existing `ioreg` dependency closure

Read-only inspection of existing arm64e `usr/sbin/ioreg` identifies direct
install names:

```text
/usr/lib/libncurses.5.4.dylib
/usr/lib/libSystem.B.dylib
/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation
/System/Library/Frameworks/IOKit.framework/Versions/A/IOKit
```

The known-good restore ramdisk includes `ioreg`, `libSystem.B.dylib`, and
`dyld`, but not `libncurses.5.4.dylib`, CoreFoundation, or a compatible shared
cache. Its observed failure is:

```text
dyld: Library not loaded: /usr/lib/libncurses.5.4.dylib
Reason: ... no dyld cache
```

The read-only 23G71 image catalogue did not provide a verified matching
`libncurses.5.4.dylib`. Copying arbitrary libraries or an incomplete
System/Cryptex dependency closure remains unjustified.

## Custom query feasibility

A minimal real utility could traverse `IORegistryEntry` APIs and report DCP,
AppleASCWrapV6, AppleA7IOPNub, RTBuddy, AppleDCPExpert, AppleCLCD2, and
provider-child paths. It cannot be built yet because the local material has no
iOS SDK IOKit headers or link-time framework stubs. The M1 ramdisk's
`libSystem.B.dylib` is a re-export umbrella; direct linking fails until its
many `/usr/lib/system/*.dylib` re-export dependencies are supplied as valid
link-time stubs.

## Runtime insertion boundary

The host can now produce the binary and copied trustcache, but not a safe,
bootable copied ramdisk. Installed `apfsprogs` provides check/create tools;
there is no verified non-privileged APFS image-population tool. An installed
APFS module advertises experimental write support, but loading/mounting it
would be privileged and no approved metadata-preserving procedure exists.
No APFS copy, mount, or guest test was attempted.

## Decision

M8 is blocked before guest execution by APFS insertion, not by the compiler,
ad-hoc signer, or trustcache generator. The smallest next action is an
explicitly authorized, documented APFS-copy/population procedure. Validate it
first by inserting only the M8 smoke executable into a copied v5 ramdisk and
booting it with its copied trustcache. Only after that passes should work begin
on an IOKit/IORegistry utility.

## M1 regression

M8 Recovery changed no boot asset or QEMU source. Original M1 APFS and
trustcache hashes were rechecked against their release values; the most recent
actual root-shell regression remains the post-M6 boot to `bash-5.3#`.
