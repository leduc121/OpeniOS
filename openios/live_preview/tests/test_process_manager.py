"""Unit tests for dev server process lifecycle and URL parsing."""

import sys
import tempfile
import time
import unittest
from pathlib import Path

from openios.live_preview.core.models import ServerState
from openios.live_preview.core.process_manager import URL_REGEX, ProcessManager


class TestProcessManager(unittest.TestCase):
    def test_url_regex(self) -> None:
        lines = [
            "  ➜  Local:   http://localhost:5173/",
            "  ➜  Network: http://192.168.1.100:5173/",
            "Vite dev server running at: http://127.0.0.1:3000/app",
            "Starting web server at http://0.0.0.0:8080",
        ]
        matches = []
        for line in lines:
            m = URL_REGEX.search(line)
            if m:
                matches.append(m.group(1))

        self.assertEqual(len(matches), 4)
        self.assertEqual(matches[0], "http://localhost:5173/")
        self.assertEqual(matches[2], "http://127.0.0.1:3000/app")

    def test_process_lifecycle(self) -> None:
        ready_url: list[str] = []
        logs: list[str] = []

        pm = ProcessManager(
            on_log=lambda l: logs.append(l),
            on_ready=lambda u: ready_url.append(u),
        )

        with tempfile.TemporaryDirectory() as td:
            # Run simple python script outputting a dummy dev server URL
            cmd = [
                sys.executable,
                "-u",
                "-c",
                "import time; print('Ready at http://127.0.0.1:9999/'); time.sleep(10)",
            ]
            started = pm.start_process(cmd, cwd=Path(td))
            self.assertTrue(started)

            # Wait for URL capture
            for _ in range(30):
                if ready_url:
                    break
                time.sleep(0.1)

            self.assertEqual(len(ready_url), 1)
            self.assertEqual(ready_url[0], "http://127.0.0.1:9999/")
            self.assertEqual(pm.state, ServerState.READY)

            # Clean shutdown
            pm.stop_process(timeout_sec=1.0)
            self.assertEqual(pm.state, ServerState.STOPPED)
            self.assertIsNone(pm.process)


if __name__ == "__main__":
    unittest.main()
