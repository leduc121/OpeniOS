"""Unit tests for framework adapter registry and validation."""

import json
import tempfile
import unittest
from pathlib import Path

from openios.live_preview.adapters.expo_web import ExpoWebAdapter
from openios.live_preview.adapters.flutter_web import FlutterWebAdapter
from openios.live_preview.adapters.registry import adapter_registry
from openios.live_preview.adapters.static_web import StaticWebAdapter
from openios.live_preview.adapters.vite_react import ViteReactAdapter
from openios.live_preview.core.models import FrameworkType, ProjectInfo


class TestAdapters(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_vite_react_adapter_validation(self) -> None:
        adapter = ViteReactAdapter()
        valid, msg = adapter.validate(self.root)
        self.assertFalse(valid)
        self.assertIn("package.json", msg)

        # Add package.json
        (self.root / "package.json").write_text('{"name": "test"}')
        valid, msg = adapter.validate(self.root)
        self.assertFalse(valid)
        self.assertIn("node_modules", msg)

        # Add node_modules
        (self.root / "node_modules").mkdir()
        valid, msg = adapter.validate(self.root)
        self.assertTrue(valid)

    def test_expo_web_adapter(self) -> None:
        adapter = ExpoWebAdapter()
        (self.root / "package.json").write_text('{"name": "test-expo", "dependencies": {"expo": "^50.0"}}')
        self.assertTrue(adapter.detect(self.root))

    def test_flutter_web_adapter(self) -> None:
        adapter = FlutterWebAdapter()
        (self.root / "pubspec.yaml").write_text("name: flutter_app")
        self.assertTrue(adapter.detect(self.root))

    def test_adapter_registry_lookup(self) -> None:
        proj_vite = ProjectInfo(path=self.root, name="vite", framework=FrameworkType.REACT_VITE)
        adapter = adapter_registry.find_adapter(proj_vite)
        self.assertIsInstance(adapter, ViteReactAdapter)

        proj_expo = ProjectInfo(path=self.root, name="expo", framework=FrameworkType.EXPO_WEB)
        adapter = adapter_registry.find_adapter(proj_expo)
        self.assertIsInstance(adapter, ExpoWebAdapter)

        proj_flutter = ProjectInfo(path=self.root, name="flutter", framework=FrameworkType.FLUTTER_WEB)
        adapter = adapter_registry.find_adapter(proj_flutter)
        self.assertIsInstance(adapter, FlutterWebAdapter)


if __name__ == "__main__":
    unittest.main()
