# M8 experimental test results

| Phase | Status | Evidence |
| --- | --- | --- |
| original M1 asset integrity | PASS | v5 APFS/trustcache SHA-256 rechecked against release values |
| Mach-O link | PASS | LLVM 21.1.8 created iOS 26.6 `MH_EXECUTE` smoke binary |
| ad-hoc signing | PASS | `ldid` reports fixed identifier and `flags=0x2(adhoc)` |
| CDHash/trustcache | PASS | copied hash list and v1 trustcache have 468 entries including smoke hash |
| copied APFS insertion | PASS | M8.1/M8.2 disposable images were populated with clean unmount/loop cleanup |
| guest smoke execution | PASS | M8.2 utility ran at `bash-5.3#` with AMFI allow and exit status 0 |
| `openios-ioreg` | BLOCKED | actual runtime fails first on missing `libncurses.5.4.dylib` |
| M1 boot regression | PASS | exact historical legacy command reaches shell and executes a marker |

## M8.1 execution preflight (2026-10-29)

**BLOCKED before QEMU boot.** The disposable M8.1 image was checked after the
reported manual privileged population attempt. It still has the same SHA-256
as the source M1 image:

```text
cf39a91c5f7cce04ad27bd2fde6161e038d5f30af81672305b55938c3c0e115f
```

It contains neither the script's `mount-result.txt` / `SHA256SUMS.mounted`
evidence nor `usr/local/bin/openios-m8-smoke` in a read-only `7z` catalogue.
There is no APFS mount and no loop device attached to the disposable image.
The source M1 ramdisk and trustcache checksums remain valid.

The standalone host copy of `openios-m8-smoke` remains correctly signed, and
the copied 10,320-byte trustcache is v1 with 468 entries including its CDHash.
Those facts do not prove the executable was inserted into the image. Booting
this unmodified APFS file would not test guest execution and was intentionally
not performed.

## M8.1 populated-image boot attempt (2026-10-29)

The later preflight verified that privileged population did complete: the
experimental APFS SHA-256 is
`706db9c0fdaa33535e8153c776e6ccd27bbb5727460a31a3750e11d0466b423e`,
its catalogue contains `usr/local/bin/openios-m8-smoke` (33,584 bytes), and
the mount record identifies `/dev/loop31` followed by clean unmount/detach.
The on-image and host binary hashes both equal
`8dc91ccfbf405ac44549199bc85d01de75ba5389fcc9b760a5da4f66f2ccf10b`.

Two bounded 112-second serial boots were then run with the preserved M1 boot
arguments and `test-display=off,display-mmio-trace=off`:

1. M8.1 APFS plus its v1, 468-entry trustcache;
2. unchanged M1 APFS plus its original trustcache as a control.

Both reached kernel/APFS startup, including
`apfs_module_start: ... com.apple.filesystems.apfs`, then stopped producing
serial output after:

```text
Waiting on <dict ... IOProviderClass ... IOMedia ... Content ... Apple_HFS ...>
```

Neither emitted `bash-5.3#`, the scheduled smoke command, an
`OPENIOS_M8_SMOKE_STATUS=` marker, AMFI rejection, dyld error, or code-signing
error before QEMU was terminated by the deliberate timeout (`exit 124`). Since
the unchanged M1 control has the same bounded outcome in this host run, the
result does not isolate the populated image as the cause. It is not guest
execution evidence and Gate 2 remains **BLOCKED**.

The host smoke command was:

```sh
openios/tools/display/build_m8_macho_smoke.sh /tmp/openios-m8-smoke
```

It returned `identifier=com.openios.m8.smoke`,
`cdhash=208619c3ecb34afcedbdda7f5a22fceb48530f47`, and
`trustcache: version=1 entries=468 smoke_cdhash_present=yes`.

No DCP, DART, RTKit, GPU, display MMIO, APFS firmware, or QEMU behavior was
changed. The exact stop condition is APFS population: using the installed
experimental APFS module would require privileged operations without a safe
approved procedure.
