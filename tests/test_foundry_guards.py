"""Synthetic planning guards; no external targets are inspected."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("foundry", ROOT / "scripts/foundry.py")
foundry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(foundry)


class FoundryGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "example"
        foundry.init(self.root, "A safe AI product planner", "owner")
        self.doc = Path(self.tmp.name) / "fixture.md"
        self.doc.write_text("# Fictional planning document\n", encoding="utf-8")

    def complete_before_architecture(self):
        for key in foundry.QUESTIONS:
            foundry.answer(self.root, key, "Fixture " + key, "owner")
        for stage in range(4):
            for path in foundry.DOCS[stage]:
                foundry.submit(self.root, path, self.doc, "writer")
            foundry.review(self.root, "pass", "self_check", "reviewer", "Synthetic")
            foundry.confirm(self.root, "owner", "Confirm fixture")

    def complete_security_design(self):
        for key in foundry.guard.PROFILE:
            foundry.security_profile(self.root, key, "Fictional category only", "owner")
        for code in foundry.guard.CATALOG:
            foundry.security_assess(
                self.root, code, "mitigate", "Example planning proposal", "planner",
                "example protected component", "untrusted client boundary",
                "hypothetical unauthorized exposure", "separate privileged server operations",
                "planned negative test against isolated test account")

    def test_security_questions_start_with_product_idea(self):
        questions = foundry.next_step(self.root)["security_questions"]
        self.assertIn("protected_assets", questions)
        self.assertIn("trust_boundary", questions)
        self.assertFalse(foundry.guard.gate(foundry.load(self.root))["design_ready"])

    def test_high_risk_not_automatically_accepted(self):
        with self.assertRaises(ValueError):
            foundry.security_assess(self.root, "ORCHESTRATION_EXPOSURE",
                                    "accept_risk", "No reason to protect it", "owner")
        with self.assertRaises(ValueError):
            foundry.security_assess(self.root, "ORCHESTRATION_EXPOSURE",
                                    "mitigate", "Missing a test plan", "owner")

    def test_stage_four_requires_security_profile_and_threat_review(self):
        self.complete_before_architecture()
        for path in foundry.DOCS[4]:
            foundry.submit(self.root, path, self.doc, "writer")
        foundry.review(self.root, "pass", "self_check", "reviewer", "Synthetic")
        with self.assertRaisesRegex(ValueError, "stage gate"):
            foundry.confirm(self.root, "owner", "Ignoring security risks")
        self.complete_security_design()
        self.assertIn("docs/04-security-threat-model.md",
                      foundry.next_step(self.root)["missing_documents"])
        for path in foundry.DOCS[4]:
            foundry.submit(self.root, path, self.doc, "writer")
        foundry.review(self.root, "pass", "self_check", "reviewer", "Synthetic")
        foundry.confirm(self.root, "owner", "Confirm only design plan")
        self.assertFalse(foundry.guard.gate(foundry.load(self.root))["operationally_verified"])

    def test_changed_risk_invalidates_review(self):
        self.complete_before_architecture()
        self.complete_security_design()
        for path in foundry.DOCS[4]:
            foundry.submit(self.root, path, self.doc, "writer")
        foundry.review(self.root, "pass", "self_check", "reviewer", "Synthetic")
        foundry.security_assess(self.root, "RESOURCE_ABUSE", "not_applicable",
                                "No paid calls in this hypothetical app", "planner")
        self.assertIn("docs/04-security-threat-model.md",
                      foundry.next_step(self.root)["missing_documents"])
        with self.assertRaisesRegex(ValueError, "stage gate"):
            foundry.confirm(self.root, "owner", "Stale version")

    def test_scope_limited_agent_task_handoff(self):
        task = foundry.assign_task(self.root, "research", "docs/00-asset-recall.md",
                                   "Prepare asset recall notes", "owner")
        self.assertEqual(task["authorization"], "PLANNING_DOCUMENT_ONLY")
        with self.assertRaises(ValueError):
            foundry.deliver_task(self.root, task["id"], self.doc, "writer")
        foundry.claim_task(self.root, task["id"], "researcher")
        with self.assertRaises(ValueError):
            foundry.deliver_task(self.root, task["id"], self.doc, "other")
        result = foundry.deliver_task(self.root, task["id"], self.doc, "researcher")
        self.assertEqual(result["status"], "delivered")
        self.assertEqual((self.root / "docs/00-asset-recall.md").read_bytes(),
                         self.doc.read_bytes())

    def test_task_outside_current_stage_is_rejected(self):
        with self.assertRaises(ValueError):
            foundry.assign_task(self.root, "architect", "docs/04-security-threat-model.md",
                                "Incorrect stage", "owner")
        with self.assertRaises(ValueError):
            foundry.assign_task(self.root, "unknown-role", "docs/00-asset-recall.md",
                                "Wrong role", "owner")

    def test_pending_task_blocks_approval(self):
        for key in foundry.QUESTIONS:
            foundry.answer(self.root, key, "Fixture answer", "owner")
        task = foundry.assign_task(self.root, "research", "docs/00-asset-recall.md",
                                   "Collect facts", "owner")
        foundry.submit(self.root, "docs/00-asset-recall.md", self.doc, "writer")
        foundry.review(self.root, "pass", "self_check", "reviewer", "Synthetic")
        with self.assertRaisesRegex(ValueError, "stage gate"):
            foundry.confirm(self.root, "owner", "Early approval")
        foundry.claim_task(self.root, task["id"], "researcher")
        foundry.deliver_task(self.root, task["id"], self.doc, "researcher")
        foundry.review(self.root, "pass", "self_check", "reviewer", "Synthetic")
        foundry.confirm(self.root, "owner", "Deliverable confirmed")

    def test_security_draft_discloses_no_certification(self):
        draft = foundry.guard.render(foundry.load(self.root))
        self.assertIn("ORCHESTRATION_EXPOSURE", draft)
        self.assertIn("no security certification", draft)
        self.assertIn("NOT_MEASURED", draft)

    def test_prior_state_without_security_is_not_validated(self):
        data = foundry.load(self.root)
        data.pop("security")
        for stage in data["stages"]:
            stage["confirmed"] = True
        foundry.save(self.root, data)
        self.assertEqual(foundry.status(self.root)["status"], "SECURITY_DESIGN_INCOMPLETE")
        with self.assertRaisesRegex(ValueError, "security design review"):
            foundry.handoff(self.root, "owner")


if __name__ == "__main__":
    unittest.main()
