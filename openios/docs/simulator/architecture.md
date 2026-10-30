# OpeniOS simulator host shell

`openios/tools/simulator/openios_simulator.py` is a Linux/Tk host shell for the
existing QEMU-SPTM Darwin machine. It is not an iOS UI implementation.

```text
Tk device frame / controls
        |                         \
QMP screendump + optional input     serial file tail
        |                             |
QEMU-SPTM Darwin machine -------- iOS restore guest
        |
actual QEMU DisplaySurface (when a guest-capable display device exists)
```

The host UI launches the known M1 restore-shell configuration with
`test-display=off`, `display-mmio-trace=off`, `-display none`, a private QMP
socket, and a serial-log file. It polls QMP `screendump` only on explicit user
capture. Thus the device-frame canvas can show actual QEMU pixels when
available, including the existing diagnostic device, but it cannot manufacture
SpringBoard pixels.

The yellow provenance label is deliberate:

- no framebuffer: `NO GUEST FRAMEBUFFER`;
- selected PPM: `QEMU DIAGNOSTIC FRAMEBUFFER — NOT IOS UI`;
- active QMP capture: QEMU framebuffer with provenance determined by the
  active guest device.

QMP pointer injection is disabled by default. If explicitly enabled it uses
`input-send-event`; no claim is made that the Darwin machine currently has a
guest input device which consumes those events.

## Running

```sh
python3 openios/tools/simulator/openios_simulator.py
python3 openios/tools/simulator/openios_simulator.py --diagnostic-ppm /tmp/frame.ppm
python3 openios/tools/simulator/openios_simulator.py --self-test
```

Tk 8.6 is used because neither PySide6 nor PyQt6 is installed. The application
does not add dependencies, change firmware, or modify QEMU source.
