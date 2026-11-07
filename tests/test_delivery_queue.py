"""Negative tests for advisory cross-repository Mission queue; no GitHub IO or model calls."""
import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/delivery_queue.py"
SPEC = importlib.util.spec_from_file_location("delivery_queue", SCRIPT)
queue = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(queue)
PLAN = json.loads((ROOT / "docs/delivery/mission-index.json").read_text(encoding="utf-8"))


class DeliveryQueueTests(unittest.TestCase):
    def test_plan_is_only_owner_repo_index(self):
        result = queue.validate(PLAN)
        self.assertEqual(len(result), 8)
        self.assertTrue(all("status" not in t for t in PLAN["work_packages"]))
        self.assertFalse(queue.triage(PLAN)["release_authorized"])
        self.assertEqual(queue.triage(PLAN)["status"], "TRIAGE_ONLY")

    def test_first_work_packages_are_ready_for_inspection_not_release(self):
        r = queue.triage(PLAN)
        self.assertEqual(r["next"]["id"], "WP-01")
        self.assertEqual([x["id"] for x in r["parallel_candidates"]], ["WP-01", "WP-03"])
        self.assertIn("WP-05", [x["id"] for x in r["blocked"]])
        self.assertFalse(r["independent_review_authenticated"])

    def test_local_pass_forgery_rejected_not_promoted(self):
        issue = PLAN["work_packages"][0]["issue"]
        for payload in (
            {"issues": {issue: "PASS"}},
            {"issues": {issue: {"status": "PASS"}}},
            {"issues": {issue: "approved"}},
            {"issues": {issue: "closed"}, "reviewer": "coder-created-admin"},
        ):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                queue.triage(PLAN, payload)

    def test_all_issue_closures_never_authorize_release(self):
        obs = {"issues": {
            task["issue"]: "closed" for task in PLAN["work_packages"]
        }}
        obs["issues"].update({
            link: "closed" for task in PLAN["work_packages"]
            for link in task.get("external_blockers", [])
        })
        r = queue.triage(PLAN, obs)
        self.assertIsNone(r["next"])
        self.assertEqual(len(r["claimed_closed_requires_verification"]), 8)
        self.assertFalse(r["release_authorized"])

    def test_dependency_state_is_only_advisory(self):
        obs = {"issues": {
            PLAN["work_packages"][0]["issue"]: "closed"
        }}
        result = queue.triage(PLAN, obs)
        self.assertEqual(result["next"]["id"], "WP-02")
        self.assertEqual(result["next"]["dependencies"][0]["claimed_state"], "closed")
        self.assertFalse(result["release_authorized"])

    def test_no_ghost_tasks_or_unknown_requirements(self):
        p = copy.deepcopy(PLAN)
        p["work_packages"][1]["depends_on"] = ["WP-99"]
        with self.assertRaisesRegex(ValueError, "DEPENDENCY_UNKNOWN"):
            queue.validate(p)
        p = copy.deepcopy(PLAN)
        p["work_packages"][0]["acceptance_ids"] = []
        with self.assertRaisesRegex(ValueError, "ACCEPTANCE_UNMAPPED"):
            queue.validate(p)

    def test_cycle_self_dependency_and_duplicate_issue_fail(self):
        p = copy.deepcopy(PLAN)
        p["work_packages"][0]["depends_on"] = ["WP-02"]
        with self.assertRaisesRegex(ValueError, "DEPENDENCY_CYCLE"):
            queue.validate(p)
        p = copy.deepcopy(PLAN)
        p["work_packages"][0]["depends_on"] = ["WP-01"]
        with self.assertRaisesRegex(ValueError, "SELF_DEPENDENCY|DEPENDENCY_CYCLE"):
            queue.validate(p)
        p = copy.deepcopy(PLAN)
        p["work_packages"][1]["issue"] = p["work_packages"][0]["issue"]
        with self.assertRaisesRegex(ValueError, "DUPLICATE_ISSUE"):
            queue.validate(p)

    def test_rejects_unowned_issue_urls_and_extra_status_fields(self):
        p = copy.deepcopy(PLAN)
        p["work_packages"][0]["issue"] = "https://github.com/other/tool/issues/1"
        with self.assertRaisesRegex(ValueError, "REPO_MISMATCH"):
            queue.validate(p)
        p = copy.deepcopy(PLAN)
        p["work_packages"][0]["status"] = "DONE"
        with self.assertRaisesRegex(ValueError, "WORK_PACKAGE_SCHEMA_INVALID"):
            queue.validate(p)
        with self.assertRaisesRegex(ValueError, "ISSUE_URL_INVALID"):
            queue.issue_repo("file:///tmp/data.json")

    def test_observation_only_registered_issue_and_known_state(self):
        with self.assertRaisesRegex(ValueError, "OBSERVATION_UNKNOWN_ISSUE"):
            queue.triage(PLAN, {"issues": {"https://github.com/jaminliu89/prism/issues/9999": "closed"}})
        with self.assertRaisesRegex(ValueError, "OBSERVATIONS_SCHEMA_INVALID"):
            queue.triage(PLAN, {"receipts": {"status": "PASS"}})

    def test_cli_executes_without_network_and_does_not_claim_approval(self):
        c = subprocess.run([sys.executable, str(SCRIPT), "validate"],
                           capture_output=True, text=True, timeout=10)
        self.assertEqual(c.returncode, 0, c.stderr)
        self.assertEqual(json.loads(c.stdout)["status"], "PLAN_VALID_ONLY")
        r = subprocess.run([sys.executable, str(SCRIPT), "next"],
                           capture_output=True, text=True, timeout=10)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(json.loads(r.stdout)["release_authorized"])
        with tempfile.TemporaryDirectory() as directory:
            bad = Path(directory) / "bad.json"
            bad.write_text(json.dumps({"issues": {"x": "PASS"}}), encoding="utf-8")
            t = subprocess.run([sys.executable, str(SCRIPT), "--observations", str(bad), "next"],
                               capture_output=True, text=True, timeout=10)
            self.assertEqual(t.returncode, 2)
            self.assertEqual(json.loads(t.stderr)["status"], "NOT_READY")


if __name__ == "__main__":
    unittest.main()
