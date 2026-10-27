#!/usr/bin/env python3
"""Loopback-only Foundry adapter. Existing foundry.py remains the state authority."""
import argparse
import json
import mimetypes
import re
import secrets
import tempfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
import foundry as f

REPO = Path(__file__).resolve().parents[1]
MAX_BODY = 262144


class Workbench:
    def __init__(self, workspace, project=None):
        self.workspace = Path(workspace).resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.mounted = Path(project).resolve() if project else None

    def root(self, project_id):
        if project_id == 'mounted' and self.mounted:
            return self.mounted
        if not re.fullmatch(r'[a-f0-9]{16}', project_id):
            raise ValueError('unknown project')
        root = self.workspace / project_id
        if root.is_symlink() or root.resolve().parent != self.workspace:
            raise ValueError('project escapes workspace')
        return root

    def projects(self):
        ids = [p.name for p in self.workspace.iterdir()
               if re.fullmatch(r'[a-f0-9]{16}', p.name) and not p.is_symlink()]
        if self.mounted:
            ids.insert(0, 'mounted')
        result = []
        for id_ in ids:
            root = self.root(id_)
            if (root / '.foundry/project.json').is_file():
                data = f.load(root)
                result.append({'id': id_, 'idea': data['idea_original'],
                               'stage': f.current(data), 'revision': data['revision']})
        return result

    def snapshot(self, project_id):
        root = self.root(project_id)
        data = f.load(root)
        return {'id': project_id, 'status': f.status(root, data),
                'answers': {key: value['value'] for key, value in data['answers'].items()},
                'stages': data['stages'],
                'artifact_validity': {p: f.verified_artifact(root, data['stages'][i], p)
                                      for i, paths in f.DOCS.items() for p in paths},
                'topics': data.get('panel_topics', []), 'changes': data['changes'],
                'documents': {str(k): list(v) for k, v in f.DOCS.items()},
                'next': f.next_step(root, data), 'tasks': data.get('tasks', [])}

    def document(self, project_id, path):
        if path not in {p for paths in f.DOCS.values() for p in paths}:
            raise ValueError('document is not in the planning contract')
        root = self.root(project_id)
        file = f.file_under(root, path)
        content = file.read_bytes() if file.is_file() else b''
        data = f.load(root)
        stage = next(i for i, paths in f.DOCS.items() if path in paths)
        return {'path': path, 'content': content.decode('utf-8'),
                'sha256': f.digest(content) if content else None,
                'valid': f.verified_artifact(root, data['stages'][stage], path)}

    def action(self, project_id, body):
        if any(not isinstance(v, str) for k, v in body.items() if k != 'revision'):
            raise ValueError('action fields must be text')
        root = self.root(project_id)
        revision = body.get('revision')
        if type(revision) is not int:
            raise ValueError('revision is required; refresh project')
        actor = body.get('actor', '')
        if not isinstance(actor, str) or not actor.strip():
            raise ValueError('记录人不能为空')
        action = body.get('action')
        f.check_rev(f.load(root), revision)
        if action == 'answer':
            f.answer(root, body['key'], body['value'], actor, revision)
        elif action == 'submit':
            with tempfile.NamedTemporaryFile() as source:
                source.write(body['content'].encode()); source.flush()
                f.submit(root, body['path'], source.name, actor, revision)
        elif action == 'review':
            f.review(root, body['verdict'], 'self_check', actor, body['note'], revision)
        elif action == 'confirm':
            f.confirm(root, actor, body['statement'], revision)
        elif action == 'panel-open':
            f.panel_open(root, body['question'], actor, revision)
        elif action == 'panel-opinion':
            f.panel_opinion(root, body['id'], body['role'], actor, body['verdict'],
                            body['severity'], body['reasoning'], body['evidence'],
                            body['counterexample'], revision)
        elif action == 'panel-resolve':
            f.panel_resolve(root, body['id'], body['outcome'], actor, body['rationale'], revision)
        else:
            raise ValueError('unsupported workbench action')
        return self.snapshot(project_id)


def handler_for(app, port, token):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass  # Do not log project content or session tokens.

        def respond(self, code, value):
            blob = json.dumps(value, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(blob)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers(); self.wfile.write(blob)

        def allowed(self, write=False):
            expected = f'127.0.0.1:{port}'
            if self.headers.get('Host') != expected:
                self.respond(403, {'error': 'invalid local host'}); return False
            origin = self.headers.get('Origin')
            if origin and origin != f'http://{expected}':
                self.respond(403, {'error': 'cross-origin request denied'}); return False
            if write and self.headers.get('X-Foundry-Token') != token:
                self.respond(403, {'error': 'session expired; reload workbench'}); return False
            return True

        def do_GET(self):
            if not self.allowed(): return
            url = urlsplit(self.path)
            parts = url.path.strip('/').split('/')
            try:
                if url.path == '/api/session':
                    return self.respond(200, {'token': token})
                if url.path == '/api/sources':
                    return self.respond(200, json.loads((REPO / 'UPSTREAM.lock.json').read_text()))
                if url.path == '/api/projects':
                    return self.respond(200, app.projects())
                if len(parts) == 3 and parts[:2] == ['api', 'projects']:
                    return self.respond(200, app.snapshot(parts[2]))
                if len(parts) == 4 and parts[:2] == ['api', 'projects'] and parts[3] == 'document':
                    return self.respond(200, app.document(parts[2], parse_qs(url.query)['path'][0]))
                if url.path.startswith('/api/'):
                    return self.respond(404, {'error': 'unknown endpoint'})
                dist = REPO / 'web/dist'
                relative = url.path.lstrip('/') or 'index.html'
                file = (dist / relative).resolve()
                if not file.is_relative_to(dist.resolve()) or not file.is_file():
                    return self.respond(404, {'error': '先运行 npm run build --prefix web'})
                blob = file.read_bytes()
                self.send_response(200)
                self.send_header('Content-Type', mimetypes.guess_type(file.name)[0] or 'application/octet-stream')
                self.send_header('Content-Length', str(len(blob)))
                self.send_header('X-Content-Type-Options', 'nosniff')
                self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
                self.end_headers(); self.wfile.write(blob)
            except (ValueError, KeyError, OSError) as error:
                self.respond(400, {'error': str(error)})

        def do_POST(self):
            if not self.allowed(write=True): return
            try:
                size = int(self.headers.get('Content-Length', 0))
                if size < 1 or size > MAX_BODY:
                    return self.respond(413, {'error': 'content must be 1–262144 bytes'})
                if self.headers.get('Content-Type') != 'application/json':
                    return self.respond(415, {'error': 'JSON required'})
                body = json.loads(self.rfile.read(size))
                if not isinstance(body, dict): raise ValueError('JSON object required')
                if self.path == '/api/projects':
                    idea, actor = body['idea'], body['actor']
                    if not all(isinstance(v, str) and v.strip() for v in (idea, actor)):
                        raise ValueError('点子和记录人不能为空')
                    id_ = secrets.token_hex(8)
                    f.init(app.root(id_), idea, actor)
                    return self.respond(201, app.snapshot(id_))
                parts = self.path.strip('/').split('/')
                if len(parts) == 4 and parts[:2] == ['api', 'projects'] and parts[3] == 'actions':
                    return self.respond(200, app.action(parts[2], body))
                self.respond(404, {'error': 'unknown endpoint'})
            except (ValueError, KeyError, TypeError, OSError) as error:
                self.respond(409 if 'stale project revision' in str(error) else 400,
                             {'error': str(error)})
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True, type=Path)
    parser.add_argument('--project', type=Path, help='explicitly mount one existing CLI project')
    parser.add_argument('--port', default=8765, type=int)
    args = parser.parse_args()
    app = Workbench(args.workspace, args.project)
    server = HTTPServer(('127.0.0.1', args.port), handler_for(app, args.port, secrets.token_urlsafe(32)))
    print(f'Foundry: http://127.0.0.1:{args.port} (local identity claims only)', flush=True)
    server.serve_forever()


if __name__ == '__main__':
    main()
