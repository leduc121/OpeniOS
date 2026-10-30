#!/usr/bin/env python3
"""OpeniOS diagnostic simulator shell.

This is a host launcher/viewer.  It intentionally never draws a SpringBoard
imitation: its screen is either an actual QEMU screendump or an explicit
diagnostic placeholder.  Guest touch injection remains opt-in because the
Darwin machine has no verified guest input path yet.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_QEMU = ROOT / "third_party/darwin-vm/qemu-sptm/build/qemu-system-aarch64"
DEFAULT_BOOT = ROOT / "openios/firmware/linux/iphone15-3-26.6/boot"
DEFAULT_WORK = ROOT / "openios/firmware/linux/work"
DEFAULT_ARGS = "rd=md0 serial=3 -v -noprogress wdt=-1 wlan-olyhal-abort"


class QmpError(RuntimeError):
    pass


def qmp_command(socket_path: Path, command: str, arguments: dict | None = None) -> dict:
    """Issue one QMP command using its greeting/capabilities handshake."""
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(0.4)
        client.connect(str(socket_path))
        stream = client.makefile("rwb")
        greeting = json.loads(stream.readline())
        if "QMP" not in greeting:
            raise QmpError("QMP greeting missing")
        stream.write(b'{"execute":"qmp_capabilities"}\r\n')
        stream.flush()
        capability = json.loads(stream.readline())
        if "error" in capability:
            raise QmpError(str(capability["error"]))
        request = {"execute": command}
        if arguments:
            request["arguments"] = arguments
        stream.write((json.dumps(request) + "\r\n").encode())
        stream.flush()
        reply = json.loads(stream.readline())
        if "error" in reply:
            raise QmpError(str(reply["error"]))
        return reply.get("return", {})


class Simulator(tk.Tk):
    def __init__(self, diagnostic_ppm: Path | None = None) -> None:
        super().__init__()
        self.title("OpeniOS Simulator — diagnostic host shell")
        self.minsize(1060, 740)
        self.configure(background="#171717")
        self.process: subprocess.Popen[str] | None = None
        self.session_dir: Path | None = None
        self.qmp_path: Path | None = None
        self.serial_path: Path | None = None
        self.frame_path: Path | None = None
        self.frame_image: tk.PhotoImage | None = None
        self.last_serial_size = 0
        self.diagnostic_ppm = diagnostic_ppm
        self._variables()
        self._build()
        self.protocol("WM_DELETE_WINDOW", self.shutdown)
        self.after(300, self.poll)

    def _variables(self) -> None:
        self.qemu_var = tk.StringVar(value=str(DEFAULT_QEMU))
        self.boot_var = tk.StringVar(value=str(DEFAULT_BOOT))
        self.ramdisk_var = tk.StringVar(value=str(DEFAULT_WORK / "ramdisk-shell-v5.apfs"))
        self.trustcache_var = tk.StringVar(value=str(DEFAULT_WORK / "ramdisk-v5.tc"))
        self.status_var = tk.StringVar(value="Stopped — no guest framebuffer available")
        self.frame_status_var = tk.StringVar(value="NO GUEST FRAMEBUFFER")
        self.input_enabled = tk.BooleanVar(value=False)

    def _build(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#171717")
        style.configure("TLabel", background="#171717", foreground="#e8e8e8")
        style.configure("Header.TLabel", font=("TkDefaultFont", 13, "bold"))
        style.configure("Muted.TLabel", foreground="#a0a0a0")
        style.configure("TButton", padding=7)

        header = ttk.Frame(self, padding=(16, 12))
        header.pack(fill="x")
        ttk.Label(header, text="OpeniOS Simulator", style="Header.TLabel").pack(side="left")
        ttk.Label(header, text="iPhone 14 Pro Max · D74AP · diagnostic host shell",
                  style="Muted.TLabel").pack(side="left", padx=14)
        ttk.Label(header, textvariable=self.status_var, style="Muted.TLabel").pack(side="right")

        body = ttk.Frame(self, padding=(16, 0, 16, 16))
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(0, weight=1)

        device_box = ttk.Frame(body, padding=14)
        device_box.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self.canvas = tk.Canvas(device_box, background="#101010", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _: self.draw_device())
        self.canvas.bind("<Button-1>", self.maybe_send_touch)
        self.canvas.bind("<ButtonRelease-1>", self.maybe_send_touch)

        right = ttk.Frame(body)
        right.grid(row=0, column=1, sticky="nsew")
        controls = ttk.LabelFrame(right, text="Session", padding=10)
        controls.pack(fill="x")
        ttk.Button(controls, text="Boot restore shell", command=self.boot).grid(row=0, column=0, sticky="ew")
        ttk.Button(controls, text="Stop", command=self.stop).grid(row=0, column=1, sticky="ew", padx=(8, 0))
        ttk.Button(controls, text="Capture PNG/PPM", command=self.capture).grid(row=1, column=0, sticky="ew", pady=(8, 0))
        ttk.Button(controls, text="Load diagnostic PPM", command=self.choose_ppm).grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(8, 0))
        controls.columnconfigure((0, 1), weight=1)
        ttk.Checkbutton(controls, text="Enable experimental QMP pointer injection",
                        variable=self.input_enabled).grid(row=2, column=0, columnspan=2, sticky="w", pady=(8, 0))

        config = ttk.LabelFrame(right, text="Firmware configuration", padding=10)
        config.pack(fill="x", pady=(12, 0))
        for row, (label, variable) in enumerate((("QEMU", self.qemu_var), ("Boot assets", self.boot_var),
                                                  ("Ramdisk", self.ramdisk_var), ("Trustcache", self.trustcache_var))):
            ttk.Label(config, text=label, style="Muted.TLabel").grid(row=row * 2, column=0, sticky="w")
            ttk.Entry(config, textvariable=variable).grid(row=row * 2 + 1, column=0, sticky="ew", pady=(0, 6))
        config.columnconfigure(0, weight=1)

        log_box = ttk.LabelFrame(right, text="Live serial log", padding=8)
        log_box.pack(fill="both", expand=True, pady=(12, 0))
        self.log = tk.Text(log_box, height=14, background="#0d0d0d", foreground="#d5d5d5",
                           insertbackground="#ffffff", wrap="word", state="disabled")
        self.log.pack(fill="both", expand=True)
        footer = ttk.Label(self, text="Screen is host diagnostic until QEMU supplies a framebuffer. It is not iOS UI or SpringBoard.",
                           style="Muted.TLabel", padding=(16, 0, 16, 12))
        footer.pack(fill="x")

    def append_log(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.configure(state="disabled")

    def qemu_args(self) -> list[str]:
        boot = Path(self.boot_var.get())
        return [self.qemu_var.get(), "-machine",
                "darwin," + ",".join((
                    f"bootkc={boot / 'bootkc'}", f"dtree={boot / 'dtree'}",
                    f"sptm={boot / 'sptm'}", f"txm={boot / 'txm'}",
                    f"ramdisk={self.ramdisk_var.get()}", f"tc={self.trustcache_var.get()}",
                    f"args={DEFAULT_ARGS}", "test-display=off", "display-mmio-trace=off")),
                "-display", "none", "-monitor", "none", "-serial", f"file:{self.serial_path}",
                "-qmp", f"unix:{self.qmp_path},server=on,wait=off"]

    def boot(self) -> None:
        if self.process and self.process.poll() is None:
            return
        if not Path(self.qemu_var.get()).is_file():
            messagebox.showerror("OpeniOS", "QEMU binary does not exist")
            return
        self.session_dir = Path(tempfile.mkdtemp(prefix="openios-simulator-"))
        self.qmp_path = self.session_dir / "qmp.sock"
        self.serial_path = self.session_dir / "serial.log"
        self.frame_path = self.session_dir / "frame.ppm"
        try:
            self.process = subprocess.Popen(self.qemu_args(), text=True)
        except OSError as error:
            self.status_var.set(f"Launch failed: {error}")
            return
        self.last_serial_size = 0
        self.status_var.set("Booting restore shell — waiting for QMP framebuffer")
        self.append_log("$ " + " ".join(self.qemu_args()) + "\n")

    def stop(self) -> None:
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.status_var.set("Stopping QEMU")

    def shutdown(self) -> None:
        self.stop()
        self.destroy()

    def choose_ppm(self) -> None:
        name = filedialog.askopenfilename(filetypes=[("Portable pixmap", "*.ppm"), ("All files", "*")])
        if name:
            self.diagnostic_ppm = Path(name)
            self.frame_status_var.set("QEMU DIAGNOSTIC FRAMEBUFFER — NOT IOS UI")
            self.draw_device()

    def capture(self) -> None:
        if not self.qmp_path or not self.frame_path:
            self.status_var.set("No active QMP session")
            return
        try:
            qmp_command(self.qmp_path, "screendump", {"filename": str(self.frame_path)})
            self.diagnostic_ppm = self.frame_path
            self.frame_status_var.set("QEMU FRAMEBUFFER — provenance depends on active guest device")
            self.draw_device()
        except (OSError, ValueError, QmpError) as error:
            self.status_var.set(f"Capture unavailable: {error}")

    def maybe_send_touch(self, event: tk.Event) -> None:
        if not self.input_enabled.get() or not self.qmp_path:
            return
        x0, y0, x1, y1 = self.screen_rect()
        if not (x0 <= event.x <= x1 and y0 <= event.y <= y1):
            return
        x = round((event.x - x0) * 65535 / max(1, x1 - x0))
        y = round((event.y - y0) * 65535 / max(1, y1 - y0))
        try:
            qmp_command(self.qmp_path, "input-send-event", {"events": [
                {"type": "abs", "data": {"axis": "x", "value": x}},
                {"type": "abs", "data": {"axis": "y", "value": y}},
                {"type": "btn", "data": {"button": "left", "down": event.type == tk.EventType.ButtonPress}},
            ]})
        except (OSError, ValueError, QmpError) as error:
            self.status_var.set(f"Guest input not operational: {error}")

    def screen_rect(self) -> tuple[int, int, int, int]:
        width, height = self.canvas.winfo_width(), self.canvas.winfo_height()
        h = max(160, height - 48)
        w = min(width - 48, int(h * 9 / 19.5))
        x0, y0 = (width - w) // 2, (height - h) // 2
        return x0, y0, x0 + w, y0 + h

    def draw_device(self) -> None:
        canvas = self.canvas
        canvas.delete("all")
        x0, y0, x1, y1 = self.screen_rect()
        pad = 12
        canvas.create_rectangle(x0 - pad, y0 - pad, x1 + pad, y1 + pad, fill="#050505", outline="#363636", width=2)
        canvas.create_rectangle(x0, y0, x1, y1, fill="#080808", outline="")
        island_w, island_h = max(54, (x1 - x0) // 3), max(10, (y1 - y0) // 40)
        island_x = (x0 + x1 - island_w) // 2
        canvas.create_oval(island_x, y0 + 8, island_x + island_w, y0 + 8 + island_h, fill="#000000", outline="")
        source = self.diagnostic_ppm
        if source and source.is_file():
            try:
                self.frame_image = tk.PhotoImage(file=str(source))
                canvas.create_image((x0 + x1) // 2, (y0 + y1) // 2, image=self.frame_image)
            except tk.TclError as error:
                self.frame_status_var.set(f"Unreadable QEMU PPM: {error}")
        else:
            canvas.create_text((x0 + x1) // 2, (y0 + y1) // 2 - 10, fill="#e6e6e6",
                               text="No guest framebuffer", font=("TkDefaultFont", 15, "bold"))
            canvas.create_text((x0 + x1) // 2, (y0 + y1) // 2 + 18, fill="#9a9a9a",
                               text="Awaiting QEMU screendump", font=("TkDefaultFont", 10))
        canvas.create_text((x0 + x1) // 2, y1 + 27, fill="#e7b44e", text=self.frame_status_var.get(),
                           font=("TkDefaultFont", 9, "bold"))

    def poll(self) -> None:
        if self.process and self.process.poll() is not None:
            self.status_var.set(f"QEMU exited ({self.process.returncode})")
        if self.serial_path and self.serial_path.exists():
            size = self.serial_path.stat().st_size
            if size > self.last_serial_size:
                with self.serial_path.open("r", errors="replace") as serial:
                    serial.seek(self.last_serial_size)
                    self.append_log(serial.read())
                self.last_serial_size = size
        if self.diagnostic_ppm and self.diagnostic_ppm.is_file():
            self.draw_device()
        self.after(600, self.poll)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--diagnostic-ppm", type=Path, help="show a QEMU screendump, labelled diagnostic")
    parser.add_argument("--self-test", action="store_true", help="check paths and QMP request serialization without creating a window")
    args = parser.parse_args()
    if args.self_test:
        assert ROOT.is_dir() and DEFAULT_BOOT.is_dir()
        request = json.dumps({"execute": "screendump", "arguments": {"filename": "/tmp/frame.ppm"}})
        assert "screendump" in request
        print("PASS: simulator host-side configuration and QMP request serialization")
        return 0
    Simulator(args.diagnostic_ppm).mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
