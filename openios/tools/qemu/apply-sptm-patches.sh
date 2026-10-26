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

while IFS= read -r patch_name; do
  case "$patch_name" in
    ''|'#'*) continue ;;
  esac

  patch_path="$PATCH_DIR/$patch_name"
  [ -f "$patch_path" ] || {
    echo "error: patch not found: $patch_path" >&2
    exit 1
  }

  if git -C "$QEMU_DIR" apply --check "$patch_path" 2>/dev/null; then
    echo "applying $patch_name"
    git -C "$QEMU_DIR" apply "$patch_path"
  elif git -C "$QEMU_DIR" apply --reverse --check "$patch_path" 2>/dev/null; then
    echo "already applied: $patch_name"
  else
    echo "error: $patch_name is neither applicable nor fully applied" >&2
    echo "Preserving the QEMU-SPTM working tree unchanged." >&2
    exit 1
  fi
done < "$PATCH_DIR/series"
