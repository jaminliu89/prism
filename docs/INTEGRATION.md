# 独立使用与集团协作

Prism自己的唯一源：`jaminliu89/prism`。集团路由唯一源：SkillHub根 `SKILL_REGISTRY.yaml`。原能力唯一源不迁移：idea-to-blueprint、delivery-walkthrough/checklist在SkillHub；site-reverse-clone方法在用户指定的 [jaminliu89/site-reverse-clone](https://github.com/jaminliu89/site-reverse-clone) 独立仓库。

其本体为 `skills/site-reverse-clone/SKILL.md`，编排规则为 `ORCHESTRATION.md`，抓取实现为 `skills/web-clone/`，专项在 `adapters/`。集团 `sources/skillhub/site/` 只是接入合同，不替代此仓库。Prism的审计/复刻/交付计划通过 `external_read` 列出该固定版本的直接阅读链接；方法与编排先读，抓取实现只在适用且已获授权时执行。全面项目审计另直接读取 `skills/site-reverse-clone/references/project-audit.md`，覆盖完整性、安全、内部人员/Agent协作与编排，审计不要求复刻。

| 意图 | 集团PRIMARY | Prism/其他能力 |
|---|---|---|
| 明确“Prism/棱镜/用棱镜审计产品” | Prism规划/审计编排SPECIALIST | CPO/PM保留价值与范围决定；按需加载checklist/site取证 |
| 普通“我有个点子/写PRD” | idea-to-blueprint | Prism可被调用组织资料；不接管阶段确认 |
| “走查/交付/checklist/上线” | delivery-walkthrough | Prism组织跨维度发现；site专项取证；现有发布合同不变 |
| “逆向/复刻这个目标” | agent-reverse-engineering或显式site-reverse-clone | Prism汇总需求/问题，不能用普通审计授权启动复刻 |
| 独立技术选型/设计 | CTAB / group-design-department | Prism向原owner提交发现，不决定更换基线/视觉 |

不抢占裸“审计”“QA”“产品”等宽泛别名。需要独立产品体检且用户明确选Prism时才走Prism主入口。跨专项只保留一条用户主线与一份问题ID映射。

## 三种部署/使用方式

### 明确委托Mission时的增量职责

用户明确让Prism领导vibecoding、实现目标或复现业务时，按[MISSION.md](MISSION.md)由实际当前Agent兼任产品负责人、架构师和技术集成执行职责，主动维护任务并接续授权内编码；不是另任命不存在的成员。独立模式可直接复用当前宿主，集团仍沿用既有产品/工程治理和实际验收者，不抢普通审计、技术选型或发布的宽泛路由。调用CTF/Hackathon/Dev/REA依据具体目标和授权，而不是出现关键词就执行第三方代码。

上表为普通审计/规划的原主责；明确Mission属于新增工程编排范围。既有Foundry handoff仍不授予工程权限；Mission的工程授权须另取用户开发委托。规划快照与专业引擎的主库不迁移，不修改sources只读资产。集团薄适配固定提交尚未升级时，必须先核对版本，不能宣称旧入口已具备Mission。

1. 独立离线：克隆私有仓库，读SKILL.md，用随仓规划/清单/审计Prompt与标准库CLI；不需要安装SkillHub。网络、浏览器、原生设备及site引擎仍按实际需要另行发现。
2. 集团：根Registry加载薄适配，按锁定Prism提交读本体；支持Agent在会话中使用当前可用工具。适配声明不等于自动安装、后台监听或所有旧会话已加载。
3. 专项：Prism把工作单交现有checklist/site/设计/技术能力，收回同版本证据与发现。收到其他Agent消息不自动授权反向发信，外发仍依当前用户授权。

## 固定版本快照

UPSTREAM.lock.json记录精确source repository/commit/path与本地SHA。`sources/`用于独立可读的固定版本资料，不是上游可执行引擎，不自动递归读取其所有引用。Prism只加载本任务明确需要的本地叶子文档；遇到外部依赖先按锁引用主库并确认实际可用性，缺失写受阻。

更新流程：在原能力主库修改→来源测试/审查→显式选择新提交→仅更新白名单源文件与lock→doctor与本仓回归→集团更新Prism固定版本。不得把快照改成另一套方法真相源。

用户项目报告、HAR、私有网页、凭证不作为集团共享规则自动回写；仅经确认的可复用知识按集团原有资产规则晋级。


## Web Evidence Router（2026-10-28）

Crawl4AI / Scrapling 双引擎按任务目标编排，候选顺序见固定 SkillHub 协作合同，脚本 `scripts/web_evidence_router.py` 只给执行宿主提供确定性选路、失败切换与证据摘要核验，不能当作真实抓取或MCP连接证据；详见 `docs/WEB_EVIDENCE_ROUTING.md`。源事实、权限和独立QA仍沿现有原owner。

## 网络包证据编排（Wireshark/TShark，2026-10-29）

明确网络协议、PCAP/PCAPNG、DNS/TLS/HTTP时序问题时，集团仍由 `agent-reverse-engineering` 受理逆向任务、委托 `network-packet-intelligence` 这一 TOOLBOX；Prism 仅按 [网络证据路由](NETWORK_PACKET_EVIDENCE_ROUTING.md) 选择 TShark/capinfos/editcap 或要求人工 GUI 复核，并与当前审计/ Mission 共享同版本 Evidence ID。不新建独立安全主责、不重写SkillHub原方法、不自动上传包或进行实际网卡捕获。

`python3 scripts/packet_evidence_router.py route --intent capture_metadata --access owned_capture` 只生成计划；`verify-evidence` 只核证据文件 SHA256/路径和最低结构约束，不代表网络结论认证。实时捕获须独立明确授权，即便声明已批准也仍为 PLAN_ONLY，交当前有权限宿主另行执行。无样本、无 CLI、无归属授权时保留 UNKNOWN/BLOCKED；独立QA与发布主责不变。
