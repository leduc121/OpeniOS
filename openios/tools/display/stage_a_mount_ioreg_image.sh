#!/usr/bin/env bash
# Narrowly-scoped root-only insertion for the Stage A IODTPlane probe image.
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
experiment="$repo_root/openios/firmware/linux/experiments/stage-a-20261030"
source_image="$repo_root/openios/firmware/linux/experiments/m10.1-asc-children-20261029/ramdisk-shell-m10.1.apfs"
image="$experiment/ramdisk-shell-stage-a.apfs"
source_binary="/tmp/openios-m10-ioreg-build/openios-ioreg"
destination_rel="usr/local/bin/openios-ioreg"

test "$(id -u)" = 0 || { echo "must be run through sudo" >&2; exit 1; }
test -f "$source_image" || { echo "source image missing: $source_image" >&2; exit 1; }
test -f "$source_binary" || { echo "source binary missing: $source_binary" >&2; exit 1; }

mkdir -p "$experiment"
if [ ! -f "$image" ]; then
    echo "Copying source image to $image..."
    cp "$source_image" "$image"
fi

mount_dir=$(mktemp -d /tmp/openios-stage-a-apfs.XXXXXX)
loop_dev=""
mounted=false

cleanup() {
    status=$?
    if "$mounted"; then umount "$mount_dir" || status=1; fi
    if test -n "$loop_dev"; then losetup --detach "$loop_dev" || status=1; fi
    rmdir "$mount_dir" 2>/dev/null || true
    exit "$status"
}
trap cleanup EXIT INT TERM

modprobe apfs
loop_dev=$(losetup --find --show --sector-size 4096 "$image")
mount -t apfs -o rw,readwrite,vol=0,nosuid,nodev "$loop_dev" "$mount_dir"
mounted=true

test -d "$mount_dir/usr/local/bin"
install -m 0755 "$source_binary" "$mount_dir/$destination_rel"
cmp -s "$source_binary" "$mount_dir/$destination_rel"
sync

sha256sum "$source_binary" "$mount_dir/$destination_rel" >"$experiment/SHA256SUMS.mounted"
printf '%s\n' "loop_device=$loop_dev" >"$experiment/mount-result.txt"
printf '%s\n' "destination=/$destination_rel" >>"$experiment/mount-result.txt"
printf '%s\n' "PASS: inserted Stage A IODTPlane probe binary" >>"$experiment/mount-result.txt"
echo "Stage A insertion successful into $image"
