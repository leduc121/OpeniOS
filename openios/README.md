# OpeniOS

Experimental research project: an open-source iOS device emulator for Linux, built on
QEMU-based Apple Silicon emulation work.

## Status: research only. This is NOT a working iOS Simulator.

Nothing in this repository currently boots iOS on an A16 with a graphical interface.
Features below are goals, not implemented functionality.

## What upstream projects verifiably do (per their own READMEs)

| Project | Claim | Graphics |
|---|---|---|
| Inferno (this repo's base) | Emulates Apple T8030 (A13); iOS 14 guest | Yes (see Inferno-iOS) |
| darwin-vm | A12-A19 / M-series boot to a root shell | No |
| Inferno-iOS | iOS app that runs an iPhone 11 (A13, iOS 14) guest | Yes |

The gap this project targets: A16 (T8120) with a graphical iOS guest.

## Layout

- `openios/docs/`   feasibility notes, gap analysis, machine inventories
- `openios/scripts/` reproducible build scripts
- `openios/desktop/` future Qt/QML frontend (not started)
- `openios/devices/` per-device notes (iPhone 14 Pro Max, iPhone15,3, T8120)
- `third_party/`    upstream references (git-ignored; hashes in third_party/PINS.txt)

## Legal

Based on ChefKiss Inferno (GPLv3; upstream-authored code AGPLv3), derived from QEMU.
Keep upstream licenses. Do not use ChefKiss branding. No Apple firmware or decrypted
images may be committed; `firmware/` is git-ignored. Obtain firmware legitimately.
