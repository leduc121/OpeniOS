#!/usr/bin/env bash
# Smoke-test the OpeniOS guest-physical-memory framebuffer research device.
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
QEMU="${1:-$ROOT/third_party/darwin-vm/qemu-sptm/build/qemu-system-aarch64}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

RAW="$WORK/pattern.xrgb"
PPM="$WORK/screendump.ppm"

perl -e '
    open my $f, ">:raw", $ARGV[0] or die $!;
    for my $y (0..179) {
        for my $x (0..319) {
            my ($r, $g, $b) =
                $x < 160
                    ? ($y < 90 ? (255, 32, 32) : (32, 64, 255))
                    : ($y < 90 ? (32, 255, 64) : (255, 224, 32));
            print $f pack("C4", $b, $g, $r, 0);
        }
    }
' "$RAW"

printf 'screendump %s\nquit\n' "$PPM" | "$QEMU" \
    -machine virt -m 256M -S -display none -serial none -monitor stdio \
    -device loader,file="$RAW",addr=0x48000000,force-raw=on \
    -device openios-guest-fb,addr=0x48000000,width=320,height=180,stride=1280 \
    >/dev/null

perl -e '
    open my $f, "<:raw", $ARGV[0] or die $!;
    local $/;
    my $ppm = <$f>;
    $ppm =~ /\AP6\s+320\s+180\s+255\s/s or die "bad PPM header\n";
    my $pixels = substr($ppm, $+[0]);
    my @tests = (
        [10, 10, [255, 32, 32]], [200, 10, [32, 255, 64]],
        [10, 120, [32, 64, 255]], [200, 120, [255, 224, 32]],
    );
    for my $test (@tests) {
        my ($x, $y, $want) = @$test;
        my @got = unpack("C3", substr($pixels, ($y * 320 + $x) * 3, 3));
        join(",", @got) eq join(",", @$want)
            or die "pixel $x,$y: got @got, expected @$want\n";
    }
' "$PPM"

echo "PASS: guest RAM produced the expected 320x180 four-color screendump"
