"""Architecture-first stage gates, Mermaid structural checks, and legacy compatibility."""
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SYS = ROOT / "scripts"
if str(SYS) not in sys.path:
    sys.path.insert(0, str(SYS))
import architecture_gate
spec = importlib.util.spec_from_file_location("foundry_arch", SYS / "foundry.py")
foundry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(foundry)
VALID = (ROOT / "tests/fixtures/architecture-sketch.md").read_text(encoding="utf-8")


class MermaidArchitectureGate(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "project"
        foundry.init(self.root, "Small local service for test users", "owner")
        self.source = Path(self.temp.name) / "plan.md"
        self.source.write_text("# Fixture document\n\nDraft only.\n")

    def before_architecture(self):
        for key in foundry.QUESTIONS:
            foundry.answer(self.root, key, "Fixture " + key, "owner")
        for stage in (0, 1):
            for path in foundry.DOCS[stage]:
                foundry.submit(self.root, path, self.source, "author")
            foundry.review(self.root, "pass", "self_check", "reviewer",
                           "Fixture; not independently verified")
            foundry.confirm(self.root, "owner", "Accept synthetic stage")
        self.assertEqual(foundry.current(foundry.load(self.root)), 2)

    def test_valid_mermaid_is_structure_only(self):
        result = architecture_gate.validate(VALID)
        self.assertIn("flowchart", result["diagrams"])
        self.assertIn("sequencediagram", result["diagrams"])
        self.assertFalse(result["technical_correctness_verified"])
        self.assertFalse(result["mermaid_render_verified"])
        self.assertFalse(result["contract_generation_authorized"])

    def test_missing_diagram_sections_and_unsafe_handler_rejected(self):
        with self.assertRaisesRegex(ValueError, "missing architecture reasoning"):
            architecture_gate.validate("# Idea only")
        with self.assertRaisesRegex(ValueError, "fenced mermaid"):
            architecture_gate.validate(VALID.replace("```mermaid", "```plain"))
        with self.assertRaisesRegex(ValueError, "unsafe Mermaid"):
            architecture_gate.validate(VALID.replace("    U[User]", "    click U href \"https://example.org\"\n    U[User]"))
        with self.assertRaisesRegex(ValueError, "visible dependency"):
            architecture_gate.validate(VALID.replace("    UI --> API", "    UI  API").replace("    U[User] --> UI[Browser client]", "    U[User]  UI[Browser client]").replace("    API --> DB", "    API  DB"))
        with self.assertRaisesRegex(ValueError, "too small"):
            architecture_gate.validate("x" * (architecture_gate.MAX_BYTES + 1))

    def test_stage_two_blocks_contract_until_valid_diagram_and_review(self):
        self.before_architecture()
        pending = foundry.next_step(self.root)["missing_documents"]
        self.assertIn(architecture_gate.ARCHITECTURE_PATH, pending)
        for path in foundry.DOCS[2]:
            if path != architecture_gate.ARCHITECTURE_PATH:
                foundry.submit(self.root, path, self.source, "author")
        with self.assertRaisesRegex(ValueError, "stage gate"):
            foundry.confirm(self.root, "owner", "Skip architecture")
        with self.assertRaisesRegex(ValueError, "architecture sketch blocked"):
            foundry.submit(self.root, architecture_gate.ARCHITECTURE_PATH,
                           self.source, "author")
        original = self.source.read_text()
        self.source.write_text(VALID)
        foundry.submit(self.root, architecture_gate.ARCHITECTURE_PATH,
                       self.source, "architect")
        self.assertEqual(foundry.current(foundry.load(self.root)), 2)
        with self.assertRaisesRegex(ValueError, "stage gate"):
            foundry.confirm(self.root, "owner", "Skip review")
        foundry.review(self.root, "pass", "self_check", "architect-reviewer",
                       "Reviewed design assumptions in synthetic fixture")
        foundry.confirm(self.root, "owner", "Confirm synthetic architecture stage")
        self.assertEqual(foundry.current(foundry.load(self.root)), 3)
        self.source.write_text(original)

    def test_architecture_change_invalidates_approved_stage_two(self):
        self.before_architecture()
        for path in foundry.DOCS[2]:
            source = Path(ROOT / "tests/fixtures/architecture-sketch.md") if path == architecture_gate.ARCHITECTURE_PATH else self.source
            foundry.submit(self.root, path, source, "author")
        foundry.review(self.root, "pass", "self_check", "reviewer", "fixture")
        foundry.confirm(self.root, "owner", "Review architecture baseline")
        event = foundry.propose(self.root, "architecture", "Change data trust boundary",
                                "New evidence affects architecture", "architect")
        result = foundry.decide(self.root, event["id"], "accept", "owner",
                                "Approve review of the affected architecture baseline")
        self.assertIn(2, result["invalidated_stages"])
        self.assertEqual(foundry.current(foundry.load(self.root)), 2)
        self.assertIn(architecture_gate.ARCHITECTURE_PATH,
                      foundry.next_step(self.root)["missing_documents"])

    def test_existing_foundry_data_keeps_legacy_stage_document_contract(self):
        data = foundry.load(self.root)
        data.pop("architecture_first_schema", None)
        foundry.save(self.root, data)
        self.assertNotIn(architecture_gate.ARCHITECTURE_PATH,
                         foundry.docs_for(foundry.load(self.root), 2))
        self.assertIn("docs/02-state-machines.md", foundry.docs_for(data, 2))

    def test_cli_diagram_structure_on_fixture(self):
        result = subprocess.run([sys.executable, str(SYS / "architecture_gate.py"),
                                 str(ROOT / "tests/fixtures/architecture-sketch.md")],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
