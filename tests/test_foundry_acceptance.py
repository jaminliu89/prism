"""CLI end-to-end acceptance through a real subprocess; synthetic decisions, no models."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ProductFoundryAcceptance(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name) / "scenario"
        self.document = Path(self.tmp.name) / "artifact.md"
        self.document.write_text("# Synthetic user-approved planning artifact\n\nEvidence: fixture only.\n")
        self.cli = [sys.executable, str(ROOT / "scripts/foundry.py"),
                    "--project", str(self.project)]

    def cli_call(self, command, *args, success=True):
        p = subprocess.run(self.cli + [command] + list(args), capture_output=True, text=True)
        if success:
            self.assertEqual(p.returncode, 0, p.stderr)
            try:
                return json.loads(p.stdout)
            except json.JSONDecodeError as exc:
                self.fail("CLI did not produce JSON: " + str(exc))
        self.assertNotEqual(p.returncode, 0, p.stdout)
        return p.stderr

    def docs(self, stage):
        return (
            ["docs/00-idea-brief.md", "docs/00-asset-recall.md"] if stage == 0 else
            ["docs/01-product-research.md"] if stage == 1 else
            ["docs/02-stories-and-journeys.md", "docs/02-state-machines.md"] if stage == 2 else
            ["docs/03-prd.md", "docs/03-design-system.md"] if stage == 3 else
            ["docs/04-architecture.md", "docs/04-technology-decisions.md",
             "docs/04-security-threat-model.md"] if stage == 4 else
            ["docs/05-roadmap.md", "docs/06-task-board.md",
             "docs/05-definition-of-done.md"] if stage == 5 else
            ["docs/07-consistency-audit.md", "docs/08-engineering-handoff.md",
             "docs/07-security-acceptance-plan.md"]
        )

    def approve(self, stage):
        for p in self.docs(stage):
            self.cli_call("submit", "--artifact", p, "--file",
                          str(self.document), "--actor", "writer")
        self.cli_call("review", "--verdict", "pass", "--kind", "self_check",
                      "--actor", "reviewer", "--note", "Synthetic review only")
        return self.cli_call("confirm", "--actor", "owner",
                             "--statement", "Confirm synthetic stage %d" % stage)

    def test_real_cli_idea_to_security_panel_to_handoff_to_revision(self):
        start = self.cli_call("init", "--idea",
                              "Create a private beginner animation design assistant",
                              "--actor", "owner")
        self.assertEqual(start["current_stage"], 0)
        self.assertIn("protected_assets", self.cli_call("next")["security_questions"])

        for key, value in (
            ("audience", "beginner animators"),
            ("problem", "editing flow is complex"),
            ("success", "finish one exported storyboard")):
            self.cli_call("answer", "--key", key, "--value", value, "--actor", "owner")

        p = self.cli_call("panel-open", "--question", "Should MVP include plugins?",
                          "--actor", "owner")
        key = p["topic"]
        self.cli_call("panel-opinion", "--id", key, "--role", "architect",
                      "--actor", "architect-a", "--verdict", "support",
                      "--severity", "medium", "--reasoning", "Extensibility",
                      "--evidence", "Hypothetical roadmap",
                      "--counterexample", "No real plugin demand")
        self.cli_call("panel-opinion", "--id", key, "--role", "challenger",
                      "--actor", "challenger-b", "--verdict", "oppose",
                      "--severity", "high", "--reasoning", "Expands trust boundary",
                      "--evidence", "Unverified external code",
                      "--counterexample", "Isolated vetted plugins")
        self.cli_call("panel-resolve", "--id", key, "--outcome", "defer",
                      "--actor", "owner", "--rationale", "Focus on core workflow")
        self.approve(0)

        for stage in (1, 2, 3):
            self.approve(stage)

        # Gate must block the nominal document sign-off until each risk is addressed.
        for path in self.docs(4):
            self.cli_call("submit", "--artifact", path, "--file",
                          str(self.document), "--actor", "writer")
        self.cli_call("review", "--verdict", "pass", "--kind", "self_check",
                      "--actor", "reviewer", "--note", "Fixture")
        rejected = self.cli_call("confirm", "--actor", "owner",
                                 "--statement", "Skipping safety", success=False)
        self.assertIn("stage gate failed", rejected)
        status = self.cli_call("security-status")
        for field in status["questions"]:
            self.cli_call("security-profile", "--key", field,
                          "--value", "Planning-only classification",
                          "--actor", "owner")
        for code in status["threat_catalog"]:
            self.cli_call("security-assess", "--code", code,
                          "--disposition", "mitigate", "--reason", "Fixture plan",
                          "--actor", "security-reviewer",
                          "--asset", "private workflow",
                          "--boundary", "external client boundary",
                          "--attack-path", "hypothetical public artifact exposure",
                          "--control", "private orchestration and server authorization",
                          "--verification", "planned isolated authorized test")
        self.approve(4)
        self.approve(5)
        self.approve(6)

        before = self.cli_call("status")
        self.assertEqual(before["status"], "BLUEPRINT_READY")
        handoff = self.cli_call("handoff", "--actor", "owner")
        self.assertFalse(handoff["execution_authorized"])
        self.assertFalse(handoff["release_authorized"])
        self.assertFalse(handoff["security_assurance"]["runtime_security_verified"])
        self.assertEqual(handoff["security_assurance"]["reverse_engineering_difficulty"],
                         "NOT_MEASURED")

        # A feature idea alone must not rewrite the approved baseline.
        change = self.cli_call("propose", "--category", "feature",
                               "--description", "Add a social feed",
                               "--rationale", "Potential future retention",
                               "--actor", "agent")
        self.assertEqual(self.cli_call("status")["status"], "BLUEPRINT_READY")
        decided = self.cli_call("decide", "--id", change["id"],
                                "--outcome", "accept", "--actor", "owner",
                                "--reason", "Consciously re-scope MVP")
        self.assertEqual(decided["current_stage"], 3)
        self.assertIn("docs/03-prd.md", self.cli_call("next")["missing_documents"])
        self.assertIn("before all seven stages",
                      self.cli_call("handoff", "--actor", "agent", success=False))


if __name__ == "__main__":
    unittest.main()
