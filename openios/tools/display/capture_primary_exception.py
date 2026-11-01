#!/usr/bin/env python3
"""OpeniOS supervisor to capture primary synchronous exception during RTBuddy startup.

Enforces bounded execution, connection validation, pre-resume breakpoint
verification, immediate logging to disk, and strict child PID cleanup.
"""

from __future__ import annotations

import fcntl
import os
from pathlib import Path
import select
import signal
import subprocess
import sys
import time

LOCK_FILE = "/tmp/openios_guest_exec.lock"
GDB_SOCK = "/tmp/openios_gdb_session.sock"
SERIAL_LOG = "/tmp/openios_serial.log"
CAPTURE_LOG = "/tmp/openios_capture_primary.log"
TIMEOUT_SECONDS = 60

def terminate_process_tree(proc: subprocess.Popen, name: str, timeout: float = 3.0):
    if proc is None or proc.poll() is not None:
        return
    print(f"[*] Stopping {name} (PID {proc.pid}) gracefully with SIGTERM...", flush=True)
    try:
        proc.terminate()
        proc.wait(timeout=timeout)
        print(f"[+] {name} (PID {proc.pid}) terminated cleanly.", flush=True)
    except subprocess.TimeoutExpired:
        print(f"[-] {name} did not exit within {timeout}s; sending SIGKILL...", flush=True)
        try:
            proc.kill()
            proc.wait(timeout=2.0)
            print(f"[+] {name} killed.", flush=True)
        except Exception as e:
            print(f"[-] Error killing {name}: {e}", file=sys.stderr, flush=True)
    except Exception as e:
        print(f"[-] Error terminating {name}: {e}", file=sys.stderr, flush=True)

def main():
    repo_root = Path(__file__).resolve().parents[3]
    worker_script = Path(__file__).parent / "gdb_capture_worker.py"
    if not worker_script.exists():
        print(f"[-] Worker script not found at {worker_script}", file=sys.stderr, flush=True)
        sys.exit(1)

    # Concurrency protection
    lock_fd = open(LOCK_FILE, "w")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("[-] Another OpeniOS guest execution is running. Aborting.", file=sys.stderr, flush=True)
        sys.exit(1)

    # Initialize log files
    if os.path.exists(GDB_SOCK):
        os.remove(GDB_SOCK)
    with open(CAPTURE_LOG, "w") as f:
        f.write(f"=== OpeniOS Primary Exception Capture Session Started at {time.ctime()} ===\n")

    qemu_proc: subprocess.Popen | None = None
    gdb_proc: subprocess.Popen | None = None

    qemu_cmd = [
        str(repo_root / "third_party/darwin-vm/qemu-sptm/build/qemu-system-aarch64"),
        "-M", "darwin",
        "-bootkc", str(repo_root / "openios/firmware/linux/iphone15-3-26.6/boot/bootkc"),
        "-dtree", "/tmp/openios-m108-dcp.dtree",
        "-sptm", str(repo_root / "openios/firmware/linux/iphone15-3-26.6/boot/sptm"),
        "-txm", str(repo_root / "openios/firmware/linux/iphone15-3-26.6/boot/txm"),
        "-ramdisk", str(repo_root / "openios/firmware/linux/work/ramdisk-shell-v5.apfs"),
        "-tc", str(repo_root / "openios/firmware/linux/work/ramdisk-v5.tc"),
        "-args", "rd=md0 serial=3 -v -noprogress wdt=-1 wlan-olyhal-abort",
        "-m", "8G",
        "-nographic",
        "-serial", f"file:{SERIAL_LOG}",
        "-S",
        "-gdb", f"unix:{GDB_SOCK},server=on,wait=off"
    ]

    try:
        print(f"[*] Starting paused QEMU (-S) with local gdbstub on {GDB_SOCK}...", flush=True)
        qemu_proc = subprocess.Popen(qemu_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"[+] QEMU spawned (PID {qemu_proc.pid})", flush=True)

        # Wait up to 5s for GDB socket to appear
        sock_ready = False
        for _ in range(50):
            if os.path.exists(GDB_SOCK):
                sock_ready = True
                break
            if qemu_proc.poll() is not None:
                print(f"[-] QEMU exited prematurely with code {qemu_proc.returncode}!", file=sys.stderr, flush=True)
                sys.exit(1)
            time.sleep(0.1)

        if not sock_ready:
            print("[-] GDB socket did not appear within 5s!", file=sys.stderr, flush=True)
            sys.exit(1)

        print("[*] Launching gdb-multiarch attached to worker script...", flush=True)
        gdb_cmd = [
            "gdb-multiarch", "-nx", "-batch",
            "-x", str(worker_script)
        ]
        gdb_proc = subprocess.Popen(
            gdb_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        print(f"[+] GDB spawned (PID {gdb_proc.pid})", flush=True)

        start_time = time.time()
        with open(CAPTURE_LOG, "a", buffering=1) as cap_f:
            while time.time() - start_time < TIMEOUT_SECONDS:
                # Check child health
                if qemu_proc.poll() is not None:
                    print(f"[-] QEMU terminated unexpectedly with code {qemu_proc.returncode}", flush=True)
                    break
                if gdb_proc.poll() is not None:
                    print(f"[*] GDB exited with code {gdb_proc.returncode}", flush=True)
                    # Drain remaining output
                    rem = gdb_proc.stdout.read()
                    if rem:
                        sys.stdout.write(rem)
                        sys.stdout.flush()
                        cap_f.write(rem)
                        cap_f.flush()
                    break

                r, _, _ = select.select([gdb_proc.stdout], [], [], 0.3)
                if r:
                    line = gdb_proc.stdout.readline()
                    if line:
                        sys.stdout.write(line)
                        sys.stdout.flush()
                        cap_f.write(line)
                        cap_f.flush()
                        os.fsync(cap_f.fileno())

        elapsed = time.time() - start_time
        if gdb_proc.poll() is None:
            print(f"[-] Bounded timeout reached ({TIMEOUT_SECONDS}s). Enforcing termination...", file=sys.stderr, flush=True)
        else:
            print(f"[+] Capture session finished in {elapsed:.2f}s", flush=True)

    finally:
        print("[*] Cleaning up session processes...", flush=True)
        if gdb_proc is not None:
            terminate_process_tree(gdb_proc, "gdb-multiarch", timeout=2.0)
        if qemu_proc is not None:
            terminate_process_tree(qemu_proc, "qemu-system-aarch64", timeout=3.0)

        if os.path.exists(GDB_SOCK):
            try:
                os.remove(GDB_SOCK)
            except Exception:
                pass

        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            lock_fd.close()
        except Exception:
            pass
        print(f"[*] Session cleanup complete. Logs preserved in {CAPTURE_LOG} and {SERIAL_LOG}", flush=True)

if __name__ == "__main__":
    main()
