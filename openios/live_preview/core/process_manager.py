"""Robust subprocess lifecycle and dev server process manager."""

from __future__ import annotations

import os
import re
import signal
import subprocess
import threading
import time
from pathlib import Path
from typing import Callable, Optional
from openios.live_preview.core.models import ServerState

# Regex to detect dev-server readiness URLs
URL_REGEX = re.compile(
    r"(https?://(?:localhost|127\.0\.0\.1|0\.0\.0\.0|\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d+)(?:/[^\s]*)?)",
    re.IGNORECASE,
)


import atexit
import socket

def find_available_port(preferred: int = 5173) -> int:
    """Find a free TCP port on 127.0.0.1, starting with preferred if unbound."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("127.0.0.1", preferred))
            return preferred
        except OSError:
            pass
    # Get ephemeral unused port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]

class ProcessManager:
    """Manages dev server process tree with isolated process group, log streaming, and URL detection."""

    _active_instances: list[ProcessManager] = []

    def __init__(
        self,
        on_log: Optional[Callable[[str], None]] = None,
        on_ready: Optional[Callable[[str], None]] = None,
        on_state_change: Optional[Callable[[ServerState], None]] = None,
    ) -> None:
        self.process: Optional[subprocess.Popen] = None
        self.state: ServerState = ServerState.STOPPED
        self.preview_url: Optional[str] = None
        self.logs: list[str] = []
        self._on_log = on_log
        self._on_ready = on_ready
        self._on_state_change = on_state_change
        self._reader_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        ProcessManager._active_instances.append(self)

    @classmethod
    def cleanup_all(cls) -> None:
        for inst in list(cls._active_instances):
            inst.stop_process()

    def _set_state(self, new_state: ServerState) -> None:
        self.state = new_state
        if self._on_state_change:
            try:
                self._on_state_change(new_state)
            except Exception:
                pass

    def start_process(
        self,
        command: list[str],
        cwd: Path,
        env: Optional[dict[str, str]] = None,
        fallback_port: int = 5173,
    ) -> bool:
        """Start a dev server command in its own process group with output piping."""
        self.stop_process()

        with self._lock:
            self.logs.clear()
            self.preview_url = None
            self._set_state(ServerState.STARTING)

            spawn_env = os.environ.copy()
            if env:
                spawn_env.update(env)
            # Ensure interactive colors don't mangle URLs and PATH contains node/flutter
            spawn_env["FORCE_COLOR"] = "0"
            spawn_env["NO_COLOR"] = "1"

            # Add node nvm path and flutter path if present
            nvm_bin = Path.home() / ".config/nvm/versions/node/v22.23.2/bin"
            flutter_bin = Path.home() / "develop/flutter/bin"
            extra_paths = []
            if nvm_bin.is_dir():
                extra_paths.append(str(nvm_bin))
            if flutter_bin.is_dir():
                extra_paths.append(str(flutter_bin))
            if extra_paths:
                spawn_env["PATH"] = ":".join(extra_paths) + ":" + spawn_env.get("PATH", "")

            try:
                self._log(f"[OpeniOS] Starting dev server: {' '.join(command)}")
                self._log(f"[OpeniOS] Working directory: {cwd}")

                self.process = subprocess.Popen(
                    command,
                    cwd=str(cwd),
                    env=spawn_env,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    preexec_fn=os.setsid,  # Create distinct process group
                )
            except Exception as e:
                self._log(f"[OpeniOS Error] Failed to launch dev server: {e}")
                self._set_state(ServerState.ERROR)
                return False

            self._reader_thread = threading.Thread(
                target=self._monitor_stream,
                args=(fallback_port,),
                daemon=True,
            )
            self._reader_thread.start()
            return True

    def send_input(self, text: str) -> bool:
        """Send input text to the running dev server stdin (e.g. 'r' for Flutter hot reload)."""
        if self.process and self.process.stdin:
            try:
                self.process.stdin.write(text)
                self.process.stdin.flush()
                return True
            except Exception as e:
                self._log(f"[OpeniOS Warning] Error sending stdin: {e}")
        return False

    def _log(self, message: str) -> None:
        self.logs.append(message)
        if self._on_log:
            try:
                self._on_log(message)
            except Exception:
                pass

    def _monitor_stream(self, fallback_port: int) -> None:
        if not self.process or not self.process.stdout:
            return

        found_url = False
        try:
            for line in iter(self.process.stdout.readline, ""):
                line_clean = line.rstrip()
                if line_clean:
                    self._log(line_clean)

                if not found_url:
                    match = URL_REGEX.search(line_clean)
                    if match:
                        raw_url = match.group(1)
                        # Normalize 0.0.0.0 to 127.0.0.1 for localhost security
                        clean_url = re.sub(r"//0\.0\.0\.0:", "//127.0.0.1:", raw_url)
                        self.preview_url = clean_url
                        found_url = True
                        self._set_state(ServerState.READY)
                        self._log(f"[OpeniOS] Detected Live Preview URL: {self.preview_url}")
                        if self._on_ready:
                            try:
                                self._on_ready(self.preview_url)
                            except Exception:
                                pass
        except Exception as e:
            self._log(f"[OpeniOS Log Error] {e}")

        # Process exited
        retcode = self.process.poll() if self.process else -1
        self._log(f"[OpeniOS] Dev server process terminated (exit code: {retcode})")
        if self.state != ServerState.STOPPED:
            self._set_state(ServerState.STOPPED)

    def stop_process(self, timeout_sec: float = 3.0) -> None:
        """Gracefully terminate only the spawned process group, escalating to SIGKILL if bounded."""
        with self._lock:
            if not self.process:
                self._set_state(ServerState.STOPPED)
                return

            proc = self.process
            self.process = None

        pid = proc.pid
        self._log(f"[OpeniOS] Terminating dev server process tree (PID group {pid})...")

        try:
            pgid = os.getpgid(pid)
            os.killpg(pgid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        except Exception as e:
            self._log(f"[OpeniOS Warning] Error sending SIGTERM: {e}")

        # Wait bounded time
        start_t = time.time()
        while time.time() - start_t < timeout_sec:
            if proc.poll() is not None:
                break
            time.sleep(0.1)

        # Force kill if still lingering
        if proc.poll() is None:
            self._log(f"[OpeniOS] Process group {pid} still running; sending SIGKILL...")
            try:
                pgid = os.getpgid(pid)
                os.killpg(pgid, signal.SIGKILL)
            except Exception:
                pass
            try:
                proc.wait(timeout=1.0)
            except Exception:
                pass

        self._set_state(ServerState.STOPPED)
        self._log("[OpeniOS] Dev server stopped cleanly.")


# Register global atexit hook to terminate spawned process groups
atexit.register(ProcessManager.cleanup_all)
