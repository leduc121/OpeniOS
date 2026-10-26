# QEMU-SPTM host graphics console prototype

## Scope

This optional prototype verifies that the Linux QEMU-SPTM build can create a
native QEMU graphics console and render through pixman. It is **not** iOS
graphics, SpringBoard, or an emulation of DisplayPipe, DCP, GPU, DART, DMA, or
guest framebuffer hardware.

The parent OpeniOS baseline is `c2ebb62e1e`. QEMU-SPTM reports version 11.1.0
and is pinned by its containing `darwin-vm` repository at
`bad6336fb24211f8c4e8e946c259bd5b12417340`.

## Source preservation

`third_party/darwin-vm/` is ignored by the parent OpeniOS `.gitignore` and is
not present in the parent Git index. It is a separate Git repository, and
`qemu-sptm/` is in turn its submodule/nested Git worktree. Consequently, edits
made only below that directory would not be preserved by an OpeniOS commit.

The reproducible source of this prototype is therefore stored in the parent
repository as:

- `openios/patches/qemu-sptm/series`
- `openios/patches/qemu-sptm/0001-openios-host-test-display.patch`
- `openios/tools/qemu/apply-sptm-patches.sh`

Apply it from the OpeniOS root:

```sh
openios/tools/qemu/apply-sptm-patches.sh
```

The script verifies the exact QEMU-SPTM revision before changing anything. It
applies each entry from `series`, reports a fully applied patch idempotently,
and stops on partial/conflicting state. It never resets or cleans the QEMU
working tree. A clean-tree `git apply --check` against an archive of the pinned
revision passed.

## Design

`openios-test-display` is a small QOM display device with no guest-visible bus,
MMIO region, interrupt, or migration state. The Darwin machine creates it only
when its `test-display` property is enabled. It owns a 960x540
`QemuGraphicConsole`; pixman fills color bars, a checker field, and a central
registration target. GTK or SDL presents the resulting QEMU display surface.

The property defaults to false, preserving the existing M1 machine setup.

## Build

From `third_party/darwin-vm/qemu-sptm`:

```sh
mkdir -p build
cd build
../configure --target-list=aarch64-softmmu --disable-pvg --disable-werror
ninja -j2
```

`--disable-werror` is required with the tested GCC 15.2 toolchain because the
baseline `apple_aic.c` has an existing enum-pointer `sscanf` format warning.
The first build without this flag stopped at that unrelated warning; no AIC
source was changed for this prototype.

The source is linked through `hw/display/meson.build` with the existing pixman
dependency.

## Run

Add the property to the existing Darwin invocation and select an available UI:

```sh
qemu-system-aarch64 \
  -machine darwin,test-display=on \
  [existing firmware arguments] \
  -display gtk
```

Use `-display sdl` instead when the build has SDL but not GTK. Omitting
`test-display=on` leaves the prototype disabled.

For a host-only smoke test that reaches display creation before the expected
missing-firmware error:

```sh
qemu-system-aarch64 -machine darwin,test-display=on -display none
```

The device can also be instantiated with the empty machine to inspect the
pattern without any Apple firmware:

```sh
qemu-system-aarch64 -machine none -device openios-test-display -display gtk
```

## Verification record

Tested on Ubuntu with GCC 15.2, QEMU-SPTM 11.1.0, pixman 0.46.4, GTK 3.24.52,
and SDL 2.32.10:

- `ninja -j2 qemu-system-aarch64`: passed.
- `qemu-system-aarch64 -machine darwin,help`: passed; lists
  `test-display=<bool>` and its description.
- Default Darwin machine (`test-display=off`) booted the existing iOS 26.6
  ramdisk to the interactive `bash-5.3#` root-shell prompt.
- Opt-in Darwin machine (`test-display=on`) also booted to the root shell.
  `uname -a` reported Darwin 25.6.0, T8120 and iPhone15,3; `id` reported
  `uid=0(root) gid=0(wheel)`; and `ls /` completed successfully.
- Standalone host smoke (`-machine none -device openios-test-display`): passed.
  QEMU monitor `screendump` produced a 960x540 PPM containing the expected
  color bars, checker field, and registration target.
- GTK and SDL were detected by the build. The standalone SDL command initialized
  successfully and remained active until the three-second smoke timeout; its
  console surface was verified separately with `screendump`. GTK initialization
  failed against the available X display, so GTK specifically remains
  unverified in this environment.

The regression boots used these existing read-only inputs:

- `openios/firmware/linux/iphone15-3-26.6/boot/bootkc`
- `openios/firmware/linux/iphone15-3-26.6/boot/dtree`
- `openios/firmware/linux/iphone15-3-26.6/boot/sptm`
- `openios/firmware/linux/iphone15-3-26.6/boot/txm`
- `openios/firmware/linux/work/ramdisk-shell-v5.apfs`
- `openios/firmware/linux/work/ramdisk-v5.tc`

## Regression test plan

1. Build with the documented configure command and `ninja -j2`.
2. Confirm `test-display=<bool>` appears in `-machine darwin,help`.
3. Boot the pinned iOS 26.6 assets with `test-display=off`; require the root
   prompt and successful `uname -a`, `id`, and `ls /`.
4. Repeat with `test-display=on`; require the same guest results.
5. Run `-machine none -device openios-test-display`, capture QEMU monitor
   `screendump`, and verify a 960x540 image with seven bars, checker field, and
   central target. Smoke-test `-display sdl` in a graphical session.
6. Treat any guest-rendered pixels as out of scope until M2.3. This pattern is
   entirely emulator-generated diagnostic output and proves no iOS graphics,
   SpringBoard, DisplayPipe, DART, DCP, or GPU behavior.

## Limitations

- The pattern is static and generated entirely by the host.
- The guest cannot discover, configure, or draw to this device.
- It does not validate any Apple display hardware behavior.
- A visible GTK/SDL window requires a graphical Linux session and the matching
  QEMU UI backend at build time.
