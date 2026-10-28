"""Real local subprocesses and synthetic targets; no model, remote target or deployment."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('mission', ROOT/'scripts/mission.py')
mission = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mission)


class MissionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)/'project'
        self.root.mkdir()
        self.spec = {'profile': 'dev', 'goal': 'Create and retrieve an order across processes',
                     'target': 'synthetic local order service', 'principal': 'fixture-host',
                     'scope': 'local temporary project only; no network or paid services',
                     'acceptance': ['Order persists and is readable after process restart'],
                     'components': [{'path': 'backend', 'purpose': 'order persistence', 'source': 'proposed'}],
                     'implementation_authorized': True,
                     'authorization_statement': 'test author permits this local subprocess fixture'}

    def initialize(self):
        return mission.initialize(self.root, self.spec)

    def execute(self, code='print("fixture")'):
        return mission.execute(self.root, [sys.executable, '-c', code], 'fixture-builder', True, 3)

    def report(self, run):
        path = next(p for p in run['logs'] if p.endswith('stdout.log'))
        return {'run_id': run['run_id'], 'snapshot_id': run['snapshot_id'], 'reviewer': 'fixture-reviewer',
                'cases': [{'requirement': self.spec['acceptance'][0], 'status': 'pass',
                           'reason': 'synthetic observed output inspected',
                           'evidence': [{'path': path, 'sha256': run['logs'][path]}]}]}

    def test_profiles_and_scaffold_not_claimed_recovered(self):
        for profile in mission.PROFILES:
            with self.subTest(profile=profile):
                project = self.root/profile
                project.mkdir()
                spec = dict(self.spec, profile=profile, competition_rules='local fixture only',
                            submission_rules='local demo artifact, no remote submission')
                result = mission.initialize(project, spec)
                self.assertEqual(result['implementation'], 'NOT_STARTED')
                self.assertEqual(result['deployment'], 'NOT_DEPLOYED')
                self.assertTrue((project/'backend/PRISM-COMPONENT.md').is_file())
                backend = (project/'docs/prism-mission/BACKEND.md').read_text()
                self.assertTrue(all(x in backend for x in mission.BACKEND))
                self.assertFalse(mission.load(project)['release_authorized'])

    def test_missing_target_does_not_execute(self):
        self.spec['target'] = ''
        self.assertEqual(self.initialize()['status'], 'TARGET_REQUIRED')
        self.assertEqual(mission.next_action(self.root)['status'], 'TARGET_REQUIRED')
        with self.assertRaisesRegex(ValueError, 'target'):
            self.execute()

    def test_ctf_and_hackathon_rules_required(self):
        for profile in ('ctf', 'hackathon'):
            self.spec['profile'] = profile
            with self.assertRaises(ValueError):
                self.initialize()
        self.assertFalse(mission.state_path(self.root).exists())

    def test_refuses_escape_symlink_and_existing_artifacts(self):
        self.spec['components'][0]['path'] = '../outside'
        with self.assertRaises(ValueError): self.initialize()
        self.spec['components'][0]['path'] = 'link/code'
        (self.root/'link').symlink_to(self.root.parent, target_is_directory=True)
        with self.assertRaises(ValueError): self.initialize()
        self.spec['components'][0]['path'] = 'backend'
        self.initialize()
        state = mission.state_path(self.root).read_bytes()
        with self.assertRaises(ValueError): self.initialize()
        self.assertEqual(mission.state_path(self.root).read_bytes(), state)

    def test_consent_and_task_authorization_both_required(self):
        self.spec['implementation_authorized'] = False
        self.initialize()
        with self.assertRaises(ValueError): self.execute()
        with self.assertRaises(ValueError):
            mission.execute(self.root, [sys.executable, '-c', 'print(1)'], 'host', False)
        self.assertEqual(mission.load(self.root)['runs'], [])

    def test_real_sqlite_input_output_and_restart(self):
        self.initialize()
        program = self.root/'backend/orders.py'
        program.write_text('''import json, sqlite3, sys
db=sqlite3.connect('backend/orders.sqlite')
db.execute('create table if not exists orders (id text primary key, item text)')
if sys.argv[1]=='create':
    db.execute('insert into orders values (?,?)', ('O1','tea'))
    db.commit()
print(json.dumps(db.execute('select * from orders').fetchall()))
db.close()
''')
        for action in ('create', 'read'):
            run = mission.execute(self.root, [sys.executable, str(program), action], 'fixture-builder', True, 3)
            self.assertEqual(run['status'], 'EXITED')
        stdout = next(self.root/p for p in run['logs'] if p.endswith('stdout.log'))
        self.assertEqual(json.loads(stdout.read_text()), [['O1', 'tea']])
        self.assertEqual(run['semantic_acceptance'], 'NOT_REVIEWED')
        record = mission.review(self.root, self.report(run))
        self.assertFalse(record['identity_verified'])
        self.assertFalse(record['release_authorized'])

    def test_failure_timeout_and_unsettled_recovery(self):
        self.initialize()
        self.assertEqual(self.execute('raise RuntimeError("expected fixture failure")')['status'], 'FAILED')
        run = mission.execute(self.root, [sys.executable, '-c', 'import time;time.sleep(3)'], 'host', True, 1)
        self.assertEqual(run['status'], 'TIMEOUT')
        state = mission.load(self.root)
        state['runs'].append({'status': 'RUNNING', 'id': 'unknown-after-fixture-crash'})
        mission.write_json(mission.state_path(self.root), state)
        self.assertEqual(mission.next_action(self.root)['status'], 'RUNNING_OR_RECOVERY_REQUIRED')
        with self.assertRaisesRegex(ValueError, 'reconciliation'): self.execute()

    def test_no_self_review_stale_code_or_changed_logs(self):
        self.initialize()
        run = self.execute()
        report = self.report(run)
        bad = copy.deepcopy(report); bad['reviewer'] = 'fixture-builder'
        with self.assertRaisesRegex(ValueError, 'self'): mission.review(self.root, bad)
        (self.root/'change.txt').write_text('new code revision')
        with self.assertRaisesRegex(ValueError, 'stale'): mission.review(self.root, report)
        new_run = self.execute()
        report = self.report(new_run)
        log = next(self.root/p for p in new_run['logs'] if p.endswith('stdout.log'))
        log.write_text('altered fixture output')
        with self.assertRaisesRegex(ValueError, 'log changed'): mission.review(self.root, report)

    def test_review_binds_contract_and_registered_run_evidence(self):
        self.initialize()
        run = self.execute()
        report = self.report(run)
        unrelated = self.root/'.prism/unrelated.txt'
        unrelated.write_text('not observed in the run')
        forged = copy.deepcopy(report)
        forged['cases'][0]['evidence'] = [{'path': '.prism/unrelated.txt',
                                         'sha256': mission.digest(unrelated.read_bytes())}]
        with self.assertRaisesRegex(ValueError, 'not registered'):
            mission.review(self.root, forged)
        state = mission.load(self.root)
        state['spec']['acceptance'] = ['weaker replacement condition']
        mission.write_json(mission.state_path(self.root), state)
        report['cases'][0]['requirement'] = state['spec']['acceptance'][0]
        with self.assertRaisesRegex(ValueError, 'contract changed'):
            mission.review(self.root, report)

    def test_snapshot_failure_blocks_retry_until_explicit_reconciliation(self):
        self.initialize()
        with self.assertRaisesRegex(ValueError, 'snapshot budget'):
            self.execute("from pathlib import Path;Path('large').write_bytes(b'x'*(21*1024*1024))")
        state = mission.load(self.root)
        self.assertEqual(state['runs'][-1]['status'], 'RECOVERY_REQUIRED')
        # Fixture-generated file is removed only by this test's explicit cleanup.
        (self.root/'large').unlink()
        self.assertEqual(mission.next_action(self.root)['status'], 'RUNNING_OR_RECOVERY_REQUIRED')
        with self.assertRaisesRegex(ValueError, 'reconciliation'): self.execute()
        with self.assertRaises(ValueError):
            mission.reconcile(self.root, state['runs'][-1]['id'], 'host', 'fixture inspected', False)
        result = mission.reconcile(self.root, state['runs'][-1]['id'], 'host', 'fixture process ended and partial changes inspected', True)
        self.assertEqual(result['status'], 'FAILED_RECONCILED')
        self.assertEqual(self.execute()['status'], 'EXITED')

    def test_non_regular_snapshot_does_not_block_on_fifo(self):
        self.initialize()
        os.mkfifo(self.root/'pipe')
        with self.assertRaisesRegex(ValueError, 'non-regular'):
            self.execute()
        self.assertEqual(mission.load(self.root)['runs'], [])

    def test_unreadable_directory_cannot_be_silently_omitted(self):
        self.initialize()
        folder = self.root/'backend'
        (folder/'code.py').write_text('print("fixture")')
        folder.chmod(0)
        try:
            if os.access(folder, os.R_OK | os.X_OK):
                self.skipTest('current user bypasses fixture filesystem permissions')
            with self.assertRaises(PermissionError):
                mission.snapshot(self.root)
        finally:
            folder.chmod(0o700)

    def test_ancestor_conflict_is_rejected_before_publishing(self):
        (self.root/'backend').write_text('existing user file')
        with self.assertRaisesRegex(ValueError, 'ancestor'):
            self.initialize()
        self.assertFalse((self.root/'docs/prism-mission/GOAL.md').exists())
        self.assertEqual((self.root/'backend').read_text(), 'existing user file')

    def test_amend_missing_target_and_contract_change(self):
        self.spec['target'] = ''
        self.initialize()
        changed = dict(self.spec, target='actual local fixture target')
        amended = mission.amend(self.root, changed, 'fixture-host', 'target now supplied')
        self.assertEqual(amended['status'], 'DISCOVERING')
        self.assertEqual(mission.next_action(self.root)['status'], 'HOST_DEV_REQUIRED')
        run = self.execute()
        report = self.report(run)
        changed['scope'] = 'new explicitly amended scope'
        mission.amend(self.root, changed, 'fixture-host', 'test changed scope')
        with self.assertRaisesRegex(ValueError, 'contract changed'):
            mission.review(self.root, report)

    def test_cli_rejects_missing_optin_and_returns_exact_output_evidence(self):
        self.initialize()
        base = [sys.executable, str(ROOT/'scripts/mission.py'), '--project', str(self.root)]
        denied = subprocess.run(base+['run', '--actor', 'host', '--', sys.executable, '-c', 'print(7)'], capture_output=True)
        self.assertNotEqual(denied.returncode, 0)
        result = subprocess.run(base+['run', '--actor', 'host', '--allow-local-execution', '--', sys.executable, '-c', 'print(7)'], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        packet = json.loads(result.stdout)
        log = next(self.root/p for p in packet['logs'] if p.endswith('stdout.log'))
        self.assertEqual(log.read_text().strip(), '7')
        self.assertEqual(hashlib.sha256(log.read_bytes()).hexdigest(), packet['logs'][str(log.relative_to(self.root))])


if __name__ == '__main__':
    unittest.main()
