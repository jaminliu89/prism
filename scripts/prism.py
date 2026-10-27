#!/usr/bin/env python3
"""Local audit planning and structural evidence checks; never executes target code."""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import codegraph_provider

ROOT = Path(__file__).resolve().parents[1]
KINDS = ('web', 'app', 'desktop', 'api', 'cli', 'service', 'other')
MODES = ('planning', 'audit', 'clone', 'release')


def need(condition, message):
    if not condition:
        raise ValueError(message)


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def local_file(base, name):
    need(nonempty(name), 'missing file path')
    relative = Path(name)
    need(not relative.is_absolute(), 'absolute evidence/source path rejected')
    path = (base / relative).resolve()
    need(path.is_relative_to(base.resolve()), 'path escapes allowed directory')
    need(path.is_file(), 'missing file: ' + name)
    return path


def doctor(root=ROOT):
    lock = json.loads((root / 'UPSTREAM.lock.json').read_text())
    need(lock.get('schema_version') == 1, 'unknown source lock schema')
    assets = lock.get('assets')
    need(isinstance(assets, list) and len(assets) > 0, 'empty source lock')
    seen = set()
    for item in assets:
        need(item['id'] not in seen, 'duplicate source id')
        seen.add(item['id'])
        need(re.fullmatch(r'[0-9a-f]{40}', item['commit']) is not None, 'source commit must be pinned')
        path = local_file(root, item['path'])
        need(hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256'], 'source hash changed: ' + item['id'])
    methods = lock.get('external_methods')
    need(isinstance(methods, list) and len(methods) > 0, 'missing external method source')
    method_ids = set()
    for method in methods:
        need(nonempty(method.get('id')) and method['id'] not in method_ids, 'invalid/duplicate external method')
        method_ids.add(method['id'])
        need(re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', method.get('repository', '')) is not None, 'invalid external repository')
        need(re.fullmatch(r'[0-9a-f]{40}', method.get('commit', '')) is not None, 'external method must be pinned')
        for key in ('path', 'orchestration_path', 'engine_path', 'project_audit_path'):
            value = method.get(key)
            need(nonempty(value) and not Path(value).is_absolute() and '..' not in Path(value).parts, 'invalid external method path: ' + key)
    return {'status': 'SNAPSHOTS_VERIFIED', 'assets': len(assets), 'external_methods': len(methods), 'engines_installed': 'NOT_CHECKED'}


def plan(mode, kind, target, revision='', root=ROOT):
    need(mode in MODES and kind in KINDS, 'unknown mode or product kind')
    need(nonempty(target), 'missing target')
    need(not (mode in ('clone', 'release') and kind == 'other'), 'clone/release adapters require a supported software target; use scoped audit for other products')
    doctor(root)
    modules = ['docs/AUDIT_PROMPT.md', 'docs/REPORT_CONTRACT.md']
    primary = 'prism'
    if mode == 'planning':
        modules = ['sources/skillhub/blueprint/MASTER_PROMPT.md', 'sources/skillhub/blueprint/DOCUMENT_CONTRACT.md']
        primary = 'idea-to-blueprint'
    else:
        if kind != 'other':
            modules += ['sources/skillhub/checklist/final-checklist.md', 'sources/skillhub/site/SKILL.md', 'sources/skillhub/site/TOOL_COLLABORATION.md']
        if mode == 'clone':
            modules += ['sources/skillhub/site/SKILL.md']
            primary = 'agent-reverse-engineering / explicit site-reverse-clone'
        if mode == 'release':
            primary = 'delivery-walkthrough'
    modules = list(dict.fromkeys(modules))
    for module in modules:
        local_file(root, module)
    external_read = []
    if mode != 'planning' and kind != 'other':
        methods = json.loads((root / 'UPSTREAM.lock.json').read_text())['external_methods']
        for method in methods:
            if method['id'] == 'site-reverse-clone':
                external_read.append({
                    'repository': method['repository'], 'commit': method['commit'],
                    'method': f"https://github.com/{method['repository']}/blob/{method['commit']}/{method['path']}",
                    'orchestration': f"https://github.com/{method['repository']}/blob/{method['commit']}/{method['orchestration_path']}",
                    'capture_engine': f"https://github.com/{method['repository']}/blob/{method['commit']}/{method['engine_path']}",
                    'project_audit': f"https://github.com/{method['repository']}/blob/{method['commit']}/{method['project_audit_path']}",
                    'execution': 'Read pinned repository directly; discover actual engine and authorization before use. Not installed by Prism.'})
        need(len(external_read) == 1, 'missing site-reverse-clone direct source')
    return {'status': 'PLAN_ONLY', 'target': target, 'revision': revision or 'UNKNOWN', 'mode': mode, 'kind': kind,
            'primary_in_group': primary, 'read': modules, 'external_read': external_read,
            'audit_scope': ['project_completeness', 'security', 'personnel_agent_collaboration', 'orchestration', 'runtime_evidence'] if mode in ('audit', 'release') else [],
            'tool_discovery': 'verify browser/device/CLI/API access per target; snapshot does not install engines',
            'next': 'stage 0 clarification then wait for confirmation' if mode == 'planning' else 'freeze scope, inspect authorized target, collect actual evidence',
            'target_executed': False, 'release_authorized': False}


def verify_report(report_path):
    report_path = Path(report_path)
    base = report_path.resolve().parent
    data = json.loads(report_path.read_text())
    need(isinstance(data, dict), 'report root must be an object')
    need(set(data).issubset({'schema_version', 'delivery_claim', 'target', 'revision', 'scope', 'executor', 'cases', 'evidence', 'findings', 'review', 'limitations'}), 'unknown report fields; product/release assertions are not supported')
    need(data.get('schema_version') == 1, 'unknown report schema')
    need(data.get('delivery_claim') == 'AUDIT_ONLY', 'report cannot claim release or product PASS')
    for key in ('target', 'revision', 'scope', 'executor'):
        need(nonempty(data.get(key)), 'missing ' + key)
    evidence = data.get('evidence')
    need(isinstance(evidence, list), 'evidence must be a list')
    refs = {}
    for item in evidence:
        need(isinstance(item, dict) and nonempty(item.get('id')), 'invalid evidence')
        need(item['id'] not in refs, 'duplicate evidence id')
        need(item.get('revision') == data['revision'], 'evidence revision mismatch')
        need(item.get('source') in ('observed', 'fixture', 'inferred'), 'unknown evidence source')
        path = local_file(base, item.get('path'))
        need(hashlib.sha256(path.read_bytes()).hexdigest() == item.get('sha256'), 'evidence hash mismatch')
        refs[item['id']] = item

    def observed(ids):
        need(isinstance(ids, list) and len(ids) > 0, 'missing observed evidence')
        need(all(isinstance(i, str) and i in refs and refs[i]['source'] == 'observed' for i in ids), 'missing/fixture/inferred evidence cannot prove observed result')

    cases = data.get('cases')
    need(isinstance(cases, list) and len(cases) > 0, 'empty cases')
    ids = set()
    incomplete = 0
    for case in cases:
        need(isinstance(case, dict) and nonempty(case.get('id')) and case['id'] not in ids, 'invalid/duplicate case')
        ids.add(case['id'])
        need(nonempty(case.get('requirement')), 'case missing requirement')
        status = case.get('status')
        need(status in ('pass', 'fail', 'blocked', 'unknown', 'not_applicable'), 'invalid case status')
        if status in ('pass', 'fail'):
            observed(case.get('evidence'))
        else:
            need(nonempty(case.get('reason')), 'unknown/blocked/N/A case needs reason')
            incomplete += status != 'not_applicable'
            values = case.get('evidence', [])
            need(isinstance(values, list) and all(isinstance(i, str) and i in refs for i in values), 'unknown evidence reference')
    findings = data.get('findings')
    need(isinstance(findings, list), 'findings must be a list')
    seen_findings = set()
    blockers = 0
    for finding in findings:
        need(isinstance(finding, dict), 'invalid finding')
        for key in ('id', 'owner', 'reproduction', 'expected', 'actual', 'next_condition'):
            need(nonempty(finding.get(key)), 'finding missing ' + key)
        need(finding['id'] not in seen_findings, 'duplicate finding id')
        seen_findings.add(finding['id'])
        need(finding.get('case_id') in ids, 'finding references missing case')
        need(finding.get('severity') in ('P0', 'P1', 'P2', 'P3'), 'invalid severity')
        need(finding.get('status') in ('open', 'resolved'), 'invalid finding status')
        observed(finding.get('evidence'))
        if finding['status'] == 'resolved':
            observed(finding.get('retest_evidence'))
        blockers += finding['status'] == 'open' and finding['severity'] in ('P0', 'P1')
    review = data.get('review')
    need(isinstance(review, dict) and review.get('status') in ('not_performed', 'self_check', 'independent_review'), 'invalid review status')
    if review['status'] == 'independent_review':
        need(nonempty(review.get('principal')) and review['principal'].strip().casefold() != data['executor'].strip().casefold(), 'executor cannot claim independent review')
        observed(review.get('evidence'))
    return {'status': 'STRUCTURALLY_VALID', 'cases': len(cases), 'open_blockers': blockers, 'incomplete_cases': incomplete,
            'independent_review': review['status'], 'semantic_authenticity': 'NOT_VERIFIED', 'release_authorized': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('doctor')
    command = sub.add_parser('plan')
    command.add_argument('--mode', choices=MODES, default='audit')
    command.add_argument('--kind', choices=KINDS, required=True)
    command.add_argument('--target', required=True)
    command.add_argument('--revision', default='')
    command = sub.add_parser('verify-report')
    command.add_argument('report', type=Path)
    command = sub.add_parser('codegraph-impact')
    command.add_argument('--repo', required=True)
    command.add_argument('--changed', nargs='+', required=True)
    command.add_argument('--codegraph-bin', required=True)
    command.add_argument('--allow-local-codegraph', action='store_true')
    args = parser.parse_args()
    try:
        if args.command == 'doctor': result = doctor()
        elif args.command == 'plan': result = plan(args.mode, args.kind, args.target, args.revision)
        elif args.command == 'codegraph-impact':
            result = codegraph_provider.impact(
                args.repo, args.changed, args.codegraph_bin,
                opt_in=args.allow_local_codegraph)
        else: result = verify_report(args.report)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(json.dumps({'status': 'REJECTED', 'reason': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
