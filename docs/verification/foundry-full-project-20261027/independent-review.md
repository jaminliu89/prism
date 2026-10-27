# 片场确认簿完整项目流程演练：独立验收审查

2026年10月27日。审查实际 principal：`codex:/root/ui_review`；主执行者：`codex:/root`。本审查没有修改源码、项目状态、确认或共享样例文档，只读检查完成后的项目。目标源码提交：`f94c32d69483a82fcbd71a34cd810e2b64b434a8`。

## 结论

**合成结构演练 PASS；纯网页完整流程 BLOCKED；正式产品蓝图 BLOCKED。不能把这次记录解释为真实产品或工程整体通过。**

| 验收对象 | 判定 | 实际证据与边界 |
| --- | --- | --- |
| UI+CLI从点子走完七阶段 | PASS | 项目5c77014a89b1eac1，revision51，7/7阶段已确认，16份阶段文档全部摘要有效且16个摘要互不相同；不是重复一份占位文档。 |
| 只用网页完成整个项目 | BLOCKED | 阶段4安全档案和威胁处置无录入UI，需CLI后才能确认；handoff也由CLI导出。六份集团辅助文档由脚本直接复制到磁盘，未经过工作台编辑。 |
| 正式蓝图批准与工程就绪 | BLOCKED | 七份确认均明确标TEST_PROXY、否认真实用户逐阶段确认；需求证据未知，任务未授权，文档自列未解决阻塞。当前BLUEPRINT_READY只说明机器结构状态。 |
| 真实需求/用户采用价值 | UNKNOWN | 没有真实访谈、客户委托、采用或订单证据。文件诚实标HYP和未验证。 |
| 样例产品实现/工程质量 | 未进入本轮验收 | 片场确认簿只有规划材料，未实际实现提案/反馈业务软件；不能把Prism工具跑通当样例产品已实现。 |
| 发布和安全运行验证 | 未授权/未验证 | execution_authorized=false、release_authorized=false、runtime_security_verified=false，不能当上线或安全通过。 |

## 已完成的独立观察

1. 读取Prism固定Blueprint的MASTER_PROMPT.md、DOCUMENT_CONTRACT.md，以及Foundry V0.1/V0.2/V0.3相关合同；本仓没有匹配的docs/work-orders目录。按project-acceptance-audit原则区分完成声称、实际行为和未验证层。
2. 已读取内容包全部16份阶段文档和6份辅助文档。内容分别覆盖原始意图/资产、定位研究、故事/状态、PRD/设计、架构/技术/威胁、路线/任务/DoD、一致性/安全验收/交接。它们不是重复占位；但所有业务判断仍属明确声明的合成假设。
3. 对实际项目目录 `/Users/kimliu/Developer/Codex/prism/work/browser-projects/5c77014a89b1eac1` 的16份登记文档逐项计算SHA256，与.foundry/project.json登记一致。事件日志52行、状态revision51；导出事件沿用revision51，不能把事件数量说成修订数量。
4. 用独立Chrome会话打开8777，实际选择完成样例。界面显示7/7已确认、修订51、无待决策议题。读取当前状态确认BLUEPRINT_READY、16项artifact_validity均true；七份确认的identity_verified全部false，声明均是TEST_PROXY_CONFIRMATION。
5. 独立实点阶段4、打开安全威胁文档。页面显示提交r39与登记SHA，编辑按钮disabled；文档明确“控制未实际执行”，并有安全档案补录后重交说明。再查看该阶段讨论，未出现伪造专家讨论。该只读会话没有pageerror。
6. 核对outcome.json、project-ref.json、final-snapshot.json、browser-steps.json、cli-steps.json、handoff.json与run.mjs。执行记录有39次网页动作和26条CLI调用记录；CLI记录包括status读取，不能全部说成26次变更。

## 主要缺口

### 1. 网页主链路在阶段4不能独立闭合

04-ui-capability.json显示securityProfileControls=0、securityAssessmentControls=0。04-security-refusal.json保存真实HTTP400：缺5项安全档案、7项威胁评估，design_ready=false，即使文档齐全且已有自检仍拒绝确认。随后执行者通过CLI登记档案/处置，再由网页重交失效安全文档并确认。

这是有效的后端拒绝证据，也证明纯网页用户在此会被阻塞。不能将“UI+CLI完成”报告成“纯工作台完成”。交接导出同样是CLI-only。此事实在既有V0.3文档中有说明，但用户要求完整网页工作流时仍是不完整能力。

### 2. 机器确认不等于真实用户批准

handoff.json的七份stage_confirmations均由同一执行者以TEST_PROXY记录，明确说明“我不是用户本人，不代表真实客户审批或逐阶段用户确认”，identity_verified=false。样例07-consistency-audit.md保留B-01真实需求未知、B-02真实阶段确认未发生、B-03独立内容审查待执行、B-04工程未授权。

这些记录诚实，适用于测试状态迁移；却不满足固定Blueprint“用户逐阶段确认、阻塞清零或范围经用户明确调整”的正式语义。BLUEPRINT_READY及“全部阶段已确认”不能单独证明正式规划通过。本次独立审查也不补签七阶段用户决定、不代替真实需求研究。

### 3. 六份集团辅助合同不在工作台白名单和交接版本锁内

实际存在六份：00-planning-state.md、risks-and-decisions.md、requirements-traceability.md、TODO.md、05-AGENTS-draft.md、05-CLAUDE-draft.md。run.mjs通过copyFileSync直接放入项目；foundry.DOCS只列16阶段文件，工作台文档读取白名单沿用该集合，六份辅助文件不能在现有UI/API里预览编辑。

它们未进入stage.artifacts的SHA登记，handoff.documents也只有16路径，不包含辅助六份；handoff本身不携逐文档SHA。原始状态文件保存16份摘要，但不能据此宣称导出包已锁定全部22份集团规划合同。这是追踪和交接的实际缺口。

## 文档语义判断

样例有明确P0范围：文本提案、反馈关联revision、裁决确认、导出恢复；US/REQ/AC/ADR/TASK能够基本对应，自动剪辑和云端审批被暂缓，未偷偷进入范围。需求、建议、裁决、运行结果与授权边界有区分。技术/安全是候选和验收计划，没有冒充已实现控制。

它仍不是正式工程输入：研究尚未发生，技术版本/许可核验待TASK-01，实际责任人和工程任务未获授权，阶段台账没有真实用户确认。文档自己诚实记录这些缺口；不能因机器允许导出而反推内容已经合格。

## 版本与证据边界

本次核验的源码SHA256：

- scripts/foundry.py：ad0428b2f7d56063ab8a5502fdec1921eeddb102f36f5db12572eb81b3f160d7
- scripts/foundry_guard.py：796aec232a94c49fb77817989a6054cd56eeffa2df715e5840e79a7e917c431b
- scripts/foundry_panel.py：69bafa5a47e9697f7e05bb4c5208209bdcc643e11803cd8c0bd0d762374ce88f
- scripts/foundry_web.py：62cc9afaa9c446941b642a8f3fae351c2b38c373b1cdc35a434fe0613fd0b824
- web/src/App.tsx：b7446ae01ffbc89a7f0710115a73b93833ea899b9e346205db8cceea4d25f82b
- web/src/index.css：c3ea9865235cd22446d6141df5a09f2c6761b0bc890bba850008ca6fcfd30f9b

实际证据为本目录执行记录、阶段快照、完成截图、真实项目状态/文档及本次独立只读浏览器观察。没有在本轮独立重放全部39次变更，没有执行篡改/变更回流负测，没有重新做容量实验；任何失败或未执行容量检查均不在此记为通过。没有认证用户身份、审查真实外部Agent、完成真实产品工程、安全渗透或生产发布。
