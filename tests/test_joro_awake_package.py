"""Packaging checks: complete archive, matching checksum, no private files."""

import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile

REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "joro-awake"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = load("joro_awake_package", REPO / "setup-scripts/build_joro_awake_package.py")
installer = load("joro_awake_installer", SOURCE / "setup-scripts/install_keep_awake.py")


class PackageTests(unittest.TestCase):
    def test_archive_has_every_installer_input_and_matching_checksum(self):
        with tempfile.TemporaryDirectory(prefix="joro-package-") as directory:
            archive, sums, digest = builder.build(SOURCE, directory)
            self.assertEqual(digest, hashlib.sha256(archive.read_bytes()).hexdigest())
            self.assertEqual(sums.read_text(encoding="ascii").split()[0], digest)
            release = (SOURCE / "VERSION").read_text(encoding="utf-8").strip()
            prefix = f"joro-awake-{release}"
            with zipfile.ZipFile(archive) as bundle:
                self.assertIsNone(bundle.testzip())
                names = set(bundle.namelist())
            for name in installer.FILES + ("README.md", "LICENSE", "THIRD_PARTY_NOTICES.md"):
                self.assertIn(f"{prefix}/{name}", names)
            private = [name for name in names
                       if name.endswith(".pyc") or "/.git/" in name or "/.venv/" in name]
            self.assertEqual(private, [])


if __name__ == "__main__":
    unittest.main()
