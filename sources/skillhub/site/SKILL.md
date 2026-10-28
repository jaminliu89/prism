---
name: site-reverse-clone
description: 集团项目完整性、安全、内部人员/Agent协作编排与目标复刻审计专项。用于网页、App、桌面端、API、CLI 的抓取取证、行为与契约核对、架构复原、复刻保真度检查和归档；由 REA、交付走查或工程质量门禁调用。
metadata:
  version: "1.2.0"
  owner: "CTAB / QA Evidence"
---

# 目标复刻、走查与证据审计

本文件是集团适配入口。根 `SKILL_REGISTRY.yaml` 决定归属、状态和路由；方法论唯一权威保留在独立仓库，不复制另一份本体。

## 登记决定

2026-10-26 Founder 明确授权登记并承担走查、审计。采用 KEEP_WITH_BOUNDARY：独立仓库保留方法本体，SkillHub 维护集团适配、责任与调用合同；REA 为逆向主入口，delivery-walkthrough 为交付走查主责，现有 QA/发布门禁不变。本轮登记是规则接入，不是目标产品审计通过。

## 来源与可用性

- 仓库：https://github.com/jaminliu89/site-reverse-clone
- 锁定 revision：`bc3f7d7e2a70bcd1c4e6d04fd6a770c1ea9ad0f4`
- 方法入口：`skills/site-reverse-clone/SKILL.md`；抓取引擎：`skills/web-clone/`；专项适配器：`adapters/`。
- 开工先读取锁定版本方法与本次所需 references，发现实际 CLI/MCP/浏览器及目标权限。上游更新须对比差异和复验后更新锁定，不自动跟随 main。
- 集团 active 表示本适配协议已登记；不等于已安装工具、MCP 会话可用或真实目标已通过。网页能力有上游实测记录；API 部分实测；原生 App、Electron、CLI 的上游方法齐备但缺实战样本，本次逐目标验证。

## 责任与路由

- 逆向、技术拆解、复刻：`agent-reverse-engineering → site-reverse-clone`；显式指定本 Skill 时直达专项，不重复分诊。
- 软件走查、QA、交付：`delivery-walkthrough` 保持 PRIMARY，必须加载本专项完成适用证据审计；与复刻无关的普通软件同样适用。
- 技术/架构审计：`engineering-quality-os` 或董事会当前技术 PRIMARY 调用本专项；商业、财务、内容等领域负责人保留各自判断权。
- 外部资源读取与归档经 `connector-os`；实现交 CTO/工程体系，产品映射交 CPO，技术取舍交 CTAB。独立 QA 与最终发布门禁沿用现有制度。
- 不抢占通用“走查/QA/审计”别名，不新增董事会或项目状态机。

## 普通项目全面审计

用户已明确本能力一般用于项目完整性、安全、内部人员/Agent协作和编排审计，不限于复刻项目。必须读取独立仓库锁定版本的 `skills/site-reverse-clone/references/project-audit.md`，本体方法版本1.6.0；集团不复制第二份细则。

检查需求→用例→页面/角色/状态→接口/服务/模型→存储/真实输出→任务/证据闭环；安全覆盖凭证、身份/对象/租户授权、输入/工具执行、Prompt注入、供应链和运行配置。协作覆盖实际principal与接手、任务合同、最小权限、依赖/调度、并发/重试/取消/预算/终止、交接集成、独立验收及失败回流/重开。岗位登记、流程图、派工消息和自述都不能单独证明合格。无内部记录则UNKNOWN；逐域报告，不以平均分盖掉核心/安全/协作阻断。

明确项目完整性/协作编排审计可直达本专项；交付/上线仍由delivery-walkthrough主责，Prism可以串联本专项与checklist。审计不自动触发复刻、改代码或生产发布。

## 集团现有工具协作

执行前加载 [工具协作合同](references/TOOL_COLLABORATION.md) 与其机器可读分工。按目标调用集团现有 Playwright、browser-use、Crawl4AI、Scrapling、frontend-design 和工程/设计/Connector 工具箱；复用现有脚本和接口，不重复造抓取器或浏览器Agent。工具按证据缺口选择，交接同任务同版本证据，关键路径复验后归档。精确复刻与重设计使用不同视觉判据。

## 审计执行合同

1. 固定原需求、目标 URL/路径、源码与构建 revision、批准范围、资源预算；先恢复已有证据，再判六类目标及混合目标，避免重复抓取。
2. 逐项映射“承诺/用例 → 页面与状态 → 请求/契约 → 服务或模型 → 存储/输出 → 证据”。自有源码优先；无法观测的服务端实现保持 UNKNOWN。
3. 走查关键正常、失败、恢复与跨页链路，对照实际输入输出核实 API 字段/错误、持久化、刷新或重启恢复。复刻另核视觉、素材、交互与行为保真度；仅截图一致不能证明业务链通过。
4. 对 AI 产品按需求覆盖 prompt 版本/生成管线、模型选择与降级、工具调度、流式中断恢复、prompt-to-UI、实时预览、对话迭代、版本历史、部署和成本证据。无源码或日志权限时报告 PARTIAL/UNKNOWN，不能从前端猜完整内部实现。
5. 使用 SOURCE / PARTIAL / GUESS 标结论；真实响应只证明实际观测字段和条件，不证明后端源码。保存反例、版本、命令、原始响应/日志或截图引用。失败两次换观测面/方法，不能刷重试假装推进。
6. 每项发现记录 ID、P0/P1/P2/P3、用户影响、复现步骤、预期/实际、证据定位、owner、修复建议、复验结果；受阻项另记范围、原因和 next_condition。核心链 P0/P1 未解决不得建议放行。
7. 提交审计结果后由当前工程负责人修复，同版本回归；实现者不得更换角色名自称独立 QA。审计报告可如实不通过；只报告 AUDIT_ONLY，不将审计完成提升为正式交付/生产验收。

## 产物与出口

按实际任务维护：`NOTES.md`、`ARCHIVE_INDEX.md`、`BUSINESS_LOGIC_MERMAID.md`、`architecture-restoration.html`、`AUDIT_REPORT.md`；复刻时附 `CLONE_REPORT.md`。记录适用与不适用范围，已有等价产物可复用，禁止为补文件伪造证据。

归档前完成架构复原，缺失层显式标 UNKNOWN；冻结 revision 与文件摘要、校验快照、将发现/修复/未验证项映射回现有 Requirement/Task/Evidence。最终清单继续使用 `delivery-walkthrough` 的 release contract 和 `scripts/check-delivery-evidence.py`，本专项不另设放行凭证。

本合同不授予越权访问、付费、发信、生产改动或自动部署权限；沿用当前用户授权及 Connector 安全门禁。
