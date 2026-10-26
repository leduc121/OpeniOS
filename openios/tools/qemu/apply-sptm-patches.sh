#!/usr/bin/env bash
# Apply the OpeniOS QEMU-SPTM patch series without resetting local work.
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
QEMU_DIR="${1:-$ROOT/third_party/darwin-vm/qemu-sptm}"
PATCH_DIR="$ROOT/openios/patches/qemu-sptm"
EXPECTED_REV="bad6336fb24211f8c4e8e946c259bd5b12417340"

git -C "$QEMU_DIR" rev-parse --git-dir >/dev/null 2>&1 || {
  echo "error: QEMU-SPTM Git repository not found: $QEMU_DIR" >&2
  exit 1
}

actual_rev="$(git -C "$QEMU_DIR" rev-parse HEAD)"
if [ "$actual_rev" != "$EXPECTED_REV" ]; then
  echo "error: QEMU-SPTM revision mismatch" >&2
  echo "expected: $EXPECTED_REV" >&2
  echo "actual:   $actual_rev" >&2
  exit 1
fi

patches=()
declare -A touched_paths=()

while IFS= read -r patch_name; do
  case "$patch_name" in
    ''|'#'*) continue ;;
  esac

  patch_path="$PATCH_DIR/$patch_name"
  [ -f "$patch_path" ] || {
    echo "error: patch not found: $patch_path" >&2
    exit 1
  }

  patches+=("$patch_path")
  while IFS=$'\t' read -r _ _ path; do
    touched_paths["$path"]=1
  done < <(git apply --numstat "$patch_path")
done < "$PATCH_DIR/series"

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT
git -C "$QEMU_DIR" archive HEAD | tar -x -C "$tmpdir"
for patch_path in "${patches[@]}"; do
  git -C "$tmpdir" apply "$patch_path"
done

series_applied=true
for path in "${!touched_paths[@]}"; do
  if ! cmp -s "$tmpdir/$path" "$QEMU_DIR/$path"; then
    series_applied=false
    break
  fi
done

if "$series_applied"; then
  echo "QEMU-SPTM patch series already applied."
  exit 0
fi

rm -rf "$tmpdir"
mkdir -p "$tmpdir"
git -C "$QEMU_DIR" archive HEAD | tar -x -C "$tmpdir"
for path in "${!touched_paths[@]}"; do
  if [ -e "$QEMU_DIR/$path" ]; then
    mkdir -p "$tmpdir/$(dirname "$path")"
    cp -a "$QEMU_DIR/$path" "$tmpdir/$path"
  else
    rm -f "$tmpdir/$path"
  fi
done

for patch_path in "${patches[@]}"; do
  if ! git -C "$tmpdir" apply "$patch_path"; then
    echo "error: patch series does not apply cleanly" >&2
    echo "Preserving the QEMU-SPTM working tree unchanged." >&2
    exit 1
  fi
done

for patch_path in "${patches[@]}"; do
  git -C "$QEMU_DIR" apply "$patch_path"
done
echo "Applied ${#patches[@]} QEMU-SPTM patches."
