#!/usr/bin/env python3
"""Run commands or upload/execute Mach-O binaries in the OpeniOS guest with robust lifecycle management."""

import argparse
import base64
import fcntl
import os
import pty
import select
import subprocess
import sys
import time

LOCK_FILE = "/tmp/openios_guest_exec.lock"

def drain_output(master, timeout=0.1):
    out = b''
    while True:
        r, _, _ = select.select([master], [], [], timeout)
        if not r:
            break
        try:
            chunk = os.read(master, 4096)
            if not chunk:
                break
            out += chunk
        except OSError:
            break
    return out

def run_guest_session(qemu_cmd, upload_binary=None, guest_dest="/tmp/test_bin",
                      command_to_run="/usr/local/bin/openios-ioreg",
                      boot_timeout=45, cmd_timeout=30):
    # Lock to prevent simultaneous executors competing for guest console
    lock_fd = open(LOCK_FILE, "w")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("[-] Another OpeniOS guest execution is currently running. Exiting.", file=sys.stderr)
        return False, b"ERROR: concurrent executor active\n", -1

    master, slave = pty.openpty()
    proc = None
    full_log = b''
    cmd_output = b''
    status_str = "UNKNOWN"
    cmd_exit_code = -1
    start_time = time.time()

    try:
        proc = subprocess.Popen(qemu_cmd, stdin=slave, stdout=slave, stderr=slave, close_fds=True)
        os.close(slave)
        slave = None

        print(f"[*] Booting QEMU (pid {proc.pid})...", file=sys.stderr)

        # 1. Wait for boot prompt
        prompt_reached = False
        boot_start = time.time()
        while time.time() - boot_start < boot_timeout:
            # Check if QEMU died
            ret = proc.poll()
            if ret is not None:
                status_str = f"QEMU_EXIT_EARLY (exit code {ret})"
                print(f"[-] {status_str}", file=sys.stderr)
                break

            r, _, _ = select.select([master], [], [], 0.5)
            if r:
                try:
                    chunk = os.read(master, 4096)
                    if not chunk:
                        break
                    full_log += chunk
                    if b'bash-5.3#' in full_log:
                        prompt_reached = True
                        break
                except OSError:
                    break

        if not prompt_reached and proc.poll() is None:
            status_str = "BOOT_TIMEOUT"
            print(f"[-] Timed out after {boot_timeout}s waiting for guest bash prompt", file=sys.stderr)

        if prompt_reached:
            print(f"[+] bash-5.3# prompt reached in {time.time() - boot_start:.2f}s!", file=sys.stderr)

            # Disable echo
            os.write(master, b"stty -echo\n")
            drain_output(master, 0.2)

            # Upload if requested
            if upload_binary and os.path.exists(upload_binary) and os.path.isfile(upload_binary):
                with open(upload_binary, "rb") as f:
                    b64_data = base64.b64encode(f.read())
                print(f"[*] Uploading binary {upload_binary} ({len(b64_data)} b64 bytes)...", file=sys.stderr)

                start_marker = f"cat << 'EOF_UPLOAD' | base64 -d > {guest_dest}\n".encode()
                os.write(master, start_marker)

                chunk_sz = 512
                offset = 0
                while offset < len(b64_data):
                    chunk = b64_data[offset:offset + chunk_sz] + b"\n"
                    written = 0
                    while written < len(chunk):
                        _, w, _ = select.select([], [master], [], 2.0)
                        if w:
                            n = os.write(master, chunk[written:])
                            written += n
                        r, _, _ = select.select([master], [], [], 0.01)
                        if r:
                            full_log += os.read(master, 4096)
                    offset += chunk_sz
                    time.sleep(0.01)

                os.write(master, b"\nEOF_UPLOAD\n")
                drain_output(master, 0.3)
                os.write(master, f"chmod 0755 {guest_dest}\n".encode())
                drain_output(master, 0.2)
                print(f"[+] Upload complete to {guest_dest}", file=sys.stderr)

            drain_output(master, 0.1)

            # Execute command with unique sentinel that cannot match terminal echo
            tag = f"RES_{int(time.time() * 1000)}"
            print(f"[*] Executing command: {command_to_run}", file=sys.stderr)
            full_cmd = f"{command_to_run}\nprintf '__%s:%d__\\n' {tag} $?\n".encode()
            os.write(master, full_cmd)

            cmd_start = time.time()
            cmd_done = False
            # Output pattern produced by printf: "__RES_<timestamp>:<exit_code>__"
            # Terminal echo is disabled above. The runtime-only tag makes an
            # accidental match in command output vanishingly unlikely.
            target_prefix = f"__{tag}:".encode()

            while time.time() - cmd_start < cmd_timeout:
                ret = proc.poll()
                if ret is not None:
                    status_str = f"QEMU_EXIT_DURING_COMMAND (exit code {ret})"
                    print(f"[-] {status_str}", file=sys.stderr)
                    break

                r, _, _ = select.select([master], [], [], 0.5)
                if r:
                    try:
                        chunk = os.read(master, 4096)
                        if not chunk:
                            break
                        full_log += chunk
                        cmd_output += chunk
                        if target_prefix in cmd_output:
                            cmd_done = True
                            # Drain any remaining bytes from PTY
                            extra = drain_output(master, 0.2)
                            full_log += extra
                            cmd_output += extra
                            # Extract exit code
                            idx = cmd_output.find(target_prefix) + len(target_prefix)
                            end_idx = cmd_output.find(b"__", idx)
                            if end_idx != -1:
                                code_str = cmd_output[idx:end_idx].decode('ascii', errors='ignore')
                            else:
                                code_str = cmd_output[idx:].split(b"\n")[0].strip().decode('ascii', errors='ignore')
                            try:
                                cmd_exit_code = int(code_str)
                            except ValueError:
                                cmd_exit_code = 0
                            status_str = f"SUCCESS (cmd exit code {cmd_exit_code})"
                            print(f"[+] Command completed with exit code {cmd_exit_code}!", file=sys.stderr)
                            break
                    except OSError:
                        break

            if not cmd_done and proc.poll() is None:
                status_str = f"COMMAND_TIMEOUT after {cmd_timeout}s"
                print(f"[-] {status_str}", file=sys.stderr)

    finally:
        total_elapsed = time.time() - start_time
        proc_alive = (proc is not None and proc.poll() is None)
        if proc_alive:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=2)
            proc_alive = False

        try:
            os.close(master)
        except OSError:
            pass
        if slave is not None:
            try:
                os.close(slave)
            except OSError:
                pass

        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            lock_fd.close()
        except Exception:
            pass

        print(f"[*] Session ended: status={status_str}, elapsed={total_elapsed:.2f}s, qemu_alive={proc_alive}", file=sys.stderr)

    ok = ("SUCCESS" in status_str and cmd_exit_code == 0)
    return ok, full_log, cmd_exit_code

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--qemu", default="third_party/darwin-vm/qemu-sptm/build/qemu-system-aarch64")
    parser.add_argument("--dtree", default="/tmp/test-dcp.dtree")
    parser.add_argument("--tc", default="/tmp/combined.tc")
    parser.add_argument("--ramdisk", default="openios/firmware/linux/experiments/stage-a-20261030/ramdisk-shell-stage-a.apfs")
    parser.add_argument("--upload", default="")
    parser.add_argument("--guest-dest", default="/tmp/test_bin")
    parser.add_argument("--cmd", default="/usr/local/bin/openios-ioreg")
    parser.add_argument("--boot-timeout", type=int, default=45)
    parser.add_argument("--cmd-timeout", type=int, default=30)
    parser.add_argument("--timeout", type=int, default=45, help="legacy alias for boot-timeout")
    args = parser.parse_args()

    boot_to = args.boot_timeout if args.boot_timeout != 45 else args.timeout

    qemu_cmd = [
        args.qemu,
        "-M", "darwin",
        "-bootkc", "openios/firmware/linux/iphone15-3-26.6/boot/bootkc",
        "-dtree", args.dtree,
        "-sptm", "openios/firmware/linux/iphone15-3-26.6/boot/sptm",
        "-txm", "openios/firmware/linux/iphone15-3-26.6/boot/txm",
        "-ramdisk", args.ramdisk,
        "-tc", args.tc,
        "-args", "rd=md0 serial=3 -v -noprogress wdt=-1 wlan-olyhal-abort",
        "-m", "8G",
        "-nographic",
        "-serial", "mon:stdio"
    ]

    ok, log, code = run_guest_session(qemu_cmd, upload_binary=args.upload,
                                      guest_dest=args.guest_dest,
                                      command_to_run=args.cmd,
                                      boot_timeout=boot_to,
                                      cmd_timeout=args.cmd_timeout)
    sys.stdout.write(log.decode('utf-8', errors='replace'))
    sys.stdout.flush()
    if not ok:
        print(f"[-] Session failed with code {code}. Log length: {len(log)} bytes", file=sys.stderr)
        sys.exit(code if code > 0 else 1)

if __name__ == "__main__":
    main()

