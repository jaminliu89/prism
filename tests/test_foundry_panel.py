"""Synthetic expert panel contracts; no model or external tool calls."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("foundry", ROOT / "scripts/foundry.py")
foundry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(foundry)


class PanelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "product"
        foundry.init(self.root, "A planning application", "owner")
        self.md = Path(self.temp.name) / "draft.md"
        self.md.write_text("# Synthetic document\n", encoding="utf-8")
        for key in foundry.QUESTIONS:
            foundry.answer(self.root, key, "Fixture " + key, "owner")

    def submit_stage_zero(self):
        for path in foundry.DOCS[0]:
            foundry.submit(self.root, path, self.md, "writer")
        foundry.review(self.root, "pass", "self_check", "reviewer",
                       "Synthetic baseline only")

    def test_open_review_blocks_stage_even_with_documents(self):
        item = foundry.panel_open(self.root, "Which user segment first?", "owner")
        self.submit_stage_zero()
        self.assertEqual(item["topic"], "PNL-0001")
        self.assertEqual(len(foundry.next_step(self.root)["open_panel_topics"]), 1)
        with self.assertRaisesRegex(ValueError, "stage gate"):
            foundry.confirm(self.root, "owner", "Stage 0 approved")

    def test_opposition_and_challenger_supported(self):
        topic = foundry.panel_open(self.root, "Is this the MVP?", "owner")["topic"]
        foundry.panel_opinion(self.root, topic, "pm", "agent-a", "support", "medium",
                              "Scope fits", "Assumed user notes", "Users may disagree")
        foundry.panel_opinion(self.root, topic, "challenger", "agent-b", "oppose", "high",
                              "Too broad", "No demand evidence", "Paid tests may support it")
        self.assertTrue(foundry.panel.unresolved(foundry.load(self.root))[0]["serious_disagreement"])
        foundry.panel_resolve(self.root, topic, "revise", "owner", "Cut to core workflow")
        self.assertEqual(foundry.panel.unresolved(foundry.load(self.root)), [])
        self.assertFalse(foundry.panel.topic(foundry.load(self.root), topic)["independent_validation"])

    def test_cannot_resolve_without_adversarial_input(self):
        topic = foundry.panel_open(self.root, "Should we build?", "owner")["topic"]
        foundry.panel_opinion(self.root, topic, "pm", "agent-a", "support", "info",
                              "Yes", "Hypothesis", "Could be wrong")
        with self.assertRaisesRegex(ValueError, "adversarial"):
            foundry.panel_resolve(self.root, topic, "adopt", "owner", "Approved")

    def test_duplicate_claim_and_missing_provenance_rejected(self):
        topic = foundry.panel_open(self.root, "Choose product type", "owner")["topic"]
        with self.assertRaisesRegex(ValueError, "evidence"):
            foundry.panel_opinion(self.root, topic, "ux", "writer", "concern", "medium",
                                  "Design concern", "", "Counterexample")
        foundry.panel_opinion(self.root, topic, "ux", "writer", "concern", "medium",
                              "Design concern", "Interview not yet confirmed", "Alternative flow")
        with self.assertRaisesRegex(ValueError, "duplicate"):
            foundry.panel_opinion(self.root, topic, "ux", "writer", "support", "medium",
                                  "Alternate", "Notes", "Counterexample")

    def test_resolving_topic_requires_fresh_stage_review(self):
        topic = foundry.panel_open(self.root, "Can first users complete core task?", "owner")["topic"]
        self.submit_stage_zero()
        foundry.panel_opinion(self.root, topic, "challenger", "reviewer", "concern", "medium",
                              "Possible friction", "Assumption", "Users succeed")
        foundry.panel_resolve(self.root, topic, "defer", "owner", "Record test hypothesis")
        with self.assertRaisesRegex(ValueError, "stage gate"):
            foundry.confirm(self.root, "owner", "Outdated review")
        foundry.review(self.root, "pass", "self_check", "reviewer", "Reviewed after decision")
        foundry.confirm(self.root, "owner", "Stage reviewed")
        self.assertEqual(foundry.current(foundry.load(self.root)), 1)


if __name__ == "__main__":
    unittest.main()
