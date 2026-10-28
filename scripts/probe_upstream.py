#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
probe_upstream.py — 上游指纹探测工具（Prism 取证沉淀，2026-10-29）

对本地 api-worker（Vibe助手 的本地网关，默认 127.0.0.1:9182）做只读式指纹探测，
采集模型目录与最小抽样响应，用于判定"这个额度网关背后对接的上游模型供应商"。

设计要点：
  - 用 curl --noproxy '*' 访问本机 worker，规避本机全局代理(fake-ip)对 127.0.0.1 的干扰。
  - 只发 max_tokens=1 的最小请求，把额度消耗压到接近零。
  - 指纹维度：id 前缀 / object / model 透传 / system_fingerprint / usage 结构 / Vertex 特征字段 / 模型 owned_by。
  - 输出：模型目录(分池) + 各池抽样指纹 + JSON 报告。

用法：
  python3 probe_upstream.py            # 全量：拉目录 + 抽样全部池
  python3 probe_upstream.py --catalog  # 仅拉模型目录
  python3 probe_upstream.py --sample gpt-5.4-mini  # 仅抽样指定模型
  python3 probe_upstream.py --json     # 附加输出 machine-readable JSON

依赖：仅 Python3 标准库 + 本机 curl。
"""
import json, subprocess, sys, time, os

AUTH_FILE = os.path.expanduser('~/api-worker/.auth')
BASE      = 'http://127.0.0.1:9182'
# 每个池取一个代表模型，覆盖 OpenAI 系 / DeepSeek / Claude(ccmax) / Claude(kiro)
DEFAULT_SAMPLES = [
    'gpt-5.4-mini', 'deepseek-v4.1-flash', 'gpt-6.1-sol',
    'ccmax:claude-opus-4-5', 'ccmax:claude-haiku-4-5',
    'kiro:claude-sonnet-5', 'kiro:claude-opus-4-6',
]

def auth_token():
    try:
        return open(AUTH_FILE).read().strip()
    except Exception as e:
        print(f'[!] 读取鉴权失败 {AUTH_FILE}: {e}')
        sys.exit(1)

def curl(path, payload=None, timeout=15):
    """用 curl --noproxy 请求 worker。payload 非空则 POST JSON，否则 GET。"""
    tok = auth_token()
    cmd = ['curl', '-s', '--noproxy', '*', '--max-time', str(timeout),
           '-H', f'x-auth-token: {tok}', '-H', 'Content-Type: application/json']
    if payload is not None:
        cmd += ['-d', json.dumps(payload)]
    cmd.append(BASE + path)
    t0 = time.time()
    out = subprocess.run(cmd, capture_output=True, text=True)
    raw = out.stdout
    dt = time.time() - t0
    return raw, dt

def fetch_catalog():
    """拉取 /v1/models，返回模型列表（带 owned_by / endpoint 类型 / 显示名）。"""
    raw, _ = curl('/v1/models?limit=1000')
    try:
        d = json.loads(raw)
    except Exception:
        print('[!] /v1/models 非 JSON:', raw[:200]); return []
    return d.get('data', [])

def parse_sse(raw):
    """解析 SSE(data: {...}+[DONE]) 或纯 JSON，返回首个 chunk dict 或 None。"""
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith('data: ') and line[6:] != '[DONE]':
            try: return json.loads(line[6:])
            except: pass
    try: return json.loads(raw)
    except: return None

def fingerprint(model):
    raw, dt = curl('/v1/chat/completions',
                   {'model': model, 'messages': [{'role': 'user', 'content': 'hi'}], 'max_tokens': 1})
    d = parse_sse(raw)
    if not d:
        return {'model': model, 't': round(dt, 2), 'raw': raw[:160]}
    u = d.get('usage', {})
    vertex = {k: u.get(k) for k in ('content_filter_results', 'input_tokens',
                                    'output_tokens', 'cached_tokens', 'reasoning_tokens') if k in u}
    return {
        'model': model, 't': round(dt, 2),
        'id': d.get('id'), 'object': d.get('object'),
        'model_ret': d.get('model'), 'fp': d.get('system_fingerprint'),
        'usage_keys': sorted(u.keys()), 'vertex_features': vertex,
        'error': d.get('error'),
    }

def split_pools(catalog):
    """按模型 id 前缀把目录分成池。"""
    pools = {}
    for m in catalog:
        mid = m.get('id', '')
        prefix = mid.split(':')[0] if ':' in mid else '(主池)'
        pools.setdefault(prefix, []).append(mid)
    return pools

def main():
    argv = sys.argv[1:]
    do_json = '--json' in argv
    if '--catalog' in argv:
        cat = fetch_catalog()
        pools = split_pools(cat)
        print(f'模型总数: {len(cat)}')
        for p, ids in pools.items():
            print(f'  [{p}] {len(ids)}个: {", ".join(ids[:12])}')
        return

    if '--sample' in argv:
        i = argv.index('--sample'); model = argv[i + 1]
        print(json.dumps(fingerprint(model), ensure_ascii=False, indent=2)); return

    # 默认全量
    cat = fetch_catalog()
    pools = split_pools(cat)
    print(f'== 模型目录（{len(cat)} 个）==')
    for p, ids in pools.items():
        print(f'  [{p}] {", ".join(ids[:12])}')
    print('\n== 各池抽样指纹 ==')
    results = []
    for m in DEFAULT_SAMPLES:
        r = fingerprint(m); results.append(r)
        print(f"  [{m}] id={r.get('id')} obj={r.get('object')} model_ret={r.get('model_ret')} "
              f"fp={r.get('fp')!r} usage_keys={r.get('usage_keys')} vertex={r.get('vertex_features')} t={r.get('t')}s")
        time.sleep(0.4)
    if do_json:
        print('\n== JSON ==')
        print(json.dumps(results, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
