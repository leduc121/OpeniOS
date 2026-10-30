#!/usr/bin/env bash
# Build, ad-hoc-sign, and trust-cache a minimal iOS Mach-O without APFS writes.
set -euo pipefail
repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
out_dir=${1:?usage: $0 OUTPUT_DIRECTORY}
ldid="$repo_root/third_party/ldid/ldid"
hashes="$repo_root/openios/firmware/linux/work/all_hashes-v5"
build_tc="$repo_root/third_party/darwin-vm/build_tc.py"
source_file="$repo_root/openios/tools/display/m8_macho_smoke.S"
stub_dir="$repo_root/openios/tools/display"
identifier=com.openios.m8.smoke
for tool in clang ld64.lld llvm-objdump python3 sort sed; do command -v "$tool" >/dev/null; done
test -x "$ldid" && test -r "$hashes" && test -r "$build_tc" && test -r "$source_file"
test -r "$stub_dir/m8_libSystem.tbd"
mkdir -p "$out_dir"
object="$out_dir/openios-m8-smoke.o"
binary="$out_dir/openios-m8-smoke"
hashlist="$out_dir/all_hashes-m8-smoke"
trustcache="$out_dir/ramdisk-m8-smoke.tc"
clang -target arm64e-apple-ios26.0 -c "$source_file" -o "$object"
# The .tbd declares only the install name/version observed in the matching
# ramdisk's libSystem.B.dylib; the smoke has no external symbol references.
# -needed_library emits LC_LOAD_DYLIB, which modern iOS dyld requires even for
# this direct-syscall diagnostic program.
ld64.lld -arch arm64e -platform_version ios 26.6 26.6 -e _main \
    -needed_library "$stub_dir/m8_libSystem.tbd" -o "$binary" "$object"
"$ldid" "-I$identifier" -Cadhoc -S "$binary"
cdhash=$("$ldid" -h "$binary" | sed -n 's/^CDHash=//p')
if [[ ! "$cdhash" =~ ^[0-9a-f]{40}$ ]]; then
    echo "invalid CDHash" >&2
    exit 1
fi
{ cat "$hashes"; printf '%s\n' "$cdhash"; } | sort -u >"$hashlist"
python3 "$build_tc" "$hashlist" "$trustcache"
python3 - "$trustcache" "$cdhash" <<'PY'
import pathlib, struct, sys
blob = pathlib.Path(sys.argv[1]).read_bytes(); cdhash = bytes.fromhex(sys.argv[2])
version, _uuid, count = struct.unpack_from('<I16sI', blob)
entries = [blob[24 + i * 22:24 + (i + 1) * 22] for i in range(count)]
assert version == 1 and len(blob) == 24 + count * 22
assert all(entry[20:] == b'\x02\x00' for entry in entries)
assert any(entry[:20] == cdhash for entry in entries)
print(f'trustcache: version={version} entries={count} smoke_cdhash_present=yes')
PY
echo "binary=$binary"; echo "identifier=$identifier"; echo "cdhash=$cdhash"; echo "trustcache=$trustcache"
llvm-objdump --macho --private-headers "$binary"
