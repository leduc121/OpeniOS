#!/usr/bin/env bash
# Root-only insertion for the disposable M10.1 ASC-child probe image.
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
experiment="$repo_root/openios/firmware/linux/experiments/m10.1-asc-children-20261029"
image="$experiment/ramdisk-shell-m10.1.apfs"
source_binary="$experiment/openios-ioreg"
destination_rel="usr/local/bin/openios-ioreg"
expected_image_sha="1a6f9fda3a2ef44872ab55b6626caa87e0844f274f5580439e3113bb20298ef6"
expected_binary_sha="5905369ebac71cbddb28350f2223572eb0ed566b2fbc031f3a3453ded7670d66"
mount_dir=$(mktemp -d /tmp/openios-m10.1-apfs.XXXXXX)
loop_dev=""
mounted=false

test "$(id -u)" = 0 || { echo "must be run through sudo" >&2; exit 1; }
test -f "$image" && test -f "$source_binary"
test "$(sha256sum "$image" | awk '{print $1}')" = "$expected_image_sha" || {
    echo "refusing: M10.1 image does not match its verified pre-insertion copy" >&2
    exit 1
}
test "$(sha256sum "$source_binary" | awk '{print $1}')" = "$expected_binary_sha" || {
    echo "refusing: M10.1 probe binary does not match the signed build" >&2
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
printf '%s\n' "PASS: inserted byte-identical M10.1 ASC-child probe" \
    >>"$experiment/mount-result.txt"
