# Prism × ChatDev / MetaGPT：最小协作适配器（AGC-01）

状态：候选实现；以 PR/CI 和独立审查为准，不能视为已部署或集团全域采用。

## 设计与来源

研究 [ChatDev 2.0 DevAll](https://github.com/OpenBMB/ChatDev) 的 DAG、动态并行、依赖和执行记录（[Workflow Authoring](https://github.com/OpenBMB/ChatDev/blob/main/docs/user_guide/en/workflow_authoring.md)；研究提交 464a681ba7）与 [MetaGPT](https://github.com/FoundationAgents/MetaGPT) 的 SOP-as-code、角色交接、结构化输出（[Software Company](https://github.com/FoundationAgents/MetaGPT/blob/main/metagpt/software_company.py)；研究提交 11cdf466d0）。

未复制第三方源码，当前为标准库独立实现。ChatDev Apache-2.0，MetaGPT MIT；未来如直接移植第三方源码需保留适用版权及许可证通知。

Prism / SkillHub 已有唯一任务源、工程治理和 VibeGuard。这里仅新增只读任务投影，不创建第二个任务事实源和 Agent Runtime。

## 实现范围

事实源：项目原有的 .foundry/project.json。

- 校验任务、角色、阶段、唯一可写产物、权限和禁止自批约束。
- 输出当前阶段可并行领取、已领取和依赖阻塞任务；已交付依赖必须通过实际文件 SHA-256 核验。
- 生成 SOP 风格的 Agent packet（任务ID、角色、目标、输入、输出、权限和修订号）；只读，不执行、不认领、不写入、不审批。
- 校验交付文件与任务、阶段记录的三个 SHA-256 一致；不认证内容、审查员或 QA。
- 拒绝路径穿越、软链接、越权标记、循环依赖、冲突写者、过期阶段。

当前 Foundry 的 task-assign 不支持显式 depends_on 参数。只能校验已在既有任务状态中出现的依赖；默认仍靠阶段门禁决定前后顺序，同阶段无显式依赖的任务可并行。不能手工改动 .foundry/project.json 来绕过原任务合同。

## 使用

~~~sh
python3 scripts/foundry.py --project /absolute/product tasks
python3 scripts/agent_collaboration.py --project /absolute/product plan
python3 scripts/agent_collaboration.py --project /absolute/product packet --id AGT-0001
python3 scripts/agent_collaboration.py --project /absolute/product verify-artifact --id AGT-0001
~~~

真实执行仍由授权 Agent 宿主通过现有 foundry.py task-claim/task-deliver 操作。Foundry 的 PLANNING_DOCUMENT_ONLY 不能扩大为编程、生产、付费或部署授权；工程任务走 Engineering Agent OS、Quality OS 与 VibeGuard，独立 QA 与人类审批照旧。

## 证据边界

- 本地独立合成契约测试 33 项通过，不是 ChatDev/MetaGPT 上游完整测试。
- 额外的真实 Foundry 生命周期测试与全量 Prism 回归须以 PR 远端 CI 为准。
- 未直接运行两个上游框架，未创建自动调度真实 Agent、跨宿主身份认证或产品端到端 E2E，不冒充已验证。
