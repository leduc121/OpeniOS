#!/usr/bin/env bash
# Root-only, one-purpose APFS insertion for the M8.1 disposable image.
# It never names or mounts the known-good M1 ramdisk.
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
experiment="$repo_root/openios/firmware/linux/experiments/m8.1-smoke-20261029"
image="$experiment/ramdisk-shell-m8.1.apfs"
source_binary="$experiment/openios-m8-smoke"
destination_rel="usr/local/bin/openios-m8-smoke"
expected_image_sha="cf39a91c5f7cce04ad27bd2fde6161e038d5f30af81672305b55938c3c0e115f"
mount_dir=$(mktemp -d /tmp/openios-m8.1-apfs.XXXXXX)
loop_dev=""
mounted=false

test "$(id -u)" = 0 || { echo "must be run through sudo" >&2; exit 1; }
test -f "$image" && test -f "$source_binary"
test "$(sha256sum "$image" | awk '{print $1}')" = "$expected_image_sha" || {
    echo "refusing: disposable image no longer matches its pre-mount M1 copy" >&2
    exit 1
}

cleanup() {
    status=$?
    if "$mounted"; then
        umount "$mount_dir" || status=1
    fi
    if test -n "$loop_dev"; then
        losetup --detach "$loop_dev" || status=1
    fi
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
printf '%s\n' "PASS: inserted byte-identical M8 smoke executable" >>"$experiment/mount-result.txt"
