#!/usr/bin/env bash
# Root-only insertion for the disposable M9.1 property-probe image.
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
experiment="$repo_root/openios/firmware/linux/experiments/m9.1-compatible-20261029"
image="$experiment/ramdisk-shell-m9.1.apfs"
source_binary="$experiment/openios-ioreg"
destination_rel="usr/local/bin/openios-ioreg"
expected_image_sha="533101d559d5274631f79c2963765fba716aecc7b5b0518786d0c01622e15a74"
mount_dir=$(mktemp -d /tmp/openios-m9.1-apfs.XXXXXX)
loop_dev=""
mounted=false

test "$(id -u)" = 0 || { echo "must be run through sudo" >&2; exit 1; }
test -f "$image" && test -f "$source_binary"
test "$(sha256sum "$image" | awk '{print $1}')" = "$expected_image_sha" || {
    echo "refusing: M9.1 image does not match its verified pre-insertion copy" >&2
    exit 1
}

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
sha256sum "$source_binary" "$mount_dir/$destination_rel" \
    >"$experiment/SHA256SUMS.mounted"
printf '%s\n' "loop_device=$loop_dev" >"$experiment/mount-result.txt"
printf '%s\n' "destination=/$destination_rel" >>"$experiment/mount-result.txt"
printf '%s\n' "PASS: inserted byte-identical M9.1 compatible-property probe" \
    >>"$experiment/mount-result.txt"
