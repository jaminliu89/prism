"""Integration regression against Prism's real Foundry CLI data model."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_module(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


foundry = read_module("foundry", "foundry.py")
collab = read_module("agent_collaboration", "agent_collaboration.py")


class RealFoundryHandoffTests(unittest.TestCase):
    def test_real_foundry_task_lifecycle(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "product"
            foundry.init(root, "A synthetic content creator tool", "owner")
            created = foundry.assign_task(root, "research", "docs/00-asset-recall.md",
                                          "Research existing assets", "owner")
            task_id = created["id"]
            self.assertIn(task_id, collab.plan(collab.load(root), root)["parallel_ready"])
            packet = collab.packet(collab.load(root), task_id, root)
            self.assertFalse(packet["execution_authorized"])
            self.assertEqual(packet["output_document"], "docs/00-asset-recall.md")

            foundry.claim_task(root, task_id, "real-synthetic-agent")
            self.assertIn(task_id, collab.plan(collab.load(root), root)["already_claimed"])
            document = Path(temp) / "draft.md"
            document.write_text("# Evidence\n\nOffline synthetic content.\n", encoding="utf-8")
            foundry.deliver_task(root, task_id, document, "real-synthetic-agent")
            state = collab.load(root)
            task = next(t for t in state["tasks"] if t["id"] == task_id)
            receipt = collab.inspect_artifact(root, state, task)
            self.assertEqual(receipt["status"], "ARTIFACT_HASH_MATCH")
            self.assertEqual(receipt["quality_assurance"], "NOT_VERIFIED")


if __name__ == "__main__":
    unittest.main()
