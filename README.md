# Prism 棱镜

独立的产品规划与证据审计入口。可单独使用，也可由SkillHub路由，与Blueprint、Checklist、Site Clone协作。

Prism把“用户要什么、产品实际上做了什么、证据证明了什么”放到同一条可追踪主线上。它是Skill、Prompt和轻量本地工具，不是无需输入就能自动审计所有产品的服务。

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

## 能力与边界

- [通用审计Prompt](docs/AUDIT_PROMPT.md)：恢复目标、阶段和历史资产，审需求、流程、设计、架构、数据、AI、安全与交付证据，按适用性裁剪。
- [规划Prompt](sources/skillhub/blueprint/MASTER_PROMPT.md)：既有idea-to-blueprint固定快照，逐阶段确认、规划期不写业务代码。
- [Checklist](sources/skillhub/checklist/final-checklist.md)：复用集团现有检查标准，不增加发布凭证。
- [Site取证合同](sources/skillhub/site/SKILL.md)：将目标类型、契约/架构取证和实际工具发现交给原能力；本仓未内置抓取器或浏览器。
- [集团协作合同](docs/INTEGRATION.md)：保留CPO/PM、设计、CTAB、工程、QA及发布主责；Prism维护编排，不复制能力主库。

Python 3.10+，仅标准库。随仓6份源文件按 [UPSTREAM.lock.json](UPSTREAM.lock.json) 锁定；独立使用不需要本机SkillHub目录。源能力更新须先在主库完成再显式升级快照，不自动跟随main。

审计报告可“不通过”或“未知”，AUDIT_ONLY只表示完成报告。修复、原型、付费、外发、生产修改需要各自授权。敏感报告默认放忽略的audits/，不自动上传到本仓。

版本/实测/缺口见 [PROGRESS.md](PROGRESS.md)，范围与验收见 [docs/SCOPE.md](docs/SCOPE.md)。
