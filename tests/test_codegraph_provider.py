"""Opt-in provider contract; mock only, no real external process/network."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import codegraph_provider as provider


class CodeGraphProviderTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.repo = self.root / "project"
        (self.repo / "src").mkdir(parents=True)
        (self.repo / "test").mkdir()
        (self.repo / "src" / "core.mjs").write_text("export const a = 1;\n")
        (self.repo / "test" / "core.test.mjs").write_text("fixture")
        (self.repo / "test" / "handler.test.mjs").write_text("fixture")
        self.bin = self.root / "fakegraph"
        self.bin.write_text("#!/usr/bin/env python3\nimport sys\n"
                            "print('test/core.test.mjs')\n"
                            "print('test/handler.test.mjs')\n")
        self.bin.chmod(0o700)

    def test_requires_explicit_opt_in(self):
        with self.assertRaisesRegex(ValueError, "opt-in"):
            provider.impact(self.repo, ["src/core.mjs"], self.bin)

    def test_rejects_missing_or_escaping_files(self):
        for path in ("../outside", "/etc/passwd", "missing.py"):
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    provider.impact(self.repo, [path], self.bin, opt_in=True)

    def test_rejects_sensitive_file_paths(self):
        (self.repo / ".env").write_text("PRIVATE")
        with self.assertRaises(ValueError):
            provider.impact(self.repo, [".env"], self.bin, opt_in=True)

    def test_returns_candidate_evidence_not_release_approval(self):
        result = provider.impact(self.repo, ["src/core.mjs"], self.bin, opt_in=True)
        self.assertEqual(result["affected_test_candidates"],
                         ["test/core.test.mjs", "test/handler.test.mjs"])
        self.assertFalse(result["agent_config_modified"])
        self.assertFalse(result["release_authorized"])
        self.assertEqual(result["graph_freshness"], "NOT_VERIFIED")
        self.assertNotIn("content", result)

    def test_rejects_untrusted_provider_result(self):
        self.bin.write_text("#!/usr/bin/env python3\nprint('../../private.key')\n")
        self.bin.chmod(0o700)
        with self.assertRaisesRegex(ValueError, "out-of-scope"):
            provider.impact(self.repo, ["src/core.mjs"], self.bin, opt_in=True)

    def test_prism_command_rejects_non_opt_in(self):
        command = [sys.executable, str(ROOT / "scripts" / "prism.py"),
                   "codegraph-impact", "--repo", str(self.repo),
                   "--changed", "src/core.mjs", "--codegraph-bin", str(self.bin)]
        denied = subprocess.run(command, capture_output=True, text=True)
        self.assertNotEqual(denied.returncode, 0)
        self.assertIn("opt-in", denied.stderr)
        allowed = subprocess.run(command + ["--allow-local-codegraph"],
                                 capture_output=True, text=True)
        self.assertEqual(allowed.returncode, 0, allowed.stderr)
        self.assertEqual(json.loads(allowed.stdout)["count"], 2)

    def test_forces_private_env(self):
        self.bin.write_text("#!/usr/bin/env python3\nimport os\n"
                            "print('test/core.test.mjs' if "
                            "os.getenv('DO_NOT_TRACK') == '1' and "
                            "os.getenv('CODEGRAPH_TELEMETRY') == '0' and "
                            "os.getenv('CODEGRAPH_NO_UPDATE_CHECK') == '1' "
                            "else 'invalid')\n")
        self.bin.chmod(0o700)
        result = provider.impact(self.repo, ["src/core.mjs"], self.bin, opt_in=True)
        self.assertEqual(result["count"], 1)


if __name__ == "__main__":
    unittest.main()
