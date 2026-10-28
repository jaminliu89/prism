"""Offline synthetic fixtures. No external websites are executed."""
import hashlib, importlib.util, json, subprocess, sys, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];SCRIPT=ROOT/"scripts/web_evidence_router.py"
spec=importlib.util.spec_from_file_location("web_evidence_router",SCRIPT)
router=importlib.util.module_from_spec(spec);spec.loader.exec_module(router)
class RouterTests(unittest.TestCase):
    def test_document_and_fields_choose_different_engines(self):
        self.assertEqual(router.route("bulk_document_to_markdown",["scrapling","crawl4ai"])["selected"],"crawl4ai")
        self.assertEqual(router.route("stable_fields_prices_catalogs",["scrapling","crawl4ai"])["selected"],"scrapling")
    def test_no_fake_runtime_claim(self):
        row=router.route("stable_fields_prices_catalogs")
        self.assertEqual(row["status"],"NEEDS_RUNTIME_DISCOVERY")
        self.assertFalse(row["tool_execution_verified"])
        with self.assertRaises(ValueError): router.route("stable_fields_prices_catalogs",["unknown"])
    def test_failover_and_website_denial(self):
        self.assertEqual(router.fallback("stable_fields_prices_catalogs","scrapling",1,"schema_mismatch")["status"],"RETRY_SAME_METHOD")
        self.assertEqual(router.fallback("stable_fields_prices_catalogs","scrapling",2,"schema_mismatch")["candidate"],"crawl4ai")
        self.assertEqual(router.fallback("stable_fields_prices_catalogs","crawl4ai",2,"parse_error")["status"],"BLOCKED")
        for code in ("access_denied","robots_disallow","site_policy","unauthorized"):
            self.assertEqual(router.fallback("bulk_document_to_markdown","crawl4ai",2,code)["status"],"BLOCKED")
    def test_evidence_hash_wrong_path_symlink(self):
        with tempfile.TemporaryDirectory() as t, tempfile.TemporaryDirectory() as external:
            root=Path(t);(root/"data.json").write_text('{"fixture":true}')
            row={"task_id":"t1","target":"fixture://site","revision":"r1","case_id":"c1","tool":"scrapling",
                 "observed_at":"2026-10-28T00:00:00Z","evidence_path":"data.json",
                 "sha256":hashlib.sha256((root/"data.json").read_bytes()).hexdigest(),
                 "claim_level":"SOURCE","redactions":[],"next_condition":"review"}
            self.assertIn("STRUCTURAL",router.verify_record(row,root)["status"])
            row["sha256"]="0"*64
            with self.assertRaisesRegex(ValueError,"hash"):router.verify_record(row,root)
            row["evidence_path"]="../escape"
            with self.assertRaisesRegex(ValueError,"outside"):router.verify_record(row,root)
            row["evidence_path"]="link"
            (root/"link").symlink_to(Path(external)/"missing")
            with self.assertRaisesRegex(ValueError,"symlink"):router.verify_record(row,root)
    def test_cli(self):
        r=json.loads(subprocess.check_output([sys.executable,str(SCRIPT),"route","--intent","stable_fields_prices_catalogs"],text=True))
        self.assertEqual(r["candidates"],["scrapling","crawl4ai"])
if __name__=="__main__": unittest.main()
