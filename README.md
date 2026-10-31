# Prism 棱镜

独立的产品规划与证据审计入口。可单独使用，也可由SkillHub路由，与Blueprint、Checklist、Site Clone协作。

## Mermaid 架构先行（0.7.0）

新产品与系统级研发在详细 PRD/API/数据/Agent 契约前，先产出 `docs/02-architecture-sketch.md` 并经实际架构审查。Prism Foundry 阶段 2 现在通过 `scripts/architecture_gate.py` 做 Mermaid 和架构推演段落静态检查，并要求正常阶段审查与确认，阶段 3 再写详细契约。正式架构/技术选型仍在原阶段 4，不重复建立方法论。旧项目不被静默迁移，普通修复复用既有架构。

[查看架构先行流程与 Mermaid 范例](docs/ARCHITECTURE_FIRST.md)

```sh
python3 scripts/architecture_gate.py tests/fixtures/architecture-sketch.md
python3 -m unittest discover -s tests -p 'test_architecture_gate.py' -v
```

以上仅是结构验证，并非 Mermaid 浏览器渲染、架构设计正确性或独立审批。

## 运行时环境自动补齐与预览部署（0.6.0）

Prism Mission 新增 [Runtime Bootstrap](docs/RUNTIME_BOOTSTRAP.md)：自动检查必要 CLI、项目依赖与部署状态；支持受控项目内 Python venv / npm ci、安全范围内的 macOS Homebrew 工具安装、本地静态预览，以及**已有 Vercel 项目**的非生产预览。当前会话内按权限与固定配方实际执行并验证，失败明确报告缺口，不把文档/安装候选冒充已部署。

```sh
python3 scripts/runtime_bootstrap.py plan --project /absolute/project --tool tshark --setup python-venv
python3 scripts/runtime_bootstrap.py apply --project /absolute/project --setup python-venv --allow-project-install
```

默认 `plan` 无副作用。机器全局安装、联网、外部预览、生产发布、费用和密钥权限不能静默扩大；自动化只在实际有能力的宿主获得相应授权后执行。CLI 不内置云账户，不会自行长期后台运行。

## 目标驱动研发（Mission 0.5.0）

明确让Prism承担CTF、Hackathon、Dev、REA或“复现这门生意并写代码”时，按[Mission合同](docs/MISSION.md)由当前Agent兼任产品负责人、架构师与集成负责人：主动取证、落地结构、实现必要后端与适用部署方法、实际验证并持续回流。普通审计仍只读；新模式不把Foundry规划权限扩大成工程或生产授权。

`python3 scripts/mission.py --help`提供目标目录初始化、状态、下一动作、宿主显式本地命令和证据审查记录。它不内置模型/抓取/REA引擎，也不是沙箱；目录模板不等于还原、进程成功不等于目标完成、部署方法不等于已部署。实际源码由当前宿主或明确指定的编码工具编写。完整用法及授权/版本边界见上述合同。

Prism把“用户要什么、产品实际上做了什么、证据证明了什么”放到同一条可追踪主线上。它是Skill、Prompt和轻量本地工具，不是无需输入就能自动审计所有产品的服务。

## 作为 Agent Skill 安装

本仓库根目录的 `SKILL.md` 是可发现入口，面向支持 Agent Skills 规范的 Agent 宿主。参考安装命令：

```sh
npx skills add jaminliu89/prism
```

**本仓库是私有仓库**：如果安装器不能直接使用已授权的 GitHub 凭据，先用 `gh auth login` 授权，再通过 `gh repo clone jaminliu89/prism` 克隆并执行 `npx skills add ./prism`。是否支持自动安装取决于目标 Agent 的 Skill CLI 与私有仓库访问权限；安装后仍须验证 Agent 是否成功发现 `prism`。不要公开仓库、泄露令牌或把安装成功视为产品审计已完成。

## 开始

克隆私有仓库后，让你的Agent完整读取 [SKILL.md](SKILL.md)。给出产品URL/仓库/资料和本次目的，可从点子规划、现有产品审计、专项取证到交付交接。工具与目标权限按本次环境核验。

```sh
gh repo clone jaminliu89/prism
cd prism
python3 scripts/prism.py doctor
python3 scripts/prism.py plan --mode audit --kind web --target 'https://your-authorized-product.example' --revision 'your-build-id'
```

`plan`只输出阅读路径和后续取证要求，不访问目标、不运行被审计代码。将`--kind`换成app、desktop、api、cli、service或other；非软件产品使用other。`--mode planning`走原blueprint阶段0–6；`clone`仅生成已明确请求复刻时的专项计划；`release`回交原delivery-walkthrough，不授权上线。

```sh
python3 scripts/prism.py verify-report /absolute/private-audit/audit.json
python3 -m unittest discover -s tests -v
```

`verify-report`检查 [报告合同](docs/REPORT_CONTRACT.md) 所述字段、证据摘要/版本/路径与已声明身份关系，返回STRUCTURALLY_VALID也可能有失败或受阻项；不认证证据内容、人员身份或产品通过，不替代独立QA。

## Wireshark 网络证据专项（离线优先）

按[网络证据编排合同](docs/NETWORK_PACKET_EVIDENCE_ROUTING.md)从已授权的PCAP/PCAPNG规划TShark、capinfos、editcap或Wireshark GUI分析。`python3 scripts/packet_evidence_router.py route --intent offline_protocol_timeline --access owned_capture` 只输出受控计划；未安装工具、未执行抓包、不代替REA/QA。实时接口抓包需要另外授权，Prism 不自动执行。

## 能力与边界

- [通用审计Prompt](docs/AUDIT_PROMPT.md)：恢复目标、阶段和历史资产，审需求、流程、设计、架构、数据、AI、安全与交付证据，按适用性裁剪。
- [规划Prompt](sources/skillhub/blueprint/MASTER_PROMPT.md)：既有idea-to-blueprint固定快照，逐阶段确认、规划期不写业务代码。
- [Checklist](sources/skillhub/checklist/final-checklist.md)：复用集团现有检查标准，不增加发布凭证。
- [Site Clone本体](https://github.com/jaminliu89/site-reverse-clone)：直接协作这个独立仓库的方法、编排与web-clone抓取实现；[集团取证合同](sources/skillhub/site/SKILL.md)仅负责接入，CLI的external_read给出固定版本直达路径。本仓未内置抓取器或浏览器。
- [集团协作合同](docs/INTEGRATION.md)：保留CPO/PM、设计、CTAB、工程、QA及发布主责；Prism维护编排，不复制能力主库。

Python 3.10+，仅标准库。随仓6份源文件按 [UPSTREAM.lock.json](UPSTREAM.lock.json) 锁定；独立使用不需要本机SkillHub目录。源能力更新须先在主库完成再显式升级快照，不自动跟随main。

审计报告可“不通过”或“未知”，AUDIT_ONLY只表示完成报告。修复、原型、付费、外发、生产修改需要各自授权。敏感报告默认放忽略的audits/，不自动上传到本仓。

版本/实测/缺口见 [PROGRESS.md](PROGRESS.md)，范围与验收见 [docs/SCOPE.md](docs/SCOPE.md)。


## Product Foundry V0.1（试验性运行层）

在原有规划与证据审计入口之外，新增 [Product Foundry V0.1](docs/FOUNDRY_V0_1.md)：对集团既有 idea-to-blueprint 阶段0–6增加本地可执行的阶段门禁、决策记录、防偏航变更影响、产物哈希与 Agent 交接 JSON；不更改源方法论和发布权限。

```sh
python3 scripts/foundry.py --project /tmp/my-product init --idea '你的产品点子' --actor owner
python3 scripts/foundry.py --project /tmp/my-product next
```

可通过 JSON CLI 被不同 Agent 宿主调用；只读 MCP stdio 提供项目状态与下一步要求。V0.1 **不含**自动 AI 推演、Agent 远程调度、真实身份认证、可视化工作台或工程执行。确认声明不等于经过认证的人类审批。完整使用示例、运行限制与测试入口见上述文档。

## Product Foundry V0.2（待验收）

在 V0.1 阶段门禁基础上加入[主动安全推演与多 Agent 任务合同](docs/FOUNDRY_SECURITY_AND_AGENT_V02.md)：在点子录入阶段提醒受保护的产品/编排资产；阶段4需给出威胁分类、控制措施、授权验证计划，不能只交架构图；阶段6增加安全验收计划。CLI 支持 security-status/security-profile/security-assess/security-draft 和 task-assign/task-claim/task-deliver/tasks；MCP 继续只读且最小披露。

**边界**：没有运行真实逆向、CTF、渗透测试，也没有自动调用任何 Agent；设计评审不能证明安全。当前位于提案分支，依照 PR 与 CI 状态决定是否合并。

## Product Foundry V0.3 本机工作台（候选）

React、Tailwind 与官方 shadcn/ui 三栏工作台，复用 Foundry V0.2 阶段/安全/争议门禁。支持点子、答案、文档编辑与基础预览、手动专家意见、审查与阶段确认；不自动调用模型，不认证审批身份。

```sh
npm ci --ignore-scripts --prefix web --registry=https://registry.npmjs.org
npm run build --prefix web
python3 scripts/foundry_web.py --workspace /absolute/private/foundry-projects --port 8773
```

浏览器打开 http://127.0.0.1:8773 。后端仍为 Python 标准库，CLI 用法不变；不要将本机服务暴露到公网。运行边界与接口见 [V0.3工程说明](docs/FOUNDRY_WORKBENCH_V03.md)，候选视觉见 [DESIGN.md](DESIGN.md)，检查证据见 [V0.3验证记录](docs/verification/foundry-v03/README.md)。

## 交付与分发工程（macOS 桌面端）

把「我这台机器上能跑」变成「用户双击能装」的判据集：[交付与分发工程](docs/RELEASE_ENGINEERING.md) 给出五条原则、十条真实陷阱（现象/根因/判据/修法）、十道验收门，以及给接手人的三次共学安排与评审者要问的三句话。

配套的 [交付清单合同](docs/RELEASE_GATE.md) 让「这次验过了」可被机器检查：

```sh
python3 scripts/release_gate.py template --product my-app --version 1.0.0 --platform macos-arm64 > release.json
# 填完证据后
python3 scripts/release_gate.py check release.json
```

`READY_FOR_HANDOFF` 表示十道门都有 `observed` 证据且哈希/版本自洽，**不**表示产物可用或可以发布（输出固定带 `release_authorized: false`）。实现脚本留在各产品主库，Prism 只维护判据与合同，不复制打包实现。真实案例与证据见 [v0.5.2 记录](docs/verification/release-engineering/README.md)。
