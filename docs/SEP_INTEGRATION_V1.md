# SEP v1.0 — 软件持续演进协议（Prism 接入合同）

状态：候选方案；未通过真实仓库 CI / 生产恢复演练，不代表已全面上线。

## 定位与权属

SEP 是可跨产品使用的工程治理协议，不是 Prism 内部新产品。SkillHub 负责集团能力发现与索引；Prism 负责按需规划、影响分析与任务编排；Vibeguard 保持独立产品，仅通过定义清晰的检查接口输出安全证据；产品仓库是其代码、功能登记、测试和发布历史的权威来源；GitHub Ruleset / CI 是合并门禁执行主体。Prism 不复制产品测试，不伪造独立 QA、CI 或发布结论。

## 不可跳过的七阶段

1. **基线**：读取当前分支、版本、README、AGENTS.md、架构、运行及恢复方法；确认已知测试状态，未知写 UNKNOWN。
2. **任务**：明确范围、验收标准、风险等级；从受保护主线创建 feature 分支。
3. **影响分析**：定位代码、调用方、公共 API、数据模式、权限、受影响功能与测试；依据代码和契约交叉核实登记表。
4. **最小变更**：控制提交范围；逐步 commit；不把 secrets、临时文件和无关修改纳入提交。
5. **验证**：静态检查、单测、契约与集成测试、关键流程 smoke；高风险变更升级到系统回归，记录缺口。
6. **交付**：PR + 必需 CI 检查 + 适当审查，合并后部署并验证实际运行版本；生产权限单独授权。
7. **回流**：更新功能登记、契约、测试、变更说明、部署或恢复证据；功能退出时记录迁移与兼容策略。

## 测试策略与防漏机制

L1：提交或 PR 更新执行 lint、类型检查、受影响单元测试。
L2：PR 合并前执行受影响模块集成 / 契约测试及固定核心业务 smoke。
L3：重要发布、定期或高风险变更执行全量必要回归、数据库迁移验证、权限与恢复演练。
如果影响范围不确定，不能把“未发现依赖”当成“没有依赖”；升级测试范围并列出未验证事项。测试通过只代表已运行的测试通过。

## 仓库建议接入面（不是强制统一目录）

- `AGENTS.md`：本地开发规则和权威文档入口。
- `docs/feature-registry.yaml`：feature_id、owner、entrypoints、contracts、dependencies、tests、status；记录与当前代码一致的更新时间。
- `docs/contracts/`：机器可核验的 API / 数据 / 行为约定。
- `tests/`：单测、集成、契约与 E2E；固定核心业务回归。
- `.github/pull_request_template.md`：任务、影响分析、验证结果、证据、回滚风险。
- `.github/workflows/`：实际可执行的项目级 CI；必需检查由 Ruleset 绑定，不凭模板存在声称已保护。
- `docs/runbooks/rollback.md`：代码、部署、数据库及外部副作用分别描述恢复方案。

## PR 最低证据合同

```yaml
sep_version: "1.0"
change_id: "PR-NUMBER"
feature_ids: []
base_sha: ""
head_sha: ""
affected_modules: []
affected_contracts: []
tests:
  - command: ""
    result: "PASS|FAIL|BLOCKED|NOT_RUN"
    evidence: ""
risk: "low|medium|high|unknown"
migration_plan: ""
rollback_plan: ""
open_gaps: []
release_authorized: false
```

字段被填充不等于内容已真实核验。证据必须对应当次提交与环境，不可沿用其他版本的绿色结果。

## 回滚原则

共享 main 优先在新分支准备 revert PR；merge commit 的 `git revert -m 1` 需确认父提交，squash commit 使用普通 revert。禁止强推改写共享 main。历史 tag 可用于 rescue 分支；`git reset --hard` 仅限已确认可丢弃本地未提交数据的非共享场景。数据库、对象存储、外部 API 副作用不因 Git revert 自动恢复。

## 验收与扩张

先选择单个产品仓库做试点：跑通一项真实功能变更、对应旧功能回归、PR/CI、部署 smoke 与恢复演练，记录误报、耗时与缺口。未取得真实结果前状态为 DESIGN_ONLY。本合同不修改 SkillHub 与 Vibeguard 仓库，也不声明这些系统已接入运行。
