# 审计报告合同

AUDIT_REPORT.md是面向人的结论；audit.json是结构化索引，不能替代原始证据。它是专项审计材料，不是集团delivery manifest、关单收据或另一个发布门禁。

## JSON字段（顶层仅接受以下字段及可选limitations）

- `schema_version: 1`、`delivery_claim: "AUDIT_ONLY"`。
- `target`、`revision`、`scope`、`executor`：非空字符串，精确到本次对象/源码或部署版本；混合环境分别拆报告或在用例范围注明，不用别的版本证据凑数。
- `cases`：非空数组。每项：`id`、`requirement`、`status`、`evidence`（证据ID列表），状态为 pass/fail/blocked/unknown/not_applicable；后三项必须有`reason`。pass/fail须附同版本的observed证据。
- `evidence`：数组。每项：唯一`id`、本地相对`path`、`sha256`、`revision`、`source`（observed/fixture/inferred）。证据只允许报告所在目录以内的文件；绝对路径、越界与指向目录外的软链拒绝。URL存原始响应/脱敏截图等本地证据文件，并注明原URL/时间/环境；工具不自动联网取证。
- `findings`：数组。每项：唯一`id`、`severity`（P0–P3）、`status`（open/resolved）、`case_id`、`evidence`、`owner`、`reproduction`、`expected`、`actual`、`next_condition`。resolved必须通过`retest_evidence`（证据ID列表）引用复验证据，同revision；修复后的新版本应出新报告并链接历史问题。
- `review`：`status`为not_performed/self_check/independent_review；独立审查再提供不同于executor的实际`principal`与observed `evidence`列表。结构检查不能认证principal是真人或审查确实发生。

发现问题的合法报告也能通过结构校验。工具输出`STRUCTURALLY_VALID`只说明字段/文件摘要/版本与已声明身份关系可核验；同时给出open_blockers、incomplete_cases和`release_authorized:false`，绝不输出产品PASS。证据内容真实性、语义、覆盖是否充分仍由实际执行者和独立审查者负责。

真实报告默认保存在git忽略的 `audits/` 或用户指定私有位置，不提交被审计产品的数据。示例材料全部标明synthetic fixture，不能当实际审计证据。
