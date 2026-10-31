#!/usr/bin/env python3
"""Release evidence gate: validates a release checklist's structure and evidence links.

Never builds, signs, mounts or publishes anything. A READY_FOR_HANDOFF result means the
evidence is complete and self-consistent, not that the artifact works or may be released.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TOP_FIELDS = {
    'schema_version', 'product', 'version', 'platform', 'channel', 'executor',
    'signing', 'artifacts', 'evidence', 'gates', 'limitations',
}
CHANNELS = ('release', 'preview')
SIGNINGS = ('notarized', 'developer_id', 'ad_hoc', 'unsigned')
ARTIFACT_KINDS = ('dmg', 'pkg', 'app', 'zip', 'tar', 'exe', 'appimage', 'deb')
EVIDENCE_KINDS = ('command_output', 'log', 'screenshot', 'release_asset', 'note')
EVIDENCE_SOURCES = ('observed', 'fixture', 'inferred')
GATE_IDS = (
    'artifact_integrity', 'install_path', 'cold_start', 'self_contained_runtime',
    'code_signing', 'log_capture', 'process_hygiene', 'ci_exercises_shipping_path',
    'version_consistency', 'first_run_instruction',
)
GATE_STATUS = ('pass', 'fail', 'blocked', 'unknown', 'not_applicable')
BLOCKING = ('fail', 'blocked', 'unknown')
UNSIGNED = ('ad_hoc', 'unsigned')


def need(condition, message):
    if not condition:
        raise ValueError(message)


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def local_file(base, name, label):
    need(nonempty(name), 'missing %s path' % label)
    relative = Path(name)
    need(not relative.is_absolute(), 'absolute %s path rejected' % label)
    path = (base / relative).resolve()
    need(path.is_relative_to(base.resolve()), '%s path escapes checklist directory' % label)
    need(path.is_file(), 'missing %s file: %s' % (label, name))
    return path


def _artifacts(data, base):
    items = data.get('artifacts')
    need(isinstance(items, list) and len(items) > 0, 'artifacts must be a non-empty list')
    seen = set()
    out = []
    for item in items:
        need(isinstance(item, dict), 'invalid artifact entry')
        for key in ('id', 'name', 'kind', 'sha256'):
            need(nonempty(item.get(key)), 'artifact missing ' + key)
        need(item['id'] not in seen, 'duplicate artifact id: ' + item['id'])
        seen.add(item['id'])
        need('/' not in item['name'] and '\\' not in item['name'], 'artifact name must be a file name: ' + item['name'])
        need(item['kind'] in ARTIFACT_KINDS, 'unknown artifact kind: %s' % item['kind'])
        need(re.fullmatch(r'[0-9a-f]{64}', item['sha256']) is not None, 'artifact sha256 must be 64 lowercase hex')
        need(isinstance(item.get('size'), int) and item['size'] > 0, 'artifact size must be a positive integer')
        need(data['version'] in item['name'], 'artifact name must contain version %s: %s' % (data['version'], item['name']))
        local = item.get('local_path')
        if local is None:
            need(nonempty(item.get('checksum_source')), 'artifact %s declares no local_path, so checksum_source is required' % item['id'])
        else:
            path = local_file(base, local, 'artifact')
            need(hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256'], 'artifact hash mismatch: ' + item['id'])
            need(path.stat().st_size == item['size'], 'artifact size mismatch: ' + item['id'])
        out.append(item['id'])
    return out


def _evidence(data, base):
    items = data.get('evidence')
    need(isinstance(items, list), 'evidence must be a list')
    refs = {}
    for item in items:
        need(isinstance(item, dict) and nonempty(item.get('id')), 'invalid evidence entry')
        need(item['id'] not in refs, 'duplicate evidence id: ' + item['id'])
        need(item.get('kind') in EVIDENCE_KINDS, 'unknown evidence kind: %s' % item.get('kind'))
        need(item.get('source') in EVIDENCE_SOURCES, 'unknown evidence source: %s' % item.get('source'))
        path = local_file(base, item.get('path'), 'evidence')
        need(hashlib.sha256(path.read_bytes()).hexdigest() == item.get('sha256'), 'evidence hash mismatch: ' + item['id'])
        refs[item['id']] = item
    return refs


def _gates(data, refs, artifacts):
    items = data.get('gates')
    need(isinstance(items, list), 'gates must be a list')
    seen = set()
    blockers = 0
    for item in items:
        need(isinstance(item, dict) and nonempty(item.get('id')), 'invalid gate entry')
        gate_id = item['id']
        need(gate_id in GATE_IDS, 'unknown gate: ' + gate_id)
        need(gate_id not in seen, 'duplicate gate: ' + gate_id)
        seen.add(gate_id)
        status = item.get('status')
        need(status in GATE_STATUS, 'invalid gate status: %s' % status)
        refs_used = item.get('evidence', [])
        need(isinstance(refs_used, list), 'gate evidence must be a list: ' + gate_id)
        need(all(isinstance(i, str) and i in refs for i in refs_used), 'gate references unknown evidence: ' + gate_id)
        if 'artifact' in item:
            need(item['artifact'] in artifacts, 'gate references unknown artifact: ' + gate_id)
        if status == 'pass':
            need(len(refs_used) > 0, 'gate marked pass needs evidence: ' + gate_id)
            need(any(refs[i]['source'] == 'observed' for i in refs_used),
                 'gate marked pass needs observed evidence, not fixture/inferred: ' + gate_id)
        else:
            need(nonempty(item.get('reason')), 'gate %s needs a reason' % gate_id)
            blockers += status in BLOCKING
    missing = [gate for gate in GATE_IDS if gate not in seen]
    need(not missing, 'missing gates: ' + ', '.join(missing))
    return blockers


def check(manifest_path):
    manifest_path = Path(manifest_path)
    base = manifest_path.resolve().parent
    data = json.loads(manifest_path.read_text(encoding='utf-8'))
    need(isinstance(data, dict), 'checklist root must be an object')
    need(set(data).issubset(TOP_FIELDS), 'unknown checklist fields: ' + ', '.join(sorted(set(data) - TOP_FIELDS)))
    need(data.get('schema_version') == 1, 'unknown checklist schema')
    for key in ('product', 'version', 'platform', 'executor'):
        need(nonempty(data.get(key)), 'missing ' + key)
    need(data.get('channel') in CHANNELS, 'unknown channel: %s' % data.get('channel'))
    need(data.get('signing') in SIGNINGS, 'unknown signing state: %s' % data.get('signing'))
    need(isinstance(data.get('limitations'), list) and all(isinstance(v, str) for v in data['limitations']),
         'limitations must be a list of strings')

    artifacts = _artifacts(data, base)
    refs = _evidence(data, base)
    blockers = _gates(data, refs, artifacts)

    # 没有公证的包，用户第一道坎是「打不开」。这条不满足不是结构错误（清单本身合法），
    # 而是一个必须显式记入的阻塞项——否则它会被混在「其余九道门都绿」里悄悄放过去。
    instruction = next(g for g in data['gates'] if g['id'] == 'first_run_instruction')
    signing_gap = data['signing'] in UNSIGNED and instruction['status'] != 'pass'
    blockers += signing_gap

    return {
        'status': 'BLOCKED' if blockers else 'READY_FOR_HANDOFF',
        'product': data['product'],
        'version': data['version'],
        'platform': data['platform'],
        'channel': data['channel'],
        'signing': data['signing'],
        'signing_gate': 'REQUIRES_FIRST_RUN_INSTRUCTION' if signing_gap else 'OK',
        'gates': len(data['gates']),
        'open_blockers': blockers,
        'artifacts': artifacts,
        'evidence': len(refs),
        'limitations': len(data['limitations']),
        'semantic_authenticity': 'NOT_VERIFIED',
        'runtime_verified': 'NOT_BY_THIS_TOOL',
        'release_authorized': False,
    }


def template(product, version, platform):
    need(nonempty(product) and nonempty(version) and nonempty(platform), 'product, version and platform are required')
    gates = []
    for gate in GATE_IDS:
        if gate == 'first_run_instruction':
            gates.append({'id': gate, 'status': 'unknown', 'reason': '填写：首次打开说明放在哪里'})
        else:
            gates.append({'id': gate, 'status': 'unknown', 'reason': '填写证据后改为 pass'})
    return {
        'schema_version': 1,
        'product': product,
        'version': version,
        'platform': platform,
        'channel': 'preview',
        'executor': '填写执行者标识',
        'signing': 'unsigned',
        'artifacts': [{
            'id': 'primary',
            'name': '%s-%s.dmg' % (product, version),
            'kind': 'dmg',
            'sha256': '0' * 64,
            'size': 1,
            'checksum_source': '填写校验和来源（Release 资产 / CI 日志 / 签名服务）',
        }],
        'evidence': [],
        'gates': gates,
        'limitations': [],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    command = sub.add_parser('check')
    command.add_argument('manifest', type=Path)
    command = sub.add_parser('template')
    command.add_argument('--product', required=True)
    command.add_argument('--version', required=True)
    command.add_argument('--platform', required=True)
    args = parser.parse_args()
    try:
        if args.command == 'check':
            result = check(args.manifest)
        else:
            result = template(args.product, args.version, args.platform)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, KeyError, TypeError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({'status': 'REJECTED', 'reason': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
