# Simulator host-shell test results

| Check | Status | Evidence |
| --- | --- | --- |
| Tk availability | PASS | Host Python reports Tk 8.6 |
| host-side configuration/QMP request | PASS | `--self-test` completes without opening a window |
| M1 command construction | PARTIAL | Code uses the preserved M1 args and assets; this UI invocation has not booted a guest |
| QMP screendump rendering | PARTIAL | implementation uses QMP `screendump`; no live QMP session was started for this host-only test |
| diagnostic framebuffer display | PARTIAL | accepts a QEMU PPM and labels it diagnostic; no iOS provenance claimed |
| mouse/touch delivery | BLOCKED | optional QMP request exists, but no verified Darwin guest input consumer |
| SpringBoard rendering | BLOCKED | no graphical userspace/DCP/display stack startup |

No firmware, APFS image, trustcache, or QEMU source was changed by the host
shell. It is independent of the M8 APFS insertion blocker.
