import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "sep_evidence_gate", ROOT / "scripts/sep_evidence_gate.py"
)
sep_evidence_gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sep_evidence_gate)

FIXTURE = ROOT / "docs/verification/sep/pilot-video-to-text-pr11.json"


class SepEvidenceGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.manifest = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.path = self.base / "sep.json"

    def check(self, data=None):
        self.path.write_text(
            json.dumps(data if data is not None else self.manifest, ensure_ascii=False),
            encoding="utf-8",
        )
        return sep_evidence_gate.check(self.path)

    def test_pilot_fixture_valid(self):
        result = self.check()
        self.assertEqual(result["status"], "STRUCTURALLY_VALID")
        self.assertEqual(result["pass_claims"], 3)
        self.assertFalse(result["release_authorized"])

    def test_pass_without_evidence_rejected(self):
        data = copy.deepcopy(self.manifest)
        data["tests"][0]["evidence"] = ""
        with self.assertRaises(ValueError):
            self.check(data)

    def test_not_run_with_evidence_rejected(self):
        data = copy.deepcopy(self.manifest)
        data["tests"].append(
            {"command": "echo skip", "result": "NOT_RUN", "evidence": "fake"}
        )
        with self.assertRaises(ValueError):
            self.check(data)

    def test_release_authorized_true_rejected(self):
        data = copy.deepcopy(self.manifest)
        data["release_authorized"] = True
        with self.assertRaises(ValueError):
            self.check(data)

    def test_template_roundtrip_blocked_until_filled(self):
        tpl = sep_evidence_gate.template("PR-0", ["x"])
        tpl["tests"][0]["result"] = "PASS"
        tpl["tests"][0]["evidence"] = "filled"
        tpl["head_sha"] = "abc1234"
        self.path.write_text(json.dumps(tpl), encoding="utf-8")
        result = sep_evidence_gate.check(self.path)
        self.assertEqual(result["status"], "STRUCTURALLY_VALID")


if __name__ == "__main__":
    unittest.main()
