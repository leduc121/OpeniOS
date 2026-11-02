# OpeniOS — Feasibility Notes (Milestone 0, Updated)

**Updated:** 2026-11-02  
**Scope:** Ubuntu-only OpeniOS development; iPhone 14 Pro Max (`iPhone15,3`, D74AP/T8120), iOS 26.6 (23G71).  
**Evidence basis:** Prior OpeniOS build, boot, GDB, guest logs and implementation reports provided by the project team. This document does not claim an independent rerun of the repository on 2026-11-02.

**Status legend:** **VERIFIED (reported runtime)** = observed in project build/guest/log reports; **VERIFIED (reported source)** = supported by reviewed code or assets; **PARTIAL** = limited functionality demonstrated; **NOT VERIFIED** = not yet established; **EXTERNAL CLAIM** = upstream project statement only.

## Host

- **VERIFIED (reported):** AMD Ryzen 5 5500U (6 cores/12 threads), x86-64 Ubuntu, approximately 14 GiB RAM and 4 GiB swap; Hyprland/Wayland environment.
- **VERIFIED (reported):** No ARM64 host hardware virtualization. iPhone A16/T8120 guest execution uses QEMU TCG; performance and scalability are not yet suitable to assume daily-use native-app emulation.
- **VERIFIED (reported):** Linux toolchain includes LLVM, `ldid`, and `gdb-multiarch`. QEMU's local GDB stub has been used to capture real guest kernel behavior.

## Upstream and builds

- **VERIFIED (reported source):** Inferno includes Apple Silicon machine implementations such as `s8000` and `t8030`; T8120 support in this project is pursued through a separate QEMU-SPTM/darwin machine path, not an Inferno T8120 machine.
- **VERIFIED (reported build):** Inferno QEMU was built on Ubuntu; its `qemu-system-aarch64` binary and `s8000`/`t8030` machines were identified. This does **not** mean Inferno can boot the target A16 GUI.
- **VERIFIED (reported build):** QEMU-SPTM 11.1.0 was built on Ubuntu, with `-M darwin` available. The project uses a pinned QEMU-SPTM source revision (`bad6336fb24211f8c4e8e946c259bd5b12417340`).
- **EXTERNAL CLAIM (not independently revalidated here):** Other upstream forks report iOS root-shell and, for different hardware/iOS generations, graphical experiments. Such claims are not evidence that SpringBoard works on OpeniOS A16.

## Target device and iOS boot

- **VERIFIED (reported runtime):** OpeniOS has booted **iPhone 14 Pro Max (`iPhone15,3`, D74AP/T8120)** with iOS **26.6 (23G71)** / Darwin **25.6.0** into the genuine guest `bash-5.3#` root shell using QEMU-SPTM.
- **VERIFIED (reported runtime):** Known-good boot uses separate `-M darwin` and `-args 'rd=md0 serial=3 -v -noprogress wdt=-1 wlan-olyhal-abort'` options, with Boot KC, Device Tree, SPTM, TXM, ramdisk and trustcache assets.
- **VERIFIED (reported runtime):** M1 regression boot and guest command markers repeatedly passed. Original experimental baseline ramdisk and trustcache hashes were preserved in the reported runs.
- **VERIFIED (reported tooling):** On Ubuntu, experimental APFS ramdisk preparation, Mach-O build/signing and trustcache-based guest execution were demonstrated. This is **not** a claim that every macOS-specific IPSW preparation or personalization step is fully replaced.

## Kernel/device bring-up (through M13 checkpoint)

- **VERIFIED (reported runtime):** `AppleASCWrapV6` and `AppleDCPExpert` matched; IOMMU matching for DCP uses `IOMapperID = 0xad`.
- **VERIFIED (reported runtime):** SPTM DART bootstrap required a `dart-id` property, and an exact 256-byte `random-seed` property was necessary for the tested Device Tree transformations.
- **VERIFIED (reported runtime):** Controlled configurations with `dart-dcp`, `dart-disp0`, and `dart-dispgrt` reached the guest shell with distinct experimental DART IDs (0, 1, 2). This verifies boot compatibility in those tests, **not** full DART DMA correctness.
- **VERIFIED (reported runtime):** `AppleA7IOPNub` allocation occurred and `RTBuddy(DCP)::start()` returned `w0 = 1` after an experimental DCP Expert MMIO mapping avoided a previously observed data abort.
- **VERIFIED (reported runtime):** `AppleCLCD2` matched and appeared in the guest IORegistry beneath `disp0`.
- **PARTIAL:** Zero-backed/limited MMIO mapping and driver publication do **not** prove ASC/RTKit handshakes, DCP firmware execution, framebuffer scanout or AGX GPU support.

## Full iOS userspace

- **VERIFIED (reported source analysis):** The restore ramdisk boot argument `rd=md0` was identified in `launchd` as a trigger for its restore-environment path.
- **VERIFIED (reported asset inventory):** Matching iOS System APFS and Cryptex images, dyld shared cache and relevant Apple trustcache entries were identified; SpringBoard and backboardd binaries/signatures were inspected.
- **NOT VERIFIED:** Boot of the complete normal iOS userspace, functioning `backboardd`/CARenderServer, executing SpringBoard, and app launching.
- **NOT VERIFIED:** Real guest-originated framebuffer pixels, functional iPhone display output, full AGX rendering and touch input.

## Separate product: OpeniOS Live Preview

- **VERIFIED (reported implementation/runtime):** An independent Ubuntu desktop Live Preview app was built under `openios/live_preview/` using GTK/WebKit, with a floating iPhone-style window.
- **VERIFIED (reported runtime):** React/Vite app rendering, interactive input and HMR were tested. A later report lists 19 passing unit/integration tests and screen-edge clipping fixes.
- **PARTIAL:** Expo Web and Flutter Web adapters exist, but detection/configuration checks alone are not proof of a full end-to-end live-update experience for every project.
- **IMPORTANT:** The welcome/Home screen in Live Preview is **HTML/CSS artwork**, not real SpringBoard or an iOS guest. Live Preview is a separate, useful developer feature; it does not establish native iOS emulation.

## Remaining blockers / next milestones

1. **Native boot (M13):** Prepare an isolated bootable full System/Cryptex setup and verify normal `launchd` services beyond restore mode.
2. **Coprocessor (M11):** Establish actual ASC mailbox traffic, RTKit handshake and DCP firmware state using runtime evidence.
3. **Display (M12):** Prove correct DART/DMA handling, framebuffer ownership and changing **guest-originated** pixels in QEMU.
4. **Graphics/userspace (M14–M16):** Bring up required compositor/GPU services, actual SpringBoard rendering, touch and app launch.
5. **Live Preview product:** Continue end-to-end Expo/Flutter tests, packaging and stability without modifying or misrepresenting the native-emulator research.

## Current milestone conclusion

**Milestone 0 feasibility questions about building on Ubuntu, booting `iPhone15,3`, and executing diagnostic binaries on Linux have been answered positively in reported experiments.** Native graphical iOS emulation on A16 remains an open, high-complexity research objective. OpeniOS Live Preview is already a separate functional preview path but does **not** run iOS.
