"""Unit tests for framework detection and package managers."""

import json
import tempfile
import unittest
from pathlib import Path

from openios.live_preview.core.framework_detector import FrameworkDetector
from openios.live_preview.core.models import FrameworkType
from openios.live_preview.core.project import ProjectManager


class TestFrameworkDetector(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_detect_react_vite(self) -> None:
        pkg = {
            "name": "my-react-app",
            "scripts": {"dev": "vite", "build": "vite build"},
            "dependencies": {"react": "^18.2.0", "react-dom": "^18.2.0"},
            "devDependencies": {"vite": "^5.0.0"},
        }
        with open(self.root / "package.json", "w") as f:
            json.dump(pkg, f)

        project = FrameworkDetector.detect(self.root)
        self.assertIsNotNone(project)
        self.assertEqual(project.framework, FrameworkType.REACT_VITE)
        self.assertEqual(project.name, "my-react-app")
        self.assertEqual(project.package_manager, "npm")

    def test_detect_package_managers(self) -> None:
        (self.root / "package.json").write_text("{}")
        (self.root / "pnpm-lock.yaml").write_text("")
        self.assertEqual(ProjectManager.detect_package_manager(self.root), "pnpm")

        (self.root / "pnpm-lock.yaml").unlink()
        (self.root / "yarn.lock").write_text("")
        self.assertEqual(ProjectManager.detect_package_manager(self.root), "yarn")

        (self.root / "yarn.lock").unlink()
        (self.root / "bun.lockb").write_text("")
        self.assertEqual(ProjectManager.detect_package_manager(self.root), "bun")

    def test_detect_expo_web(self) -> None:
        pkg = {
            "name": "expo-sample",
            "dependencies": {"expo": "~50.0.0", "react-native": "0.73.2"},
        }
        with open(self.root / "package.json", "w") as f:
            json.dump(pkg, f)

        project = FrameworkDetector.detect(self.root)
        self.assertIsNotNone(project)
        self.assertEqual(project.framework, FrameworkType.EXPO_WEB)

    def test_detect_flutter_web(self) -> None:
        (self.root / "pubspec.yaml").write_text("name: flutter_sample\ndependencies:\n  flutter:\n    sdk: flutter\n")
        project = FrameworkDetector.detect(self.root)
        self.assertIsNotNone(project)
        self.assertEqual(project.framework, FrameworkType.FLUTTER_WEB)
        self.assertEqual(project.name, "flutter_sample")

    def test_detect_static_web(self) -> None:
        (self.root / "index.html").write_text("<!DOCTYPE html><html><body><h1>Hello</h1></body></html>")
        project = FrameworkDetector.detect(self.root)
        self.assertIsNotNone(project)
        self.assertEqual(project.framework, FrameworkType.STATIC_WEB)


if __name__ == "__main__":
    unittest.main()
