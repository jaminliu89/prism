#!/usr/bin/env python3
"""Scoped goal workspace and host-authorized local execution; not a sandbox or AI engine."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import tempfile
import uuid

PROFILES = ('ctf', 'hackathon', 'dev', 'rea')
BACKEND = ('domain_api', 'auth_permissions', 'database_migrations', 'storage',
           'async_jobs', 'model_external_services', 'billing_cost', 'configuration_secrets',
           'observability', 'backup_restore', 'health_checks', 'release_rollback')
SKIP = {'.git', '.prism', 'node_modules', '.venv', '__pycache__'}
UNSETTLED = {'RUNNING', 'RECOVERY_REQUIRED', 'UNKNOWN'}


def need(ok, message):
    if not ok:
        raise ValueError(message)


def text(value):
    return isinstance(value, str) and bool(value.strip())


def digest(data):
    return hashlib.sha256(data).hexdigest()


def contract_hash(spec):
    return digest(json.dumps(spec, sort_keys=True, ensure_ascii=False).encode())


def now():
    return datetime.now(timezone.utc).isoformat()


def read_regular(path):
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        need(stat.S_ISREG(info.st_mode), 'non-regular evidence/snapshot file rejected')
        need(info.st_size <= 20 * 1024 * 1024, 'snapshot budget exceeded; narrow the project before executing')
        data = stream.read(20 * 1024 * 1024 + 1)
        need(len(data) <= 20 * 1024 * 1024, 'snapshot budget exceeded while reading')
        return data


def under(root, relative):
    p = Path(relative)
    need(not p.is_absolute() and '..' not in p.parts and p.parts, 'invalid relative path')
    current = root
    for part in p.parts:
        current = current / part
        need(not current.is_symlink(), 'symlink path rejected')
    need(current.resolve().is_relative_to(root.resolve()), 'path escapes project')
    return current


def state_path(root):
    need(root.is_dir() and not root.is_symlink(), 'project must be an existing real directory')
    return under(root, '.prism/mission.json')


def write_json(path, value):
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    with temporary.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


@contextmanager
def locked(root):
    state_path(root)
    folder = under(root, '.prism')
    folder.mkdir(exist_ok=True)
    with under(root, '.prism/mission.lock').open('a') as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('another mission writer is active')
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def load(root):
    value = json.loads(state_path(root).read_text())
    need(value.get('schema_version') == 1, 'unsupported mission schema')
    return value


def snapshot(root):
    files, omissions = {}, []
    def failed_walk(error):
        raise error
    for folder, dirs, names in os.walk(root, followlinks=False, onerror=failed_walk):
        dirs[:] = sorted(d for d in dirs if d not in SKIP)
        for d in list(dirs):
            p = Path(folder) / d
            if p.is_symlink():
                omissions.append(str(p.relative_to(root)))
                dirs.remove(d)
        for name in sorted(names):
            p = Path(folder) / name
            rel = str(p.relative_to(root))
            if name == '.env' or name.startswith('.env.') or p.is_symlink():
                omissions.append(rel)
                continue
            need(len(files) < 10000,
                 'snapshot budget exceeded; narrow the project before executing')
            files[rel] = digest(read_regular(p))
    return {'id': digest(json.dumps(files, sort_keys=True).encode()),
            'files': files, 'excluded': sorted(omissions), 'excluded_directories': sorted(SKIP),
            'coverage': 'project files except declared exclusions; not environment or external state'}


def validate_spec(root, spec):
    need(isinstance(spec, dict), 'mission spec must be an object')
    need(isinstance(spec.get('implementation_authorized', False), bool), 'implementation_authorized must be boolean')
    need(spec.get('profile') in PROFILES, 'profile must be ctf/hackathon/dev/rea')
    for key in ('goal', 'principal', 'scope'):
        need(text(spec.get(key)), 'missing ' + key)
    need(isinstance(spec.get('acceptance'), list) and spec['acceptance'] and
         all(text(x) for x in spec['acceptance']), 'acceptance must contain observable conditions')
    components = spec.get('components', [])
    need(isinstance(components, list), 'components must be a list')
    paths = []
    for item in components:
        need(isinstance(item, dict) and text(item.get('purpose')), 'component purpose required')
        path = item.get('path', '')
        under(root, path)
        need(Path(path).parts[0] not in SKIP and Path(path).parts[0] != 'docs', 'reserved component path')
        need(item.get('source') in ('observed', 'inferred', 'proposed'), 'component source required')
        paths.append(path)
    need(len(set(paths)) == len(paths), 'duplicate component path')
    target = spec.get('target', '')
    need(isinstance(target, str), 'target must be text')
    if spec['profile'] == 'ctf':
        need(text(spec.get('competition_rules')), 'CTF requires rules and allowed targets')
    if spec['profile'] == 'hackathon':
        need(text(spec.get('submission_rules')), 'hackathon requires demo/submission rules')
    return paths, target


def initialize(root, spec):
    paths, target = validate_spec(root, spec)
    components = spec.get('components', [])
    state = {'schema_version': 1, 'id': 'MSN-' + uuid.uuid4().hex[:12],
             'created_at': now(), 'spec': spec, 'runs': [], 'reviews': [],
             'status': 'DISCOVERING' if target.strip() else 'TARGET_REQUIRED',
             'identity_verified': False, 'release_authorized': False}
    docs = {
        'docs/prism-mission/GOAL.md': '# 最终目标\n\n' + spec['goal'] + '\n\n目标：' +
            (target or 'TARGET_REQUIRED') + '\n\n授权范围：' + spec['scope'] +
            '\n\n验收条件：\n' + '\n'.join('- ' + x for x in spec['acceptance']) +
            '\n\nCTF规则：' + spec.get('competition_rules', 'N/A') +
            '\n\nHackathon提交规则：' + spec.get('submission_rules', 'N/A') + '\n',
        'docs/prism-mission/STRUCTURE.md': '# 目标结构与证据映射\n\n' +
            '\n'.join('- `%s` — %s [%s]' % (x['path'], x['purpose'], x['source']) for x in components) +
            '\n\n仅创建目录不代表原项目被还原。补充入口、真实来源、模块依赖和数据流；私有后端未知。\n',
        'docs/prism-mission/BUSINESS.md': '# 业务复现\n\n待取证：目标用户、输入→处理→输出、保存/消费、错误恢复、收入机制和成本。\n\n复现可观察能力与合法替代实现；不得将推断写成原站私有源码、订单、收入或PMF。\n',
        'docs/prism-mission/BACKEND.md': '# 后端覆盖清单\n\n每行补方案、来源、代码路径、验收和阻塞；N/A必须有理由。\n\n' +
            '\n'.join('- ' + key + ': UNKNOWN' for key in BACKEND) + '\n',
        'docs/prism-mission/DEPLOYMENT.md': '# 适用部署方法\n\n状态：NOT_DEPLOYED。平台与栈未决定，不默认生成某云配置。\n\n逐个适用环境记录：本地/私有测试/生产，依赖与版本、环境变量键名、数据库迁移、启动命令、健康检查、持久化/网络、备份恢复、日志、升级/回滚及费用。\n\n经取证确定的每种部署方法须有实际配置/脚本与运行证据；未知项与N/A理由保留。生产发布另需明确授权。\n',
        'docs/prism-mission/TASKS.md': '# 实现任务\n\n复用原项目唯一任务看板；本表只映射目标和证据，不建立平行看板。\n\n1. 检查目标入口/目录/资料，记录observed/inferred/unknown。\n2. 确定业务链、后端与部署方案，关联每条验收条件。\n3. 在已获工程授权内由当前宿主或指定编码CLI实际实现；不止返回规划。\n4. 跑真实输入→处理→输出、失败恢复与同版本验收。\n\n每项补任务ID、允许文件、依赖、实际执行者、输入版本、输出、检查命令、证据和失败回流。\n',
    }
    for path in paths:
        docs[path.rstrip('/') + '/PRISM-COMPONENT.md'] = '# 组件待实现\n\n此目录来自目标合同；不声称已有业务代码。具体职责见结构映射。\n'
    with locked(root):
        need(not state_path(root).exists(), 'mission already exists; refusing overwrite')
        for name in docs:
            path = under(root, name)
            need(not path.exists(), 'existing artifact would be overwritten: ' + name)
            for parent in path.parents:
                if parent == root:
                    break
                need(not parent.exists() or parent.is_dir(), 'artifact ancestor is not a directory: ' + str(parent))
        published = []
        try:
            with tempfile.TemporaryDirectory(prefix='mission-init-', dir=root/'.prism') as staging:
                for index, (name, content) in enumerate(docs.items()):
                    staged = Path(staging)/str(index)
                    staged.write_text(content, encoding='utf-8')
                for index, name in enumerate(docs):
                    path = under(root, name)
                    path.parent.mkdir(parents=True, exist_ok=True)
                    os.link(Path(staging)/str(index), path)
                    published.append((path, path.stat().st_ino))
                write_json(state_path(root), state)
        except (OSError, ValueError):
            for path, inode in reversed(published):
                if path.exists() and not path.is_symlink() and path.stat().st_ino == inode:
                    path.unlink()  # Only this failed initialization's own published files.
            raise
    return {'status': state['status'], 'mission_id': state['id'], 'artifacts': list(docs),
            'implementation': 'NOT_STARTED', 'deployment': 'NOT_DEPLOYED'}


def next_action(root):
    state = load(root)
    if not state['spec'].get('target', '').strip():
        action = 'provide concrete target and scope; no target reconstruction has occurred'
        status = 'TARGET_REQUIRED'
    elif any(r['status'] in UNSETTLED for r in state['runs']):
        action = 'inspect owned process and existing artifacts; do not blindly restart'
        status = 'RUNNING_OR_RECOVERY_REQUIRED'
    elif not state['spec'].get('implementation_authorized', False):
        action = 'inspect target and fill business/backend/deployment; obtain engineering authorization before code execution'
        status = 'DISCOVERING'
    else:
        action = 'current host must inspect artifacts, implement scoped code, execute checks and submit same-version review'
        status = 'HOST_DEV_REQUIRED'
    return {'status': status, 'next': action, 'latest_run': state['runs'][-1] if state['runs'] else None,
            'identity_verified': False, 'release_authorized': False}


def execute(root, command, actor, opt_in=False, timeout=120):
    need(opt_in, 'explicit host opt-in --allow-local-execution required')
    need(text(actor) and command and all(text(x) for x in command), 'actor and exact command required')
    need(1 <= timeout <= 3600, 'timeout outside 1..3600 seconds')
    with locked(root):
        state = load(root)
        need(state['spec'].get('implementation_authorized') is True and
             text(state['spec'].get('authorization_statement')), 'trusted engineering authorization required')
        need(text(state['spec'].get('target')), 'concrete target required')
        need(not any(r['status'] in UNSETTLED for r in state['runs']), 'unsettled run requires reconciliation')
        run_id = 'RUN-' + uuid.uuid4().hex
        folder = under(root, '.prism/runs/' + run_id)
        folder.mkdir(parents=True)
        before = snapshot(root)
        record = {'id': run_id, 'actor_claim': actor, 'command': command, 'started_at': now(),
                  'status': 'RUNNING', 'before': before, 'contract_hash': contract_hash(state['spec']),
                  'environment_verified': False}
        state['runs'].append(record)
        write_json(state_path(root), state)
        process = None
        try:
            with (folder/'stdout.log').open('xb') as stdout, (folder/'stderr.log').open('xb') as stderr:
                process = subprocess.Popen(command, cwd=root, stdin=subprocess.DEVNULL,
                                           stdout=stdout, stderr=stderr, start_new_session=True)
                record['pid'] = process.pid
                write_json(state_path(root), state)
                try:
                    record['exit_code'] = process.wait(timeout=timeout)
                    record['status'] = 'EXITED' if process.returncode == 0 else 'FAILED'
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                    record.update(status='TIMEOUT', exit_code=process.returncode)
            record['after'] = snapshot(root)
            record['logs'] = {str(p.relative_to(root)): digest(read_regular(p)) for p in
                              (folder/'stdout.log', folder/'stderr.log')}
            record['ended_at'] = now()
            record['semantic_acceptance'] = 'NOT_REVIEWED'
            write_json(state_path(root), state)
        except (OSError, ValueError) as exc:
            record.update(status='RECOVERY_REQUIRED', error=str(exc))
            write_json(state_path(root), state)
            raise
    return {'status': record['status'], 'run_id': run_id, 'exit_code': record.get('exit_code'),
            'snapshot_id': record['after']['id'], 'logs': record['logs'],
            'semantic_acceptance': 'NOT_REVIEWED', 'usage': 'UNKNOWN', 'release_authorized': False}


def review(root, report):
    need(isinstance(report, dict), 'review report must be an object')
    with locked(root):
        state = load(root)
        run = next((x for x in state['runs'] if x['id'] == report.get('run_id')), None)
        need(run and run['status'] == 'EXITED', 'only successful settled execution can be reviewed')
        need(run['contract_hash'] == contract_hash(state['spec']), 'mission contract changed since execution')
        need(text(report.get('reviewer')) and report['reviewer'] != run['actor_claim'], 'self review rejected')
        need(report.get('snapshot_id') == run['after']['id'] == snapshot(root)['id'], 'stale code evidence')
        for name, sha in run['logs'].items():
            need(digest(read_regular(under(root, name))) == sha, 'execution log changed')
        cases = report.get('cases', [])
        need(isinstance(cases, list) and all(isinstance(x, dict) for x in cases), 'review cases must be objects')
        need(len(cases) == len(state['spec']['acceptance']), 'all acceptance conditions must be reviewed')
        need([x.get('requirement') for x in cases] == state['spec']['acceptance'], 'acceptance mismatch')
        for case in cases:
            need(case.get('status') in ('pass', 'fail', 'blocked', 'unknown') and text(case.get('reason')),
                 'case requires status and observed reasoning')
            refs = case.get('evidence', [])
            need(refs and all(isinstance(e, dict) and text(e.get('path')) and text(e.get('sha256')) for e in refs),
                 'case evidence references required')
            for evidence in refs:
                path = under(root, evidence['path'])
                registered = run['logs'].get(evidence['path'], run['after']['files'].get(evidence['path']))
                need(registered and registered == evidence['sha256'], 'evidence not registered to this run/snapshot')
                need(path.is_file() and digest(read_regular(path)) == evidence['sha256'], 'evidence missing or changed')
        saved = dict(report, recorded_at=now(), identity_verified=False,
                     conclusion='RECORDED_REVIEW_NOT_AUTHENTICATED', release_authorized=False)
        state['reviews'].append(saved)
        write_json(state_path(root), state)
        return saved


def reconcile(root, run_id, actor, reason, confirmed_stopped=False):
    need(confirmed_stopped and text(actor) and text(reason),
         'trusted host must inspect side effects and confirm no owned process remains')
    with locked(root):
        state = load(root)
        run = next((x for x in state['runs'] if x['id'] == run_id), None)
        need(run and run['status'] in UNSETTLED, 'run is not awaiting reconciliation')
        if run.get('pid'):
            try:
                os.kill(run['pid'], 0)
            except ProcessLookupError:
                pass
            else:
                raise ValueError('recorded PID still exists; verify ownership and settlement before reconciliation')
        current = snapshot(root)
        run['reconciliation'] = {'actor_claim': actor, 'reason': reason, 'at': now(),
                                 'snapshot': current, 'identity_verified': False}
        run['status'] = 'FAILED_RECONCILED'
        write_json(state_path(root), state)
        return {'status': 'FAILED_RECONCILED', 'run_id': run_id,
                'next': 'inspect partial changes and prepare a new attempt; old run not accepted'}


def amend(root, spec, actor, reason):
    validate_spec(root, spec)
    need(text(actor) and text(reason), 'trusted host actor and amendment reason required')
    with locked(root):
        state = load(root)
        need(not any(r['status'] in UNSETTLED for r in state['runs']), 'reconcile unsettled runs before amendment')
        need(spec.get('components', []) == state['spec'].get('components', []),
             'component layout changes require host-reviewed project edits, not automatic amendment')
        old_hash = contract_hash(state['spec'])
        state.setdefault('amendments', []).append({'previous_spec': state['spec'], 'at': now(),
                                                   'actor_claim': actor, 'reason': reason,
                                                   'previous_contract_hash': old_hash})
        state['spec'] = spec
        state['status'] = 'DISCOVERING' if spec.get('target', '').strip() else 'TARGET_REQUIRED'
        write_json(state_path(root), state)
        return {'status': state['status'], 'contract_hash': contract_hash(spec),
                'next': 'host must reconcile goal/architecture/task docs with amended canonical mission spec',
                'prior_reviews': 'immutable historical records; not approval of amended contract'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True, type=Path)
    sub = parser.add_subparsers(dest='action', required=True)
    init = sub.add_parser('init'); init.add_argument('--spec', required=True, type=Path)
    sub.add_parser('next')
    sub.add_parser('status')
    run = sub.add_parser('run')
    run.add_argument('--actor', required=True)
    run.add_argument('--allow-local-execution', action='store_true')
    run.add_argument('--timeout', type=int, default=120)
    run.add_argument('argv', nargs=argparse.REMAINDER)
    rev = sub.add_parser('review'); rev.add_argument('--report', required=True, type=Path)
    rec = sub.add_parser('reconcile')
    rec.add_argument('--run-id', required=True)
    rec.add_argument('--actor', required=True)
    rec.add_argument('--reason', required=True)
    rec.add_argument('--confirm-no-owned-process', action='store_true')
    change = sub.add_parser('amend')
    change.add_argument('--spec', required=True, type=Path)
    change.add_argument('--actor', required=True)
    change.add_argument('--reason', required=True)
    args = parser.parse_args()
    try:
        need(args.project.is_absolute(), 'explicit absolute project directory required')
        state_path(args.project)
        if args.action == 'init':
            result = initialize(args.project, json.loads(args.spec.read_text()))
        elif args.action == 'run':
            argv = args.argv[1:] if args.argv[:1] == ['--'] else args.argv
            result = execute(args.project, argv, args.actor, args.allow_local_execution, args.timeout)
        elif args.action == 'review':
            result = review(args.project, json.loads(args.report.read_text()))
        elif args.action == 'reconcile':
            result = reconcile(args.project, args.run_id, args.actor, args.reason, args.confirm_no_owned_process)
        elif args.action == 'amend':
            result = amend(args.project, json.loads(args.spec.read_text()), args.actor, args.reason)
        elif args.action == 'status': result = load(args.project)
        else: result = next_action(args.project)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result.get('status') in ('FAILED', 'TIMEOUT') else 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({'status': 'REJECTED', 'reason': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
