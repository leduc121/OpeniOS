#!/usr/bin/env bash
# OpeniOS baseline QEMU build. Builds in build-<target>/, never installs.
# Usage: openios/scripts/build-baseline.sh inferno|sptm
# Env:   JOBS=2 (parallel jobs), FORCE=1 (skip the low-memory check)
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
JOBS="${JOBS:-2}"
TARGET="${1:-}"
LOGDIR="$ROOT/openios/build-logs"
DOCDIR="$ROOT/openios/docs"
mkdir -p "$LOGDIR" "$DOCDIR"

if [ -n "${CONDA_PREFIX:-}" ]; then
  echo "error: conda is active ($CONDA_PREFIX). Run 'conda deactivate' first." >&2
  exit 1
fi

case "$TARGET" in
  inferno)
    SRC="$ROOT"
    BUILD="$ROOT/build-inferno"
    ARGS=(--target-list=aarch64-softmmu --disable-guest-agent --enable-slirp
          --enable-lzfse --enable-nettle --enable-gnutls --disable-werror)
    ;;
  sptm)
    SRC="$ROOT/third_party/darwin-vm/qemu-sptm"
    BUILD="$ROOT/build-sptm"
    ARGS=(--target-list=aarch64-softmmu --disable-pvg --disable-werror)
    ;;
  *)
    echo "usage: $0 inferno|sptm" >&2
    exit 2
    ;;
esac

[ -x "$SRC/configure" ] || { echo "error: $SRC/configure not found" >&2; exit 1; }

avail_kb="$(awk '/MemAvailable/ {print $2}' /proc/meminfo)"
if [ "$avail_kb" -lt 3145728 ] && [ "${FORCE:-0}" != "1" ]; then
  echo "error: only $((avail_kb/1024)) MiB RAM available (<3 GiB)." >&2
  echo "Close apps first, or run with FORCE=1 at your own risk." >&2
  exit 1
fi

STAMP="$(date +%Y%m%d-%H%M%S)"
LOG="$LOGDIR/$TARGET-$STAMP.log"

{
  echo "== OpeniOS build: $TARGET @ $STAMP"
  echo "source : $SRC"
  echo "commit : $(git -C "$SRC" rev-parse HEAD)"
  echo "gcc    : $(gcc --version | head -1)"
  echo "python : $(python3 --version)"
  echo "meson  : $(meson --version 2>&1 | head -1)"
  echo "ninja  : $(ninja --version 2>&1 | head -1)"
  echo "jobs   : $JOBS"
  echo "args   : ${ARGS[*]}"
  echo
} | tee "$LOG"

mkdir -p "$BUILD"
cd "$BUILD"
"$SRC/configure" "${ARGS[@]}" 2>&1 | tee -a "$LOG"
nice -n 10 make -j"$JOBS" 2>&1 | tee -a "$LOG"

BIN="$BUILD/qemu-system-aarch64"
[ -x "$BIN" ] || { echo "error: build finished but $BIN is missing" >&2; exit 1; }

{
  echo
  echo "== built: $BIN"
  "$BIN" --version | head -1
} | tee -a "$LOG"

"$BIN" -machine help > "$DOCDIR/machines-$TARGET.txt"
echo "machine inventory saved to $DOCDIR/machines-$TARGET.txt"
echo "Apple/Darwin-related machines:"
grep -i -E "apple|t8|s8|darwin" "$DOCDIR/machines-$TARGET.txt" || echo "(none matched)"
