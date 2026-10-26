# OpeniOS M1 — iOS Root Shell

Device: iPhone 14 Pro Max
Model: iPhone15,3
Board: D74AP
SoC: A16 / T8120
iOS: 26.6 (23G71)
Darwin: 25.6.0

Host: Ubuntu Linux
Emulator: QEMU-SPTM

Status:
- Darwin kernel boot: PASS
- APFS ramdisk mount: PASS
- dyld/launchd initialization: PASS
- Interactive Bash root shell: PASS
- uname/id/ls execution: PASS
- iOS GUI: NOT IMPLEMENTED
- SpringBoard: NOT IMPLEMENTED
- Hot reload: NOT IMPLEMENTED

Boot artifacts:
- openios/firmware/linux/iphone15-3-26.6/boot/
- openios/firmware/linux/work/ramdisk-shell-v5.apfs
- openios/firmware/linux/work/ramdisk-v5.tc

Known issues:
- Experimental Linux APFS write support
- Incomplete restore ramdisk user space
- Missing system services
