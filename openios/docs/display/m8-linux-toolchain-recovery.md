# M8 Recovery: Ubuntu-native Mach-O signing and trustcache

## Status

**PASS (host-side):** Ubuntu builds a minimal iOS-platform Mach-O, signs it
with repository Procursus `ldid`, extracts a 20-byte CDHash, and creates a
validated copied trustcache. **BLOCKED (guest-side):** no experimental APFS
ramdisk was made because there is no verified non-privileged APFS image writer.
No guest execution is claimed.

## Recovered toolchain

| Component | Verified result |
| --- | --- |
| signer | `ldid v2.1.5-procursus7-23-gaf86971` |
| compiler/linker | Ubuntu Clang/LLD 21.1.8, including `ld64.lld` |
| inspector | LLVM 21.1.8 `llvm-objdump` / `llvm-readobj` |
| trustcache packer | `third_party/darwin-vm/build_tc.py` |
| APFS | check/create tools only; no safe image-population workflow |

The prior claim that `ldid` was absent is corrected: it was merely not on
`PATH`.

## Reproduce

```sh
openios/tools/display/build_m8_macho_smoke.sh /tmp/openios-m8-smoke
```

The script fixes the identifier at `com.openios.m8.smoke`, so an output-file
name cannot silently alter it. It requests an arm64e iOS 26.6 object, links an
iOS Mach-O executable, and invokes:

```sh
ldid -Icom.openios.m8.smoke -Cadhoc -S openios-m8-smoke
```

The recovery run reported `CodeDirectory ... flags=0x2(adhoc)` and
`CDHash=208619c3ecb34afcedbdda7f5a22fceb48530f47`. The copied trustcache
validated as version 1, 468 entries, with this CDHash present. These results
prove packaging, not AMFI/dyld runtime acceptance.

The smoke source is intentionally a loader/signing diagnostic, not a DCP or
IORegistry program. It has no linked dylib dependency, but the normal Mach-O
`/usr/lib/dyld` loader command; actual guest loader behavior is untested.

## Link and APFS limitations

The ramdisk's `libSystem.B.dylib` is a re-export umbrella. `ld64.lld` rejects
a direct link because its `/usr/lib/system/*.dylib` re-exports are unavailable
as link-time stubs. IOKit/CoreFoundation headers and stubs are likewise absent,
so `openios-ioreg` cannot be built yet.

The M1 source hashes remain:

```text
cf39a91c5f7cce04ad27bd2fde6161e038d5f30af81672305b55938c3c0e115f  ramdisk-shell-v5.apfs
4d0df820489a76aa7dcc630b63ae6701589cc1637d0bfd526ea07f35dbe5b8a6  ramdisk-v5.tc
```

An experimental-write APFS kernel module is installed, but loading/mounting it
needs privileged operations and no reviewed metadata-preserving procedure
exists. No image copy/mount was attempted. The smallest next action is to
authorize and document an APFS-copy/populate procedure, then run only this
smoke binary with its copied trustcache before attempting IORegistry work.
