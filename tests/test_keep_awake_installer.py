"""Small pure settings-merge checks. No real configuration is edited here."""

import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / "setup-scripts/install_keep_awake.py"
spec = importlib.util.spec_from_file_location("keep_awake_installer", path)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallerTests(unittest.TestCase):
    def test_existing_hooks_and_settings_are_preserved(self):
        original = {"env": {"EXAMPLE": "keep"}, "hooks": {
            "Stop": [{"hooks": [{"type": "command", "command": "user-stop"}]}],
            "SessionStart": [{"hooks": [{"type": "command", "command": "user-start"}]}]}}
        updated = installer.hooks(original, None, "joro-command")
        self.assertEqual(updated["hooks"]["Stop"], original["hooks"]["Stop"])
        self.assertEqual(updated["hooks"]["SessionStart"], original["hooks"]["SessionStart"])
        self.assertEqual(updated["env"], original["env"])
        self.assertNotIn("PreToolUse", original["hooks"])

    def test_repeat_install_and_interrupted_manifest_recovery_are_idempotent(self):
        once = installer.hooks({}, None, "joro-command")
        self.assertEqual(installer.hooks(once, "joro-command", "joro-command"), once)
        self.assertEqual(installer.hooks(once, None, "joro-command"), once)

    def test_uninstall_preserves_unrelated_callbacks_in_mixed_group(self):
        original = {"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [
            {"command": "joro-command"}, {"command": "user-command"}]}]}}
        updated = installer.hooks(original, "joro-command", None)
        self.assertEqual(updated["hooks"]["PreToolUse"], [{"matcher": "Bash", "hooks": [{"command": "user-command"}]}])

    def test_uninstall_does_not_rewrite_unrelated_empty_groups(self):
        original = {"hooks": {"Stop": [{"hooks": []}]}}
        self.assertEqual(installer.hooks(original, "joro-command", None), original)


if __name__ == "__main__":
    unittest.main()
