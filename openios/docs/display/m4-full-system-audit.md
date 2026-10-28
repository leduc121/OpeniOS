# M4 full iOS 26.6 boot-environment audit

## Scope

This audit advances beyond the restore-ramdisk inventory by acquiring the
complete official restore IPSW for `iPhone15,3`, iOS 26.6 build `23G71`.  The
known-good M1 Boot KC, Device Tree, SPTM, TXM, ramdisk, and trustcache are not
overwritten.  Downloaded and extracted material lives under separate paths.

The audit does not equate possession of a System image with a bootable iOS
installation.  A normal graphical boot also needs the correct APFS volume
group, Preboot metadata, Data volume state, keybags, trust policy, and device
services.

## Official restore source and integrity

- Device identifier: `iPhone15,3` (iPhone 14 Pro Max / D74AP).
- Product version: iOS 26.6.
- Product build: `23G71`.
- Filename: `iPhone15,3_26.6_23G71_Restore.ipsw`.
- Expected size: `10,479,268,599` bytes.
- Expected SHA-256:
  `90e93d2fd2f16f6e3cf379723ea0345006076fbb11fea45ca659cd917b7ef114`.
- Source: [Apple CDN](https://updates.cdn-apple.com/2026SummerFCS/fullrestores/140-57822/5E2D7120-DF74-40A8-AEE4-0BF4A268D867/iPhone15,3_26.6_23G71_Restore.ipsw).

The local file has exactly that size and SHA-256, and `unzip -tq` completed
without an error.  `BuildManifest.plist`, `Restore.plist`, and
`SystemVersion.plist` independently identify `iPhone15,3`, board `d74ap`,
platform `t8120` (CPID `0x8120`), and build `23G71`.

Before download, the filesystem had 172 GiB free and the existing OpeniOS
firmware directory used 2.8 GiB.  The download was resumable and targeted
`openios/firmware/downloads/`; it did not replace an existing file.

## Local baseline before full IPSW extraction

The pre-existing set contained:

- matching Boot KC, Device Tree, SPTM and TXM;
- one approximately 232 MB restore DMG;
- restore shell APFS images and generated trustcaches;
- no `.ipsw`, complete System image, or installed System/Data volume group.

The restore ramdisk contains IOSurface, IOMobileFramebuffer and MiniDisplay
framework binaries, but its active launchd directory contains only
`com.jprx.bash.plist`.  SpringBoard, backboardd, and WindowServer are absent.

## Volume and boot requirements

An iOS restore archive normally supplies images and manifests used to create a
sealed APFS System/Data volume group; it is not itself an already personalized
and bootable installation.  The following relationships must be preserved:

1. A matching sealed System volume and its snapshot/seal metadata.
2. Preboot content which selects the System snapshot and supplies matching
   boot/kernel metadata.
3. A paired Data volume with the expected firmlinks, ownership, preferences,
   mobile user state, and keybag/protection classes.
4. Matching dyld shared caches and launchd databases from the System build.
5. Platform signatures, entitlements, AMFI policy, and trustcaches for every
   executable introduced into the boot path.
6. Device identity and SEP-backed services needed by graphical session and
   security daemons.

The current QEMU `ramdisk=` path exposes one APFS restore volume as `md0`; it
does not model an installed iOS volume group or the full restore/personalization
workflow.  Connecting a System image as another ramdisk would not satisfy these
relationships.

## Restore components and APFS roles

The 125-entry archive contains these relevant images:

| Manifest role | Archive member | Size (bytes) | Observation |
| --- | --- | ---: | --- |
| `OS` | `094-95332-083.dmg.aea` | 7,851,737,088 | Encrypted System image |
| `Cryptex1,SystemOS` | `094-97212-084.dmg.aea` | 2,013,265,920 | Encrypted cryptex containing dyld caches |
| `Cryptex1,AppOS` | `094-96441-087.dmg` | 14,680,064 | App cryptex |
| restore ramdisk | `094-95379-087.dmg` | 232,783,899 | Restore environment |
| alternate restore ramdisk | `094-96961-086.dmg` | 234,881,051 | Restore environment |

The BuildManifest also supplies System canonical metadata (mtree), System and
cryptex root hashes, trustcaches, DCP/RestoreDCP, and AGX firmware.  It does not
contain an installed Data volume or a completed System/Data volume group.
The Device Tree's filesystem table requires System (role 1), Preboot (16),
Data (64), Baseband-Data (128), Update (192), xART (256), and Hardware (320)
relationships in a normal environment.  Device-recovery substitutes an
ephemeral Data filesystem instead.

## Read-only graphical userspace inventory

The main AEA was decrypted with Apple's public FCS response into a separate,
ignored research directory.  `file` and 7-Zip identify a 9,191,817,216-byte
APFS image named `LuckG23G71.D74OS.apfs`, containing 215,536 files.  No mount,
write, or kernel APFS driver was needed.  The Cryptex SystemOS AEA was likewise
decrypted and inspected read-only.

| Item | Verified location/result | SHA-256 where extracted |
| --- | --- | --- |
| SpringBoard | `System/Library/CoreServices/SpringBoard.app/SpringBoard`, arm64e Mach-O | `c6b02e993582a5f6db5c8bf65b68c0102442db2fc72830a7699fe1811231c57c` |
| SpringBoard launch record | `System/Library/LaunchDaemons/com.apple.SpringBoard.plist` | `30a04d78624e2ec5274aacf1882470b030df1d3552a87fa37eac0428aaa19222` |
| backboardd | `usr/libexec/backboardd`, arm64e Mach-O | `568981136cadc227adc3f2a44aeab38633f2e12417d8fa772ef22f3f8618d632` |
| backboardd launch record | `System/Library/LaunchDaemons/com.apple.backboardd.plist` | `9ed8de08ce06ffce8cf455a91d11f86bbe1e0a69d76be91db7e192ce587a567b` |
| arm64e dyld cache | Cryptex `System/Library/Caches/com.apple.dyld/dyld_shared_cache_arm64e` plus 83 subcaches | present |
| WindowServer | no standalone executable or launch plist in either inspected APFS catalogue | not found as a separate file |

Absence of a standalone WindowServer does not imply absence of composition:
the backboardd launch record publishes `com.apple.CARenderServer` and
`com.apple.backboard.display.services`, and much implementation is supplied by
the dyld shared cache.  Conversely, binary presence is not runtime activation.

The decisive launch-policy evidence is
`com.apple.SpringBoard.plist`: `LimitLoadFromHardware.osenvironment` excludes
both `device-recovery` and `diagnostics`.  It runs as user `mobile`, uses the
`App` spawn type, and depends on a broad set of FrontBoard, UIKit, bulletin,
RunningBoard, status, and notification Mach services.  backboardd also runs as
`mobile` and publishes the display and render-server services.  The current
restore ramdisk has neither this complete service database nor the installed
Data/Preboot state.  Copying the two executables into it would therefore not
constitute a legitimate graphical boot.

No signing, sealing, keybag, or personalization requirement is bypassed by
this audit.

## Security constraints

Archive integrity does not supply a personalized restore ticket.  The
BuildManifest marks both DCP images as personalized components; normal DCP is
not loaded by iBoot while RestoreDCP is.  Any signing-status statement would
require a live Apple authorization check and is deliberately not inferred
from the static archive.

The M1 trustcache covers the known restore-shell contents.  It is not assumed
to trust full graphical userspace, and it is never modified in place.  Any
future controlled boot must use copied assets and a separately documented
trust/signing experiment.

## Practical boot gap

The shortest defensible path to graphical userspace has two independent
blockers:

- filesystem: construct and mount a coherent, read-only System/Preboot plus
  copied Data-volume environment that gets launchd beyond restore mode;
- hardware: attach AppleASCWrapV6/RTBuddy and bring up evidence-backed DCP and
  display-DART transport until IOMobileFramebuffer publishes a service.

Neither track can substitute for the other.  SpringBoard cannot run from the
current shell ramdisk, and a full System filesystem cannot produce pixels
without the kernel display provider chain.

## Preservation and commit plan

No commit was made.  A clean parent-repository plan is:

1. Commit the completed M2 guest-memory framebuffer patch, test script, series
   update, and sprint report as one reproducibility-focused change.
2. Commit the M3 Device Tree probe tool and the two M3 research reports as a
   separate research change.
3. Commit the two M4 reports plus Boot-KC inspection tool as a third change.
4. Keep downloaded IPSW/images out of Git; track only hashes, source metadata,
   and extraction commands.

Before any authorized commit: run `git diff --check`, rerun the patch apply
idempotency test against pinned QEMU, and review `git status` so no firmware or
large binary is staged.

## Regression status

M4 introduced no QEMU source change and required no rebuild.  The existing
patch apply script reports `QEMU-SPTM patch series already applied` at pinned
revision `bad6336fb24211f8c4e8e946c259bd5b12417340`; both parent and nested
`git diff --check` pass.

On 2026-10-28, the following trace-off/default-display M1 command again reached
the interactive `bash-5.3#` prompt (the serial transcript also identifies the
environment as `Restore environment starting`):

```sh
timeout 90s third_party/darwin-vm/qemu-sptm/build/qemu-system-aarch64 \
  -machine darwin,bootkc=openios/firmware/linux/iphone15-3-26.6/boot/bootkc,\
dtree=openios/firmware/linux/iphone15-3-26.6/boot/dtree,\
sptm=openios/firmware/linux/iphone15-3-26.6/boot/sptm,\
txm=openios/firmware/linux/iphone15-3-26.6/boot/txm,\
ramdisk=openios/firmware/linux/work/ramdisk-shell-v5.apfs,\
tc=openios/firmware/linux/work/ramdisk-v5.tc,\
args='rd=md0 serial=3 -v -noprogress wdt=-1 wlan-olyhal-abort',\
test-display=off,display-mmio-trace=off \
  -display none -monitor none -serial stdio
```

The identical command with `test-display=on` (still `-display none` for this
serial regression) also reached `bash-5.3#`.  This verifies that the optional
diagnostic console remains non-disruptive to the M1 restore boot.  It does not
assert that an SDL/GTK surface was displayed in this run; that remains the
separate M2 screendump verification.

The M4 `io=0xffff` run was a bounded diagnostic, not a replacement for this
regression.  No M4 QEMU source change was made, so no rebuild was necessary;
the pre-existing build remains the GCC 15 `--disable-werror` build described
in the M2 documentation.  No SpringBoard, display-driver initialization, or
iOS GUI is claimed.
