# Prism 当前状态

## 2026年10月28日：Mission 0.5.0能力升级（本地独立分支）

- 用户明确要求Prism支持CTF/Hackathon/Dev/REA，围绕最终目标主动落地业务结构、必要后端与部署方法，兼任产品/架构负责人领导编码。
- 新增docs/MISSION.md与标准库scripts/mission.py：目标合同、目录与覆盖清单、受信修订、宿主显式本地执行、代码/合同/证据绑定、未结算运行阻止和人工对账、非认证审查记录。普通audit和Foundry规划权限不变；未改sources快照或另一轮V04现场。
- 最终本机完整94项测试通过，含15项Mission测试；真实本机Python/SQLite跨进程持久化。实际架构子Agent独立审查发现并复验修复1项P1和5项P2，最终15项复跑通过；冻结文件与证据见docs/verification/mission-v05/。
- 未提供具体业务/赛事目标，真实目标为TARGET_REQUIRED；没有实际云部署、模型调用、比赛提交或经营结果。不内置自动AI编码器，不提供OS沙箱或cancel命令，当前宿主承担真实实现与边界核验。
- 本段只记录本机源库；提交、远端PR/CI、SkillHub接入和安装副本采用以各自后续读回为准，不凭本段声明已发布或所有宿主已升级。

2026年10月27日。目标：用户明确要求短名字、独立私有仓库、可单用且可由集团调用，与blueprint/checklist/site clone协作。名字采用Prism（棱镜），私有仓库已创建并读回isPrivate=true。

## 已完成与实际边界

- SKILL.md、总控审计Prompt、范围/报告/协作合同、AGENTS/CLAUDE共享规则已写。
- 既有Blueprint 1.1.0、Checklist、Site合同共6份固定源快照及SHA锁已写；未复制抓取器、浏览器或发布平台。
- Python标准库CLI支持plan/doctor/verify-report。实际能力是计划及结构/摘要/版本检查，不自动审计目标，也不输出产品通过或发布授权。
- 最终29项单元测试通过；实现冻结554a213后在干净git archive中复跑29项测试、6份源SHA和3种CLI计划；实际本机自检报告verify-report通过并保留独立审查UNKNOWN，证据见docs/verification/。

## 进行中与未验证

- 已冻结实现并完成隔离副本实测；远端推送/visibility与SHA以最终读回为准。
- 集团薄适配已在SkillHub codex/prism-20261027分支写入并固定实现554a213；本机显式别名、35路由例、13交付别名/9职责、8项site路由及Registry检查通过。集团main尚未合并，不能说共享入口已采用。
- 真实外部产品完整审计、独立QA、原生设备/抓取引擎可用性未验证。当前所有多视角均为执行者自检，不冒充独立reviewer。
- 不配置后台调度、不执行付费调用、不发布软件或声称PMF。GitHub Actions未配置/未运行，避免把本机检查说成远端CI。

## 恢复与验收

先读README、docs/SCOPE.md、docs/INTEGRATION.md与UPSTREAM.lock.json；运行doctor与unittest。源资产只在主库改，升级锁需差异审查。下一用户价值验收是对明确授权的真实产品运行审计，核对发现是否可复现与可交接。


## 2026年10月27日：明确Site Clone本体入口（0.1.1）

用户明确指定jaminliu89/site-reverse-clone。此前external_methods锁已是该仓库，但CLI只输出集团适配，未暴露本体直接路径；本轮修正为external_read输出固定2fa6cb0c版本的方法、ORCHESTRATION.md与web-clone实现三个入口，并校验外部来源锁。通过GitHub连接器读取该仓库README与固定编排/抓取入口确认身份，未修改该仓库或安装引擎。

31项回归及doctor通过，新增实跑计划明确返回用户指定仓库；规划/非软件审计不加载Site。相关输出及当前实现SHA-256见docs/verification/site-clone-direct/。仍未实际抓取或复刻任何目标。集团固定Prism版本需同步到本次修正，采用与合main继续分开报告。


## 2026年10月27日：全面项目审计（0.1.2）

用户明确Site Clone承担项目完整性、安全、内部人员/Agent协作和编排检查。其本体PR #1已合main bc3f7d7，新project-audit.md为唯一详细判据；Prism更新源锁/直接入口并显式输出审计维度，保留实际执行UNKNOWN与原发布权限。33项回归及doctor通过，独立静态审查通过；已按审查建议补缺失/空项目审计路径反例；未对外部产品实际审计。集团路由同步与合并由SkillHub当前任务承接。


## 2026年10月27日：Product Foundry V0.1 候选实现（分支，待独立验收）

基于集团已存在的 idea-to-blueprint 0–6 和 Prism 入口，实现文件驱动的阶段状态、答题与文档门禁、变更影响及下游确认失效、逐文档SHA、变更审计事件、只读 MCP 和不可自动执行的 Agent 交接包。新增 tests/test_foundry.py 与 docs/FOUNDRY_V0_1.md。

此次只是候选实现，不声称已合并 main，也不声称调用了真实外部 Agent、审查过真实产品、完成用户身份认证或拥有MCP客户端兼容实测。CI/测试和PR状态以后续远端证据为准。尚需改进并发写入锁、审批认证、细粒度需求依赖图和真实点子从输入到交接的端到端运行。

## 2026年10月27日：V0.2 主动安全与 Agent 任务合同（PR 草案）

已在独立功能分支增加 scripts/foundry_guard.py 与 scripts/foundry.py 入口，覆盖风险假设、保护资产/部署边界问答、阶段4安全门禁、阶段6验收文档、MCP 只读摘要、任务领取/交付/变更取消。详细使用限制在 docs/FOUNDRY_SECURITY_AND_AGENT_V02.md。

初版 CI 发现旧项目同时出现文档失效与安全未登记时主状态优先级的显示差异；已调整回归判据要求两类阻塞信息均可读取，绝不把该项目标为蓝图就绪。提交/PR合并和测试以 GitHub 实际结果为准，不声称独立审计或真实 CTF 抵抗验证已经完成。


## 2026年10月27日：V0.3 最小本机工作台（隔离分支候选）

目标：按用户明确授权，以 React/Tailwind/官方 shadcn/ui 实现三栏编辑型工作台；复用 Foundry V0.2，不改上游方法论或原 CLI。分支 feat/foundry-workbench-v03，从远端 main 601600b 接手。

已实现 scripts/foundry_web.py 本机适配，web/ 前端项目、点子/答案/文档/议题/裁决/自检/确认链路，DESIGN.md 与 docs/FOUNDRY_WORKBENCH_V03.md。三问、文档、专家意见均为真实文件保存；无模型调用。浏览未来阶段不允许误签当前阶段；外部改文档标记版本失效，预览列登记/当前SHA。

75项Python回归、3项Chrome UI/响应式/axe自动检查和构建以 docs/verification/foundry-v03/ 最终记录为准。独立审查发现两项主任务问题并回流修正，最终结论见独立审查记录。上述自动检查使用合成项目，不证明真实专家执行、身份认证、产品质量/PMF或生产发布。

未完成：正式身份与审批权限、多进程事务锁、真实外部Agent适配、完整Markdown渲染、安全档案/任务/变更完整图形表单。仍可用原CLI继续其流程。界面是 proposed，尚无用户审美认可；不部署、不合main。远端分支/PR/CI以最终读回为准。


## 2026年10月31日：交付与分发工程（知识能力 + 证据门）

用户要求把一次真实发版的经验固化成 Skill 交给 Prism 管理，并安排集团内相关人员学习吸收。本轮新增一个**判据与证据**能力，不是新的构建或发布平台：打包脚本仍留在产品主库，Prism 只维护判断、合同与验收。

- `docs/RELEASE_ENGINEERING.md`：五条原则、十条真实陷阱（现象/根因/可写进 CI 的判据/修法）、十道验收门、三次共学安排与评审者三问。
- `docs/RELEASE_GATE.md` + `scripts/release_gate.py`：清单合同与标准库 CLI（`template`/`check`）。只核证据结构、哈希、版本一致性与引用关系；`pass` 必须有 `observed` 证据；ad-hoc/未签名必须配首次打开说明，否则计入阻塞项。输出固定 `release_authorized: false`、`runtime_verified: NOT_BY_THIS_TOOL`。
- `docs/verification/release-engineering/`：`video-to-text` v0.5.2（固定提交 b8261f4）的真实证据 7 份 + 清单，`check` 返回 `READY_FOR_HANDOFF`、10 门、0 阻塞。
- `tests/test_release_gate.py`：30 项回归，覆盖缺门/未知门/伪证据/哈希不符/路径越界/产物名不含版本/ad-hoc 缺说明等反向路径。
- 路由：SKILL.md、README、INTEGRATION（发布主责仍归 delivery-walkthrough）、AGENTS 约束。

未验证：Intel 与旧 macOS、Apple 公证、包内完整转写流程、独立 review；证据为执行者自检。本能力不放行发布，也不替代 delivery-walkthrough。
