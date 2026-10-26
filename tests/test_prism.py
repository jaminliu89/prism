"""Isolated synthetic fixtures; these tests do not audit a real product."""
import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('prism', ROOT/'scripts/prism.py')
prism = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prism)


class PrismTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.proof = self.base/'proof.txt'
        self.proof.write_text('synthetic fixture: observed failure, not a real audit')
        self.report = {'schema_version': 1, 'delivery_claim': 'AUDIT_ONLY', 'target': 'synthetic fixture', 'revision': 'fixture-r1', 'scope': 'fixture case only', 'executor': 'fixture-builder',
                       'cases': [{'id': 'C1', 'requirement': 'REQ1 fixture requirement', 'status': 'fail', 'evidence': ['E1']}],
                       'evidence': [{'id': 'E1', 'path': 'proof.txt', 'sha256': hashlib.sha256(self.proof.read_bytes()).hexdigest(), 'revision': 'fixture-r1', 'source': 'observed'}],
                       'findings': [{'id': 'F1', 'severity': 'P1', 'status': 'open', 'case_id': 'C1', 'evidence': ['E1'], 'owner': 'fixture-builder', 'reproduction': 'fixture action', 'expected': 'fixture expected', 'actual': 'fixture failure', 'next_condition': 'fixture retest'}],
                       'review': {'status': 'not_performed'}}
        self.path = self.base/'audit.json'

    def verify(self, data=None):
        self.path.write_text(json.dumps(data or self.report))
        return prism.verify_report(self.path)

    def rejected(self, change):
        data = copy.deepcopy(self.report)
        change(data)
        with self.assertRaises(ValueError): self.verify(data)

    def test_failure_report_is_valid_but_not_release(self):
        result = self.verify()
        self.assertEqual(result['status'], 'STRUCTURALLY_VALID')
        self.assertEqual(result['open_blockers'], 1)
        self.assertFalse(result['release_authorized'])

    def test_product_pass_claim_rejected(self):
        self.rejected(lambda d: d.update(delivery_claim='PASS'))

    def test_hidden_product_pass_assertion_rejected(self):
        self.rejected(lambda d: d.update(product_verdict="PASS"))

    def test_report_root_must_be_object(self):
        self.path.write_text("[]")
        with self.assertRaisesRegex(ValueError, "object"): prism.verify_report(self.path)

    def test_release_claim_rejected(self):
        self.rejected(lambda d: d.update(delivery_claim='PRODUCTION_READY'))

    def test_tampered_evidence_rejected(self):
        self.proof.write_text('changed after capture')
        with self.assertRaisesRegex(ValueError, 'hash'): self.verify()

    def test_wrong_revision_rejected(self):
        self.rejected(lambda d: d['evidence'][0].update(revision='old-fixture'))

    def test_missing_evidence_rejected(self):
        self.rejected(lambda d: d['cases'][0].update(evidence=['MISSING']))

    def test_fixture_cannot_prove_observed_case(self):
        self.rejected(lambda d: d['evidence'][0].update(source='fixture'))

    def test_inference_cannot_prove_observed_case(self):
        self.rejected(lambda d: d['evidence'][0].update(source='inferred'))

    def test_absolute_path_rejected(self):
        self.rejected(lambda d: d['evidence'][0].update(path=str(self.proof)))

    def test_path_escape_rejected(self):
        self.rejected(lambda d: d['evidence'][0].update(path='../outside'))

    def test_symlink_escape_rejected(self):
        with tempfile.TemporaryDirectory() as other:
            outside = Path(other)/'outside.txt'
            outside.write_bytes(self.proof.read_bytes())
            (self.base/'link.txt').symlink_to(outside)
            self.rejected(lambda d: d['evidence'][0].update(path='link.txt'))

    def test_duplicate_ids_rejected(self):
        self.rejected(lambda d: d['evidence'].append(d['evidence'][0]))

    def test_self_review_rejected(self):
        self.rejected(lambda d: d.update(review={'status': 'independent_review', 'principal': ' FIXTURE-BUILDER ', 'evidence': ['E1']}))

    def test_independent_review_requires_evidence(self):
        self.rejected(lambda d: d.update(review={'status': 'independent_review', 'principal': 'fixture-reviewer', 'evidence': []}))

    def test_unknown_and_na_need_reasons(self):
        for status in ('unknown', 'blocked', 'not_applicable'):
            with self.subTest(status=status):
                self.rejected(lambda d: d['cases'][0].update(status=status))

    def test_unknown_counts_as_incomplete(self):
        self.report['cases'][0].update(status='unknown', reason='fixture inaccessible')
        self.report['findings'] = []
        self.assertEqual(self.verify()['incomplete_cases'], 1)

    def test_resolved_finding_requires_retest(self):
        self.rejected(lambda d: d['findings'][0].update(status='resolved'))

    def test_no_cases_rejected(self):
        self.rejected(lambda d: d.update(cases=[]))

    def test_dangling_finding_rejected(self):
        self.rejected(lambda d: d['findings'][0].update(case_id='C2'))

    def test_real_snapshots_verified(self):
        self.assertEqual(prism.doctor()['assets'], 6)

    def test_corrupted_snapshot_rejected(self):
        (self.base/'source.md').write_text('corrupt')
        (self.base/'UPSTREAM.lock.json').write_text(json.dumps({'schema_version': 1, 'assets': [{'id': 'fixture', 'commit': 'a'*40, 'path': 'source.md', 'sha256': '0'*64}]}))
        with self.assertRaisesRegex(ValueError, 'hash'): prism.doctor(self.base)

    def test_all_software_targets_use_existing_methods_without_execution(self):
        for kind in ('web', 'app', 'desktop', 'api', 'cli', 'service'):
            with self.subTest(kind=kind):
                result = prism.plan('audit', kind, 'fixture://target', 'r1')
                self.assertIn('sources/skillhub/checklist/final-checklist.md', result['read'])
                self.assertFalse(result['target_executed'])
                self.assertFalse(result['release_authorized'])

    def test_other_product_does_not_force_software_checklist(self):
        self.assertNotIn('sources/skillhub/checklist/final-checklist.md', prism.plan('audit', 'other', 'fixture service')['read'])
        with self.assertRaises(ValueError): prism.plan('clone', 'other', 'fixture')

    def test_planning_preserves_stage_zero_confirmation(self):
        result = prism.plan('planning', 'web', 'fixture idea')
        self.assertEqual(result['primary_in_group'], 'idea-to-blueprint')
        self.assertIn('stage 0', result['next'])
        self.assertIn('wait for confirmation', result['next'])

    def test_audit_and_clone_point_to_actual_site_clone_repository(self):
        for mode in ('audit', 'clone', 'release'):
            with self.subTest(mode=mode):
                direct = prism.plan(mode, 'web', 'fixture')['external_read']
                self.assertEqual(len(direct), 1)
                self.assertEqual(direct[0]['repository'], 'jaminliu89/site-reverse-clone')
                prefix = 'https://github.com/jaminliu89/site-reverse-clone/blob/' + direct[0]['commit'] + '/'
                self.assertEqual(direct[0]['method'], prefix + 'skills/site-reverse-clone/SKILL.md')
                self.assertEqual(direct[0]['orchestration'], prefix + 'ORCHESTRATION.md')
                self.assertEqual(direct[0]['capture_engine'], prefix + 'skills/web-clone/SKILL.md')
                self.assertEqual(direct[0]['project_audit'], prefix + 'skills/site-reverse-clone/references/project-audit.md')

    def test_missing_project_audit_path_is_rejected(self):
        lock = json.loads((ROOT/'UPSTREAM.lock.json').read_text())
        for asset in lock['assets']:
            path = self.base/asset['path']
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((ROOT/asset['path']).read_bytes())
        for value in (None, ''):
            with self.subTest(value=value):
                changed = copy.deepcopy(lock)
                if value is None: changed['external_methods'][0].pop('project_audit_path')
                else: changed['external_methods'][0]['project_audit_path'] = value
                (self.base/'UPSTREAM.lock.json').write_text(json.dumps(changed))
                with self.assertRaisesRegex(ValueError, 'project_audit_path'): prism.doctor(self.base)

    def test_project_audit_plan_exposes_full_scope_without_execution(self):
        result = prism.plan('audit', 'api', 'fixture')
        self.assertEqual(result['external_read'][0]['repository'], 'jaminliu89/site-reverse-clone')
        self.assertTrue({'project_completeness', 'security', 'personnel_agent_collaboration', 'orchestration'}.issubset(result['audit_scope']))
        self.assertFalse(result['target_executed'])
        self.assertFalse(result['release_authorized'])

    def test_planning_and_nonsoftware_do_not_load_site_clone(self):
        self.assertEqual(prism.plan('planning', 'web', 'fixture')['external_read'], [])
        self.assertEqual(prism.plan('audit', 'other', 'fixture')['external_read'], [])

    def test_release_keeps_original_owner(self):
        result = prism.plan('release', 'web', 'fixture')
        self.assertEqual(result['primary_in_group'], 'delivery-walkthrough')
        self.assertFalse(result['release_authorized'])

    def test_cli_rejects_missing_or_invalid_inputs(self):
        for args in (['plan', '--kind', 'web'], ['plan', '--kind', 'web', '--target', 'x', '--mode', 'deploy']):
            r = subprocess.run([sys.executable, str(ROOT/'scripts/prism.py'), *args], cwd=self.base, capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0)

    def test_cli_works_outside_checkout(self):
        r = subprocess.run([sys.executable, str(ROOT/'scripts/prism.py'), 'plan', '--kind', 'api', '--target', 'fixture://api'], cwd=self.base, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)['status'], 'PLAN_ONLY')


if __name__ == '__main__': unittest.main()
