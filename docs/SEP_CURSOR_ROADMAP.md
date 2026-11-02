# SEP v1.0 — Cursor 执行路线图与交接手册

> 2026-11-02 规划快照；执行前必须重新检查 GitHub 实时状态。本文件记录**规划任务**而非已完成证明。
>
> 母合同：[SEP_INTEGRATION_V1.md](SEP_INTEGRATION_V1.md)；验收表：[SEP_PILOT_CHECKLIST.md](SEP_PILOT_CHECKLIST.md)；原有项目约束：仓库根目录 AGENTS.md、README.md、PROGRESS.md、docs/SCOPE.md、docs/INTEGRATION.md。

## 0. 决策、范围和完成定义

**剩余工作共 12 步，分四期**。其中步骤 1–3 为 Prism 内接入及合并，4–9 为真实产品试点，10–12 为集团集成与推广。每一步独立提交 / PR；除步骤 1–3 外不要把产品实现塞进 Prism 仓库。

目标：以真实可执行的回归测试和可追踪的发布证据，保护不断积累的旧功能。**不开发新的大型平台，不把 SEP 当成 Vibeguard 的内部功能**。

责任：
- 产品仓库：源代码、功能登记、运行测试、部署恢复的权威来源。
- Prism：任务规划、影响分析、检查调度合同和结果汇总；不得伪装已运行测试。
- SkillHub：路由发现和知识入口，保留集团大脑身份。
- Vibeguard：独立安全产品；只在明确接口和实际可用时集成。
- GitHub：Ruleset、PR、CI 的强制执行，不以 AGENTS.md 代替。

**总体完成条件**：一个经确认的产品试点在真实 commit 上走通新增功能→旧功能回归→PR/CI→合并→部署 smoke→非生产恢复演练，且能找到与版本对应的证据。若生产部署无授权，明确标 BLOCKED，不宣称最终闭环通过。

## 1. 分期路线图（12 步）

| # | 阶段 | 任务 / 预计落点 | 完成定义（DoD） | 前置 |
|---|---|---|---|---|
| 01 | A | 核实当前 PR #23 diff、权限、分支保护及现有 CI | 写出实际检查名称、运行结果、mergeability；无 CI 如实标 NOT_RUN | 无 |
| 02 | A | 对 SEP 两份基础文档及本路线图做一致性审核（Prism 分支） | 无与既有 AGENTS/Foundry/Mission 权限冲突；记录已审查证据 | 01 |
| 03 | A | PR #23 审核、按真实规则合并；若受阻则记录 | 合并 SHA 和 PR URL，或明确 BLOCKED 原因；不得绕过保护 | 02 |
| 04 | B | 选择一个现有产品仓库试点并建立 baseline | 确认 owner、实际分支、可复现运行命令、commit SHA、主要用户路径和已知缺陷 | 03 |
| 05 | B | 在试点建立功能登记与契约索引 | feature_id→入口、依赖、调用方、接口、测试映射；对照真实代码逐条抽查 | 04 |
| 06 | B | 建立关键旧功能自动回归和最小 smoke | 至少覆盖 2 条关键既有业务路径；既有失败不隐藏，记录测试环境 | 05 |
| 07 | B | 建立 PR 模板与项目适配 CI / Ruleset | 在分支提交；PR 最新 SHA 必需检查真实运行；Ruleset 生效可证实 | 06 |
| 08 | B | 选一项小新功能完整实施并分析依赖 | 需求/验收/影响表、最小代码变更、相关新旧功能测试有证据 | 07 |
| 09 | B | 合并、预览/部署 smoke 和非生产恢复演练 | 真实发布构建 SHA、Smoke 结果、回退演练与外部副作用说明；缺授权写 BLOCKED | 08 |
| 10 | C | Prism 增加可复用 SEP 任务/证据合同接入（若试点证明必要） | 不重复产品仓库测试；正反例、结构校验和真实失败状态覆盖 | 09 |
| 11 | C | SkillHub 路由 SEP；Vibeguard 独立接口适配（按需） | 真实仓库核验后单独 PR；接口版本明确，未安装时可 BLOCKED，不硬依赖 | 10 |
| 12 | D | 复盘试点并决定推广 | 统计用时、误报、漏检、阻断问题、维护成本；确定第二产品的最小复制清单 | 11 |

**下一步应先做 #01。** 本文撰写时，先前已创建 PR #23，但没有确认实际 CI 运行和合并许可；路线图提交后需重新查询最新 SHA 状态。

## 2. 推荐 PR 粒度

- **PR-A（当前 #23）**：协议、验收模板和路线图；不要混入实现代码。
- **PR-B1（试点仓库）**：baseline、功能登记和测试框架（04–06），若规模过大拆分。
- **PR-B2（试点仓库）**：PR/CI/Ruleset 配置和关键 smoke（07）。
- **PR-B3（试点仓库）**：单个新功能及相关回归（08）。
- **PR-C1（Prism）**：仅当试点需要时补 SEP 编排/证据检查（10）。
- **PR-C2（SkillHub）/ PR-C3（Vibeguard）**：分仓、独立版本和独立 review（11）。

每个小 PR：保持 main 不直接写、提交精确文件、逐项验收；失败优先修复当前分支。部署权限、密钥、生产数据库、付费外部动作不能从规划授权推断。

## 3. Cursor 首次接手操作

1. 在本机已获授权 GitHub 环境检查 `gh auth status`、`git status --short`、远端与默认分支；**不得打印密钥**。
2. 先读 `AGENTS.md`、`README.md`、`PROGRESS.md`、`docs/SCOPE.md`、`docs/INTEGRATION.md`、本目录三份 SEP 文档。
3. `gh pr view 23 --repo jaminliu89/prism --json state,mergeable,headRefOid,baseRefOid,statusCheckRollup,url`；`gh pr checks 23 --repo jaminliu89/prism`；核实 Ruleset / branch protection（权限不足写 UNKNOWN）。
4. `gh pr diff 23 --repo jaminliu89/prism` 并检查文档没有与项目真实状态冲突；只修必要文件。
5. 只在 CI / 审查 / 仓库权限允许时合并；**不得因为本文件写了“推进”就强行 merge**。
6. 后续步骤开始前确认试点仓库、实际构建/运行环境与授权；缺失时保留 BLOCKED，不伪造 PASS。

参考命令（按实际项目情况裁剪）：

```bash
git status --short
git fetch origin
gh pr view 23 --repo jaminliu89/prism --json state,mergeable,headRefOid,baseRefOid,statusCheckRollup,url
gh pr checks 23 --repo jaminliu89/prism
gh pr diff 23 --repo jaminliu89/prism
python3 -m unittest discover -s tests -v
python3 scripts/prism.py doctor
```

**注意**：以上测试命令仅适用于 Prism 工作树，必须实际执行并检查退出码；本路线图创建动作没有执行这些本机命令。

## 4. 每一步 Cursor 必须留下的交付记录

在相关仓库 PR 描述或 `docs/verification/sep/`（仅非敏感证据）写明：
- step_id、feature_ids、需求/验收、base/head commit SHA；
- 实际更改的文件、受影响模块、契约和旧功能；
- 测试命令、环境、退出码、日志/CI URL、失败与未运行项；
- 变更风险、数据库/外部服务副作用、恢复计划；
- PR URL、审查意见、merge SHA（如已合并）、部署构建/版本（如已部署）；
- status = NOT_STARTED | IN_PROGRESS | PASS | FAIL | BLOCKED | NOT_APPLICABLE；
- 下一步和阻塞原因。没有证据不准写 PASS。

更新路线图状态时，不允许因 PR 已打开就将合并、部署和生产验证标已完成。**每步只有符合 DoD 才可推进后一步**；受阻则回报具体阻塞，不通过删除测试、改低阈值、强推 main 来换绿灯。

## 5. 失败 / 紧急止损

- 工作区或 git 状态异常：停止自动修改，保护未提交工作（先查看 diff；不要直接 reset --hard）。
- PR 测试失败：保留日志，在 feature 分支修复，重跑完整必需检查。
- 意外引入回归：先停止合并/部署；共享主线使用新的 revert PR，不能强推历史。
- 数据迁移失败：执行已验证的数据库专属恢复预案，而非仅恢复 Git 代码。
- 依赖、权限或证据缺失：标 BLOCKED，报告缺少哪一个工具/权限/验证，不自行扩大授权。
- 任何声称“全部完成”之前必须校对 12 步 DoD；不可把设计文档当成产品已验证。

## 6. 给 Cursor 的可复制执行指令

> 你现在接手 `jaminliu89/prism` 的 SEP v1.0 工程任务。首先完整阅读 AGENTS.md、README.md、PROGRESS.md、docs/SCOPE.md、docs/INTEGRATION.md、docs/SEP_INTEGRATION_V1.md、docs/SEP_PILOT_CHECKLIST.md、docs/SEP_CURSOR_ROADMAP.md。按路线图 #01→#12 顺序执行，开始前验证最新 GitHub 状态，绝不假定之前的 PR/CI/merge 已成功。一次只完成一个可验收的小步骤，使用 feature branch→commit→PR→CI→审查→merge。不要破坏既有功能，不要把 Prism / SkillHub / Vibeguard 的责任混合，不要修改上游只读快照。运行真实测试并记录当前 SHA、退出码、CI 证据；未运行写 NOT_RUN，受阻写 BLOCKED。GitHub Ruleset、生产部署和数据库操作需要独立授权。每次回复列出：已完成的步骤、实测证据、当前剩余步骤、阻塞与下一步，不汇报无证据的成功。
