"""Real HTTP adapter checks over isolated synthetic projects."""
import http.client
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from http.server import HTTPServer
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import foundry_web as web
import foundry as f


class WorkbenchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.app = web.Workbench(self.temp.name)
        self.server = HTTPServer(('127.0.0.1', 0), web.handler_for(self.app, 0, 'test-token'))
        self.port = self.server.server_port
        self.server.RequestHandlerClass = web.handler_for(self.app, self.port, 'test-token')
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join()
        self.temp.cleanup()

    def call(self, path, body=None, headers=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.port)
        base = {'Content-Type': 'application/json', 'X-Foundry-Token': 'test-token'}
        base.update(headers or {})
        conn.request('POST' if body is not None else 'GET', path,
                     json.dumps(body) if body is not None else None, base)
        response = conn.getresponse()
        data = json.loads(response.read())
        code = response.status; conn.close()
        return code, data

    def create(self):
        code, value = self.call('/api/projects', {'idea': '合成验收项目', 'actor': 'tester'})
        self.assertEqual(code, 201)
        return value

    def test_real_create_write_review_and_confirmation_gate(self):
        data = self.create(); path = '/api/projects/' + data['id'] + '/actions'
        def action(**values):
            nonlocal data
            code, result = self.call(path, {**values, 'actor': 'tester', 'revision': data['status']['revision']})
            if code == 200: data = result
            return code, result
        self.assertEqual(action(action='confirm', statement='不能越过门禁')[0], 400)
        for key in ('audience', 'problem', 'success'):
            self.assertEqual(action(action='answer', key=key, value='真实保存的合成答案')[0], 200)
        self.assertEqual(data['answers']['problem'], '真实保存的合成答案')
        self.assertEqual(action(action='submit', path='docs/00-asset-recall.md', content='# 来源\n\n这是合成验收资料。')[0], 200)
        self.assertEqual(action(action='review', verdict='pass', note='仅合成流程自检')[0], 200)
        self.assertEqual(action(action='confirm', statement='确认阶段0合成验收文档')[0], 200)
        self.assertEqual(data['status']['current_stage'], 1)
        persisted = f.load(self.app.root(data['id']))
        self.assertFalse(persisted['stages'][0]['confirmation']['identity_verified'])
        self.assertEqual(f.status(self.app.root(data['id']))['agent_execution'], 'NOT_STARTED')
        self.assertFalse(data['status'].get('release_authorized', False))

    def test_reject_stale_write_and_arbitrary_document(self):
        data = self.create(); base = '/api/projects/' + data['id']
        body = {'action':'answer', 'key':'audience', 'value':'测试', 'actor':'tester', 'revision':1}
        self.assertEqual(self.call(base+'/actions', body)[0], 200)
        self.assertEqual(self.call(base+'/actions', body)[0], 409)
        self.assertEqual(self.call(base+'/document?path=.foundry/project.json')[0], 400)
        self.assertEqual(self.call(base+'/actions', {**body, 'revision':2, 'action':'handoff'})[0], 400)
        self.assertRaises(ValueError, self.app.root, '../../outside')

    def test_host_origin_token_and_body_controls(self):
        self.assertEqual(self.call('/api/projects', {}, {'Host':'evil.example'})[0], 403)
        self.assertEqual(self.call('/api/projects', {}, {'Origin':'https://evil.example'})[0], 403)
        self.assertEqual(self.call('/api/projects', {}, {'X-Foundry-Token':'wrong'})[0], 403)
        self.assertEqual(self.call('/api/projects', ['not-object'])[0], 400)
        self.assertEqual(self.call('/api/projects', {'idea':'', 'actor':'tester'})[0], 400)
        self.assertEqual(self.call('/api/projects', {'idea':'x'*web.MAX_BODY, 'actor':'tester'})[0], 413)
        self.assertEqual(self.call('/api/sources')[0], 200)
        self.assertEqual(self.call('/api/session')[1]['token'], 'test-token')


    def test_document_read_exposes_external_modification(self):
        data = self.create(); project_id = data['id']
        root = self.app.root(project_id)
        path = 'docs/00-idea-brief.md'
        code, before = self.call('/api/projects/'+project_id+'/document?path='+path)
        self.assertEqual(code, 200); self.assertTrue(before['valid'])
        (root / path).write_text('# External change', encoding='utf-8')
        code, after = self.call('/api/projects/'+project_id+'/document?path='+path)
        self.assertFalse(after['valid'])
        self.assertNotEqual(before['sha256'], after['sha256'])
        self.assertFalse(self.app.snapshot(project_id)['artifact_validity'][path])
        invalid = {'action':'answer','key':'problem','value':{},'actor':'tester','revision':1}
        self.assertEqual(self.call('/api/projects/'+project_id+'/actions',invalid)[0],400)

    def test_panel_cannot_resolve_without_dissent(self):
        data = self.create(); base = '/api/projects/' + data['id'] + '/actions'
        def action(**values):
            nonlocal data
            code, result = self.call(base, {**values, 'actor':'tester', 'revision':data['status']['revision']})
            if code == 200: data = result
            return code
        self.assertEqual(action(action='panel-open',question='是否扩张范围？'),200)
        self.assertEqual(action(action='panel-resolve',id='PNL-0001',outcome='adopt',rationale='无意见不能裁决'),400)
        self.assertEqual(action(action='panel-opinion',id='PNL-0001',role='challenger',verdict='oppose',severity='high',reasoning='未验证需求',evidence='尚无研究',counterexample='有需求证据则重新考虑'),200)
        self.assertEqual(action(action='panel-resolve',id='PNL-0001',outcome='defer',rationale='保留范围'),200)


if __name__ == '__main__': unittest.main()
