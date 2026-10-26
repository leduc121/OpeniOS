# D74AP / T8120 display hardware inventory

## disp0
- device_type: `display-subsystem`
- reg: `[{'addr': 805306368, 'size': 6881280}, {'addr': 813694976, 'size': 6881280}, {'addr': 825360384, 'size': 16384}, {'addr': 825491456, 'size': 16384}, {'addr': 825507840, 'size': 16384}, {'addr': 847249408, 'size': 8388608}, {'addr': 993853440, 'size': 16384}]`
- interrupts: `[461, 480, 464, 463, 462, 469, 459, 473, 468]`
- iommu-parent: `[175, 176]`
- MMIO[0]: 0x30000000, size 0x690000
- MMIO[1]: 0x30800000, size 0x690000
- MMIO[2]: 0x31320000, size 0x4000
- MMIO[3]: 0x31340000, size 0x4000
- MMIO[4]: 0x31344000, size 0x4000
- MMIO[5]: 0x32800000, size 0x800000
- MMIO[6]: 0x3B3D0000, size 0x4000

## dcp
- device_type: `dcp`
- reg: `[{'addr': 851443712, 'size': 442368}, {'addr': 847577088, 'size': 16384}]`
- interrupts: `[456, 455, 458, 457]`
- iommu-parent: `[173]`
- iop-version: `1`
- role: `DCP`
- MMIO[0]: 0x32C00000, size 0x6C000
- MMIO[1]: 0x32850000, size 0x4000

## dart-disp0
- device_type: `dart`
- reg: `[{'addr': 825245696, 'size': 16384}, {'addr': 825229312, 'size': 16384}]`
- interrupts: `[470]`
- sid: `AAAAAAQAAAAPAAAA`
- sid-count: `16`
- vm-base: `1099511627776`
- vm-size: `68719476736`
- MMIO[0]: 0x31304000, size 0x4000
- MMIO[1]: 0x31300000, size 0x4000

## dart-dcp
- device_type: `dart`
- reg: `{'addr': 825278464, 'size': 16384}`
- interrupts: `[470]`
- sid: `64424509445`
- sid-count: `16`
- vm-base: `1099511627776`
- vm-size: `68719476736`
- MMIO[0]: 0x3130C000, size 0x4000

## dart-dispgrt
- device_type: `dart`
- reg: `[{'addr': 825556992, 'size': 16384}, {'addr': 825540608, 'size': 16384}]`
- interrupts: `[470]`
- sid: `64424509440`
- sid-count: `16`
- vm-base: `1099511627776`
- vm-size: `3298534883328`
- MMIO[0]: 0x31350000, size 0x4000
- MMIO[1]: 0x3134C000, size 0x4000

## vram
- device_type: `vram`
- reg: `{'addr': 0, 'size': 0}`
- MMIO[0]: 0x0, size 0x0

## scaler0
- device_type: `scaler`
- reg: `[{'addr': 1660944384, 'size': 163840}, {'addr': 1663107072, 'size': 16384}, {'addr': 1663057920, 'size': 16384}]`
- interrupts: `[638, 640]`
- iommu-parent: `[182, 183]`
- MMIO[0]: 0x63000000, size 0x28000
- MMIO[1]: 0x63210000, size 0x4000
- MMIO[2]: 0x63204000, size 0x4000

## gfx-asc
- device_type: `gfx-asc`
- reg: `[{'addr': 104857600, 'size': 442368}, {'addr': 100990976, 'size': 8}]`
- interrupts: `[615, 614, 617, 616]`
- iommu-parent: `[211]`
- iop-version: `1`
- role: `GFX`
- MMIO[0]: 0x6400000, size 0x6C000
- MMIO[1]: 0x6050000, size 0x8

