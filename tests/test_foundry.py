"""Synthetic Product Foundry fixtures; do not imply independent user validation."""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("foundry", ROOT / "scripts" / "foundry.py")
foundry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(foundry)


class FoundryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "product"
        foundry.init(self.root, "A simple animation editor for beginners", "product-owner")
        self.source = Path(self.temp.name) / "draft.md"
        self.source.write_text("# Test draft\n\nSynthetic fixture content.\n", encoding="utf-8")

    def send_all(self, stage):
        for artifact in foundry.DOCS[stage]:
            foundry.submit(self.root, artifact, self.source, "writer")

    def finish_stage(self, stage, kind="self_check", actor="reviewer"):
        self.assertEqual(foundry.current(foundry.load(self.root)), stage)
        self.send_all(stage)
        foundry.review(self.root, "pass", kind, actor, "Synthetic review only")
        return foundry.confirm(self.root, "product-owner", "Confirm synthetic stage %d" % stage)

    def answer_three(self):
        for name in foundry.QUESTIONS:
            foundry.answer(self.root, name, "Synthetic answer to " + name, "product-owner")

    def test_init_preserves_idea_and_stage_zero(self):
        result = foundry.status(self.root)
        self.assertEqual(result["current_stage"], 0)
        self.assertEqual(result["status"], "PLANNING")
        self.assertIn("docs/00-asset-recall.md", result["stage_gate"]["missing_artifacts"])
        self.assertFalse(result["release_authorized"])

    def test_approval_rejected_without_core_questions(self):
        self.send_all(0)
        foundry.review(self.root, "pass", "self_check", "writer", "Looks plausible")
        with self.assertRaisesRegex(ValueError, "stage gate"):
            foundry.confirm(self.root, "product-owner", "OK")

    def test_answer_requires_known_key_and_open_stage_zero(self):
        with self.assertRaises(ValueError):
            foundry.answer(self.root, "magic", "a", "owner")
        self.answer_three()
        self.finish_stage(0)
        with self.assertRaises(ValueError):
            foundry.answer(self.root, "audience", "b", "owner")

    def test_review_blocker_prevents_confirm(self):
        self.answer_three()
        self.send_all(0)
        foundry.review(self.root, "blocked", "self_check", "reviewer", "Missing evidence")
        with self.assertRaises(ValueError):
            foundry.confirm(self.root, "owner", "OK")

    def test_independent_review_must_not_have_same_claimed_actor(self):
        self.answer_three()
        self.send_all(0)
        with self.assertRaisesRegex(ValueError, "submitter"):
            foundry.review(self.root, "pass", "independent_review", "writer", "Not independent")
        foundry.review(self.root, "pass", "independent_review", "external-reviewer", "Fixture")
        foundry.confirm(self.root, "owner", "OK")
        review = foundry.load(self.root)["stages"][0]["reviews"][0]
        self.assertFalse(review["identity_verified"])

    def test_optimistic_lock_blocks_stale_writes(self):
        revision = foundry.load(self.root)["revision"]
        foundry.answer(self.root, "audience", "beginner", "owner", expected=revision)
        with self.assertRaisesRegex(ValueError, "stale"):
            foundry.answer(self.root, "problem", "problem", "owner", expected=revision)

    def test_reject_unknown_path_and_empty_artifact(self):
        with self.assertRaisesRegex(ValueError, "stage"):
            foundry.submit(self.root, "docs/03-prd.md", self.source, "writer")
        with self.assertRaisesRegex(ValueError, "path"):
            foundry.file_under(self.root, "../escape.txt")
        self.source.write_text("")
        with self.assertRaisesRegex(ValueError, "empty"):
            foundry.submit(self.root, "docs/00-asset-recall.md", self.source, "writer")

    def test_tampered_draft_rejected(self):
        self.answer_three()
        self.send_all(0)
        (self.root / "docs/00-asset-recall.md").write_text("TAMPERED")
        foundry.review(self.root, "pass", "self_check", "reviewer", "Fixture")
        with self.assertRaisesRegex(ValueError, "stage gate"):
            foundry.confirm(self.root, "owner", "OK")

    def test_change_proposal_keeps_approved_baseline(self):
        self.answer_three()
        self.finish_stage(0)
        before = foundry.load(self.root)["stages"][0]["confirmation"].copy()
        result = foundry.propose(self.root, "feature", "Add community", "Explore retention", "agent")
        self.assertEqual(result["impact_from_stage"], 3)
        self.assertEqual(before, foundry.load(self.root)["stages"][0]["confirmation"])
        self.assertEqual(foundry.current(foundry.load(self.root)), 1)
        rejected = foundry.decide(self.root, result["id"], "reject", "owner", "Not MVP")
        self.assertEqual(rejected["status"], "rejected")

    def test_accepted_change_invalidates_downstream(self):
        self.answer_three()
        for i in range(5):
            self.finish_stage(i)
        change = foundry.propose(self.root, "feature", "Add new editing mode", "Observed need", "agent")
        result = foundry.decide(self.root, change["id"], "accept", "owner", "Approve scoped change")
        self.assertEqual(result["invalidated_stages"], [3, 4])
        self.assertEqual(result["current_stage"], 3)
        self.assertTrue(foundry.load(self.root)["stages"][2]["confirmed"])
        self.assertFalse(foundry.load(self.root)["stages"][3]["confirmed"])
        with self.assertRaisesRegex(ValueError, "stage gate"):
            foundry.confirm(self.root, "owner", "Reapprove without review")

    def test_handoff_needs_all_seven_stages(self):
        with self.assertRaisesRegex(ValueError, "before"):
            foundry.handoff(self.root, "owner")

    def test_complete_seven_stages_and_export(self):
        self.answer_three()
        for i in range(7):
            self.finish_stage(i)
        s = foundry.status(self.root)
        self.assertEqual(s["status"], "BLUEPRINT_READY")
        packet = foundry.handoff(self.root, "owner")
        self.assertFalse(packet["execution_authorized"])
        self.assertFalse(packet["release_authorized"])
        self.assertEqual(packet["project_revision"], s["revision"])
        self.assertTrue((self.root / ".foundry/HANDOFF.json").is_file())
        with self.assertRaises(ValueError):
            foundry.submit(self.root, "docs/03-prd.md", self.source, "writer")

    def test_handoff_detects_mutation_after_approval(self):
        self.answer_three()
        for i in range(7):
            self.finish_stage(i)
        (self.root / "docs/03-prd.md").write_text("Changed outside Foundry")
        with self.assertRaisesRegex(ValueError, "stale"):
            foundry.handoff(self.root, "owner")

    def test_cli_and_mcp_readonly_contract(self):
        call = [sys.executable, str(ROOT / "scripts/foundry.py"), "--project", str(self.root)]
        run = subprocess.run(call + ["next"], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(run.stdout)["stage"], 0)
        msgs = "\n".join([
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
            json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}),
            json.dumps({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                        "params": {"name": "foundry_status", "arguments": {}}}),
            json.dumps({"jsonrpc": "2.0", "id": 4, "method": "tools/call",
                        "params": {"name": "foundry_confirm", "arguments": {}}}),
        ]) + "\n"
        result = subprocess.run(call + ["mcp"], input=msgs, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = [json.loads(x) for x in result.stdout.splitlines()]
        self.assertEqual(len(lines), 4)
        self.assertEqual(len(lines[1]["result"]["tools"]), 2)
        self.assertEqual(lines[2]["result"]["content"][0]["type"], "text")
        self.assertIn("error", lines[3])


if __name__ == "__main__":
    unittest.main()
