#!/usr/bin/env bash
# Build, sign, and create a trustcache for the read-only M9 IORegistry probe.
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
out_dir=${1:?usage: $0 OUTPUT_DIRECTORY}
runtime_image=${2:-"$repo_root/openios/firmware/linux/experiments/m8.2-libsystem-20261029/ramdisk-shell-m8.2.apfs"}
ldid="$repo_root/third_party/ldid/ldid"
hashes="$repo_root/openios/firmware/linux/work/all_hashes-v5"
build_tc="$repo_root/third_party/darwin-vm/build_tc.py"
source_file="$repo_root/openios/tools/display/m9_ioreg.c"
libsystem_stub="$repo_root/openios/tools/display/m8_libSystem.tbd"
identifier=com.openios.m9.ioreg
runtime_dir=$(mktemp -d /tmp/openios-m9-iokit.XXXXXX)

cleanup() { rm -rf "$runtime_dir"; }
trap cleanup EXIT
for tool in clang ld64.lld llvm-objdump python3 sort sed 7z; do
    command -v "$tool" >/dev/null
done
test -x "$ldid" && test -r "$hashes" && test -r "$build_tc"
test -r "$source_file" && test -r "$libsystem_stub" && test -r "$runtime_image"
mkdir -p "$out_dir"

7z x -y -o"$runtime_dir" "$runtime_image" \
    System/Library/Frameworks/IOKit.framework/Versions/A/IOKit >/dev/null
iokit="$runtime_dir/System/Library/Frameworks/IOKit.framework/Versions/A/IOKit"
test -s "$iokit"

object="$out_dir/openios-ioreg.o"
binary="$out_dir/openios-ioreg"
hashlist="$out_dir/all_hashes-m9-ioreg"
trustcache="$out_dir/ramdisk-m9-ioreg.tc"
clang -target arm64e-apple-ios26.0 -ffreestanding -fno-stack-protector \
    -c "$source_file" -o "$object"
# IOKit exports below were verified from this 23G71 runtime.  dynamic_lookup
# permits libSystem's standard dyld binder without inventing a linker stub.
ld64.lld -arch arm64e -platform_version ios 26.6 26.6 -e _main \
    -undefined dynamic_lookup -needed_library "$iokit" \
    -needed_library "$libsystem_stub" -o "$binary" "$object"
"$ldid" "-I$identifier" -Cadhoc -S "$binary"
cdhash=$("$ldid" -h "$binary" | sed -n 's/^CDHash=//p')
[[ "$cdhash" =~ ^[0-9a-f]{40}$ ]] || { echo "invalid CDHash" >&2; exit 1; }
{ cat "$hashes"; printf '%s\n' "$cdhash"; } | sort -u >"$hashlist"
python3 "$build_tc" "$hashlist" "$trustcache"
python3 - "$trustcache" "$cdhash" <<'PY'
import pathlib, struct, sys
blob = pathlib.Path(sys.argv[1]).read_bytes()
version, _uuid, count = struct.unpack_from('<I16sI', blob)
assert version == 1 and len(blob) == 24 + count * 22
assert any(blob[24 + i * 22:44 + i * 22] == bytes.fromhex(sys.argv[2])
           for i in range(count))
print(f'trustcache: version={version} entries={count} ioreg_cdhash_present=yes')
PY
echo "binary=$binary"
echo "identifier=$identifier"
echo "cdhash=$cdhash"
echo "trustcache=$trustcache"
llvm-objdump --macho --dylibs-used "$binary"
