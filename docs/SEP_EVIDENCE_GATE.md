# SEP v1.0 证据清单（Prism 结构门）

`scripts/sep_evidence_gate.py` 只核对 [SEP 接入合同](SEP_INTEGRATION_V1.md) 中 PR 证据 YAML/JSON 的字段与一致性。

## 证明什么

- 字段齐全、类型正确；
- `release_authorized` 必须为 `false`；
- 标 `PASS` 的测试项必须有非空 `evidence`；
- 标 `NOT_RUN` 的项不得带证据字符串冒充已跑。

## 不证明什么

- 不执行 `tests[].command`；
- 不验证 `head_sha` / `base_sha` 在 GitHub 上真实存在；
- 不构成发布许可；输出固定 `release_authorized: false`。

## 用法

```bash
python3 scripts/sep_evidence_gate.py template --change-id PR-11 --feature-id cli-agent > sep-evidence.json
python3 scripts/sep_evidence_gate.py check sep-evidence.json
```

试点样例：`docs/verification/sep/pilot-video-to-text-pr11.json`。
