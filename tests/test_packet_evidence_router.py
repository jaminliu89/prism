"""Pure synthetic packet router checks; no interface access or Wireshark binaries."""
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/packet_evidence_router.py"
spec = importlib.util.spec_from_file_location("packet_evidence_router", SCRIPT)
router = importlib.util.module_from_spec(spec)
spec.loader.exec_module(router)


class PacketEvidenceTests(unittest.TestCase):
    def test_offline_plan_has_correct_owner_and_no_executions(self):
        r = router.route("offline_protocol_timeline", "owned_capture", ["tshark"])
        self.assertEqual(r["selected"], "tshark")
        self.assertEqual(r["primary_in_group"], "agent-reverse-engineering")
        self.assertEqual(r["specialist"], "network-packet-intelligence")
        self.assertFalse(r["tool_executed"])
        self.assertFalse(r["capture_started"])
        self.assertFalse(r["authorization_verified"])
        self.assertFalse(r["release_authorized"])

    def test_correct_engine_by_intent(self):
        self.assertEqual(router.route("capture_metadata", "authorized_lab")["candidates"][0], "capinfos")
        self.assertEqual(router.route("packet_subset_export", "owned_capture")["candidates"][0], "editcap")
        self.assertIsNone(router.route("capture_metadata", "owned_capture")["selected"])

    def test_reject_unauthorized_and_bogus_tool(self):
        for intent, scope in (("offline_protocol_timeline", "public_read"), ("capture_metadata", "owned_interface"), ("live_capture", "owned_capture"), ("live_capture", "owned_interface")):
            with self.subTest(intent=intent, scope=scope), self.assertRaises(ValueError):
                router.route(intent, scope)
        with self.assertRaises(ValueError):
            router.route("capture_metadata", "owned_capture", ["unknown"])
        r = router.route("live_capture", "owned_interface", live_capture_approved=True)
        self.assertEqual(r["status"], "PLAN_ONLY")
        self.assertFalse(r["capture_started"])

    def test_verify_hash_and_redaction_guard(self):
        with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as outside:
            root = Path(td)
            proof = root / "packet-summary.json"
            proof.write_text('{"synthetic":"only"}')
            row = {
                "task_id": "t1", "target": "synthetic-pcap", "revision": "r1",
                "scope": "owned_capture", "tool": "tshark", "tool_version": "fixture",
                "command_or_filter": "fixture: read only", "observed_at": "fixture-time",
                "artifact_path": proof.name, "sha256": hashlib.sha256(proof.read_bytes()).hexdigest(),
                "redaction_status": "reviewed", "claim_level": "observed", "limits": ["fixture"]
            }
            self.assertEqual(router.verify_record(row, root)["status"], "STRUCTURALLY_VERIFIED_ONLY")
            row["sha256"] = "0" * 64
            with self.assertRaisesRegex(ValueError, "hash"):
                router.verify_record(row, root)
            row["sha256"] = hashlib.sha256(proof.read_bytes()).hexdigest()
            row["artifact_path"] = "../outside"
            with self.assertRaisesRegex(ValueError, "relative"):
                router.verify_record(row, root)
            row["artifact_path"] = "link"
            (root / "link").symlink_to(Path(outside) / "not-here")
            with self.assertRaisesRegex(ValueError, "Symlink"):
                router.verify_record(row, root)
            row["artifact_path"] = proof.name
            row["redaction_status"] = "not_reviewed"
            row["public_export"] = True
            with self.assertRaisesRegex(ValueError, "public export"):
                router.verify_record(row, root)

    def test_cli_output(self):
        output = subprocess.check_output([sys.executable, str(SCRIPT), "route", "--intent",
                                          "capture_metadata", "--access", "owned_capture"], text=True)
        self.assertEqual(json.loads(output)["candidates"][0], "capinfos")


if __name__ == "__main__":
    unittest.main()
