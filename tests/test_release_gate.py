"""Contract checks for the release evidence gate; fixtures are synthetic, not a real release."""
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
spec = importlib.util.spec_from_file_location('release_gate', ROOT/'scripts/release_gate.py')
release_gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release_gate)

REAL = ROOT/'docs/verification/release-engineering/release-checklist.json'


class ReleaseGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.proof = self.base/'proof.txt'
        self.proof.write_text('synthetic fixture: observed command output, not a real release')
        self.digest = hashlib.sha256(self.proof.read_bytes()).hexdigest()
        self.manifest = {
            'schema_version': 1,
            'product': 'fixture-app',
            'version': '1.0.0',
            'platform': 'macos-arm64',
            'channel': 'release',
            'executor': 'fixture-builder',
            'signing': 'ad_hoc',
            'artifacts': [{'id': 'dmg', 'name': 'fixture-app-1.0.0.dmg', 'kind': 'dmg',
                           'sha256': 'a'*64, 'size': 1234, 'checksum_source': 'fixture release asset'}],
            'evidence': [{'id': 'E1', 'kind': 'command_output', 'source': 'observed',
                          'path': 'proof.txt', 'sha256': self.digest}],
            'gates': [{'id': gate, 'status': 'pass', 'artifact': 'dmg', 'evidence': ['E1']}
                      for gate in release_gate.GATE_IDS],
            'limitations': ['fixture only'],
        }
        self.path = self.base/'release.json'

    def check(self, data=None):
        self.path.write_text(json.dumps(data if data is not None else self.manifest, ensure_ascii=False), encoding='utf-8')
        return release_gate.check(self.path)

    def rejected(self, change):
        data = copy.deepcopy(self.manifest)
        change(data)
        with self.assertRaises(ValueError):
            self.check(data)

    def gate_of(self, data, gate_id):
        return next(item for item in data['gates'] if item['id'] == gate_id)

    # ---------- 正向 ----------

    def test_complete_manifest_is_ready_for_handoff(self):
        result = self.check()
        self.assertEqual(result['status'], 'READY_FOR_HANDOFF')
        self.assertEqual(result['gates'], len(release_gate.GATE_IDS))
        self.assertEqual(result['open_blockers'], 0)
        self.assertEqual(result['artifacts'], ['dmg'])

    def test_output_never_claims_authorization_or_runtime_proof(self):
        result = self.check()
        self.assertFalse(result['release_authorized'])
        self.assertEqual(result['runtime_verified'], 'NOT_BY_THIS_TOOL')
        self.assertEqual(result['semantic_authenticity'], 'NOT_VERIFIED')

    def test_template_covers_every_gate_and_is_structurally_valid(self):
        data = release_gate.template('fixture-app', '1.0.0', 'macos-arm64')
        self.assertEqual([g['id'] for g in data['gates']], list(release_gate.GATE_IDS))
        self.assertTrue(all(g['status'] == 'unknown' and g['reason'] for g in data['gates']))
        self.assertEqual(set(data), release_gate.TOP_FIELDS)
        self.assertEqual(self.check(data)['status'], 'BLOCKED')

    def test_real_video2text_checklist_is_ready(self):
        if not REAL.is_file():
            self.skipTest('real evidence record not present')
        result = release_gate.check(REAL)
        self.assertEqual(result['status'], 'READY_FOR_HANDOFF')
        self.assertEqual(result['product'], 'video-to-text')
        self.assertEqual(result['open_blockers'], 0)
        self.assertFalse(result['release_authorized'])

    # ---------- 反向：结构 ----------

    def test_unknown_top_field_rejected(self):
        self.rejected(lambda d: d.update({'approved_by': 'nobody'}))

    def test_unknown_schema_rejected(self):
        self.rejected(lambda d: d.update({'schema_version': 2}))

    def test_missing_gate_rejected(self):
        self.rejected(lambda d: d['gates'].pop())

    def test_unknown_gate_rejected(self):
        self.rejected(lambda d: d['gates'].append({'id': 'vibes_check', 'status': 'pass', 'evidence': ['E1']}))

    def test_duplicate_gate_rejected(self):
        self.rejected(lambda d: d['gates'].append(copy.deepcopy(d['gates'][0])))

    def test_unknown_channel_and_signing_rejected(self):
        self.rejected(lambda d: d.update({'channel': 'beta'}))
        self.rejected(lambda d: d.update({'signing': 'trust_me'}))

    def test_missing_identity_fields_rejected(self):
        self.rejected(lambda d: d.update({'executor': '   '}))
        self.rejected(lambda d: d.pop('version'))

    # ---------- 反向：证据 ----------

    def test_pass_without_evidence_rejected(self):
        self.rejected(lambda d: self.gate_of(d, 'cold_start').update({'evidence': []}))

    def test_pass_on_fixture_or_inferred_evidence_rejected(self):
        for source in ('fixture', 'inferred'):
            with self.subTest(source=source):
                def change(data, source=source):
                    data['evidence'][0]['source'] = source
                self.rejected(change)

    def test_evidence_hash_mismatch_rejected(self):
        self.rejected(lambda d: d['evidence'][0].update({'sha256': 'b'*64}))

    def test_duplicate_evidence_id_rejected(self):
        self.rejected(lambda d: d['evidence'].append(copy.deepcopy(d['evidence'][0])))

    def test_gate_referencing_unknown_evidence_rejected(self):
        self.rejected(lambda d: self.gate_of(d, 'log_capture').update({'evidence': ['E404']}))

    def test_absolute_and_escaping_evidence_paths_rejected(self):
        self.rejected(lambda d: d['evidence'][0].update({'path': '/etc/hosts'}))
        self.rejected(lambda d: d['evidence'][0].update({'path': '../proof.txt'}))

    def test_unknown_evidence_kind_or_source_rejected(self):
        self.rejected(lambda d: d['evidence'][0].update({'kind': 'vibes'}))
        self.rejected(lambda d: d['evidence'][0].update({'source': 'believed'}))

    # ---------- 反向：产物 ----------

    def test_artifact_name_must_carry_version(self):
        self.rejected(lambda d: d['artifacts'][0].update({'name': 'fixture-app-0.9.0.dmg'}))

    def test_artifact_name_must_be_a_file_name(self):
        self.rejected(lambda d: d['artifacts'][0].update({'name': 'dist/fixture-app-1.0.0.dmg'}))

    def test_artifact_hash_mismatch_rejected_when_local_copy_present(self):
        def change(data):
            data['artifacts'][0]['local_path'] = 'proof.txt'
        self.rejected(change)

    def test_artifact_without_local_copy_needs_checksum_source(self):
        self.rejected(lambda d: d['artifacts'][0].pop('checksum_source'))

    def test_artifact_size_must_be_positive_integer(self):
        self.rejected(lambda d: d['artifacts'][0].update({'size': 0}))
        self.rejected(lambda d: d['artifacts'][0].update({'size': '149MB'}))

    # ---------- 反向：门禁语义 ----------

    def test_non_pass_gate_needs_reason(self):
        def change(data):
            self.gate_of(data, 'cold_start').update({'status': 'blocked'})
        self.rejected(change)

    def test_blocking_statuses_count_as_open_blockers(self):
        data = copy.deepcopy(self.manifest)
        self.gate_of(data, 'process_hygiene').update({'status': 'fail', 'reason': '进程数 86'})
        result = self.check(data)
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertEqual(result['open_blockers'], 1)

    def test_not_applicable_needs_reason_but_does_not_block(self):
        data = copy.deepcopy(self.manifest)
        self.gate_of(data, 'process_hygiene').update({'status': 'not_applicable', 'reason': '静态库，无运行时进程'})
        result = self.check(data)
        self.assertEqual(result['status'], 'READY_FOR_HANDOFF')
        self.assertEqual(result['open_blockers'], 0)

    def test_unsigned_without_first_run_instruction_is_blocked(self):
        data = copy.deepcopy(self.manifest)
        data['signing'] = 'unsigned'
        self.gate_of(data, 'first_run_instruction').update({'status': 'unknown', 'reason': '还没写说明'})
        result = self.check(data)
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertEqual(result['signing_gate'], 'REQUIRES_FIRST_RUN_INSTRUCTION')
        self.assertEqual(result['open_blockers'], 2)  # 该门本身 + 签名缺口

    def test_signed_artifact_does_not_require_first_run_instruction(self):
        data = copy.deepcopy(self.manifest)
        data['signing'] = 'notarized'
        self.gate_of(data, 'first_run_instruction').update({'status': 'not_applicable', 'reason': '已公证，双击即可'})
        result = self.check(data)
        self.assertEqual(result['signing_gate'], 'OK')
        self.assertEqual(result['status'], 'READY_FOR_HANDOFF')

    # ---------- CLI ----------

    def test_cli_rejects_broken_manifest_with_exit_code(self):
        data = copy.deepcopy(self.manifest)
        data['evidence'][0]['sha256'] = 'c'*64
        self.path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        proc = subprocess.run([sys.executable, str(ROOT/'scripts/release_gate.py'), 'check', str(self.path)],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 1)
        self.assertIn('REJECTED', proc.stderr)
        self.assertIn('evidence hash mismatch', proc.stderr)

    def test_cli_prints_json_status(self):
        self.path.write_text(json.dumps(self.manifest, ensure_ascii=False), encoding='utf-8')
        proc = subprocess.run([sys.executable, str(ROOT/'scripts/release_gate.py'), 'check', str(self.path)],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(json.loads(proc.stdout)['status'], 'READY_FOR_HANDOFF')


if __name__ == '__main__':
    unittest.main()
