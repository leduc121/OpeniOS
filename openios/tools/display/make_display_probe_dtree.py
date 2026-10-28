#!/usr/bin/env python3
"""Create an opt-in Darwin DT probe with selected display matches restored.

The normal QEMU-SPTM fixup deliberately removes unsupported compatible
properties.  This tool applies that fixup, then restores only the display,
DCP, and display-DART compatible properties from the unmodified input tree.
It never enables SGX and refuses to overwrite an existing output.
"""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import sys


RESTORE_PATHS = {
    "dcp": (
        ("arm-io", "dcp"),
        ("arm-io", "dcp", "iop-dcp-nub"),
        ("arm-io", "dcp0-expert"),
    ),
    "disp0": (("arm-io", "disp0"),),
    "darts": (
        ("arm-io", "dart-dcp"),
        ("arm-io", "dart-dcp", "mapper-dcp"),
        ("arm-io", "dart-disp0"),
        ("arm-io", "dart-disp0", "mapper-disp0"),
        ("arm-io", "dart-disp0", "mapper-disp0-piodma"),
        ("arm-io", "dart-dispgrt"),
        ("arm-io", "dart-dispgrt", "mapper-dispgrt"),
    ),
}


def node_at(root, path):
    node = root
    for component in path:
        node = node[component]
    return node


def load_fixup(repo_root: Path):
    source = repo_root / "third_party/darwin-vm/dt_fixup.py"
    spec = importlib.util.spec_from_file_location("openios_dt_fixup", source)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {source}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="unmodified Apple Device Tree")
    parser.add_argument("output", type=Path, help="new probe Device Tree")
    parser.add_argument("--nvram", required=True, type=Path)
    parser.add_argument("--disable-network", action="store_true")
    parser.add_argument(
        "--enable",
        action="append",
        choices=tuple(RESTORE_PATHS),
        required=True,
        help="compatible group to restore; repeat to combine groups",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite existing output: {args.output}")
    if args.input.resolve() == args.output.resolve():
        raise SystemExit("input and output must differ")

    repo_root = Path(__file__).resolve().parents[3]
    dt = load_fixup(repo_root)
    original = dt.ADTNode()
    probe = dt.ADTNode()
    source = args.input.read_bytes()
    dt.decode_node(source, original)
    dt.decode_node(source, probe)

    with args.nvram.open("rb") as nvram:
        dt.fixup(probe, nvram, args.disable_network)

    restored = []
    for group in dict.fromkeys(args.enable):
        for path in RESTORE_PATHS[group]:
            compatible = node_at(original, path).props.get("compatible")
            if compatible is None:
                raise RuntimeError(f"input lacks compatible at /{'/'.join(path)}")
            node_at(probe, path).props["compatible"] = compatible
            restored.append(f"/{'/'.join(path)}={compatible!r}")

    # dt.fixup() removes SGX.  Keep it that way: this probe is not a GPU probe.
    if "sgx" in probe["arm-io"]:
        raise RuntimeError("SGX unexpectedly survived the normal fixup")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(dt.encode_node(probe))
    print(f"wrote {args.output}")
    print("restored display-only compatible properties:")
    print("\n".join(f"  {item}" for item in restored))
    print("SGX compatible property: not restored")
    return 0


if __name__ == "__main__":
    sys.exit(main())
