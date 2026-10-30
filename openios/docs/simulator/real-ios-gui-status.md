# Real iOS GUI status

| Gate | Status | Current evidence |
| --- | --- | --- |
| 1: emulator foundation | PASS | M1 restore shell and QEMU patch series were previously verified |
| 2: new guest executable | BLOCKED | host build/sign/trustcache passes; copied APFS population is not yet safe/reproducible |
| 3: DCP driver lifecycle | BLOCKED | DCP provider is published, but AppleASCWrapV6 lifecycle observation remains insufficient |
| 4: DCP/RTKit and DART | BLOCKED | no evidence-backed firmware protocol or DART behavior implemented |
| 5: guest display pixels | BLOCKED | only host diagnostic and controlled guest-RAM patterns exist |
| 6: SpringBoard/backboardd | BLOCKED | binaries exist in the System image; graphical userspace has not booted |
| 7: interactive simulator | PARTIAL | host launcher/viewer exists; it has no real iOS GUI or working guest input |

The closest accurate current product is a QEMU-SPTM restore-shell launcher with
a clearly labelled diagnostic device viewer. It is not a SpringBoard simulator.

The earliest concrete blocker remains M8's copied-APFS insertion path. A guest
smoke binary must execute with its copied trustcache before a runtime IORegistry
utility can improve evidence for AppleASCWrapV6. No speculative DCP/MMIO/GPU
responses should be added before that runtime evidence exists.
