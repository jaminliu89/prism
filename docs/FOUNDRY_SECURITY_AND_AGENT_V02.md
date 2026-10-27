# Product Foundry V0.2｜主动安全推演与多 Agent 文档任务合同

状态：候选实现；沿用集团原有 idea-to-blueprint 阶段0–6。新增安全设计控制与 Agent 文档协作协议，仍不自动调用模型、不执行目标代码、不对第三方扫描。

## 目标

用户只有一句点子时，主动提醒两个维度：产品是否解决正确问题；产品如何抵御非授权访问、敏感数据泄漏、提示词/编排逻辑暴露、工具权限越界和成本滥用。防守重点不是藏住前端接口名字：浏览器、已下发脚本、公开下载包和可访问 API 响应可被合法分析。必须让私有编排、模型决策和凭证留在可信边界内，并通过服务端权限与资源约束保护结果。

“CTF难度”和“逆向难度”不是可凭想象打出的安全分。必须先声明攻击者类型、具备的访问权限、目标资产、时间与可使用工具，再在己方授权的隔离环境记录是否达成、耗时、复现步骤及修复复测。设计阶段一律报告 NOT_MEASURED，不把代码混淆、前端静态扫描或项目保密当安全证明。

## 从点子触发威胁推演

创建项目后执行：

~~~sh
python3 scripts/foundry.py --project /tmp/my-product next
python3 scripts/foundry.py --project /tmp/my-product security-status
python3 scripts/foundry.py --project /tmp/my-product security-draft > /tmp/security-draft.md
~~~

即使阶段0，next 也会给出安全问题：核心资产、部署与客户端边界、可能的攻击者、信任边界、安全目标。当前安全档案在项目私有 .foundry/project.json；不要粘贴真实Token、system prompt全文或算法源码，只记保护对象的类别。

记录档案：

~~~sh
python3 scripts/foundry.py --project /tmp/my-product security-profile --key protected_assets --value "服务端多Agent编排及私有路由策略" --actor owner
python3 scripts/foundry.py --project /tmp/my-product security-profile --key deployment_boundary --value "前端仅渲染公开状态，核心调度在私有服务端" --actor architect
~~~

其他必填档案项：attacker_capability、trust_boundary、security_objective。

每项威胁都必须被实际评估（mitigate 或有理由的 not_applicable；中低风险可明确 accept_risk 并保留剩余风险）。例：

~~~sh
python3 scripts/foundry.py --project /tmp/my-product security-assess --code ORCHESTRATION_EXPOSURE --disposition mitigate --reason "编排是需要保护的商业资产" --actor security-architect --asset "私有任务编排" --boundary "客户端到服务端" --attack-path "浏览器包与公开接口响应" --control "编排和策略仅由服务端执行，前端只读有权限的结果" --verification "隔离测试环境检查构建文件、API与导出产物是否泄漏编排细节"
~~~

命令记录设计和预期测试，不真的抓取网站、解析包、渗透目标。高风险未评估、风险擅自接受、缺关键档案会阻止阶段4确认。设计修正后既有安全模型文件的提交与审查失效，需要重交重新确认。

主要威胁清单：

| 项目 | 为什么重要 | 工程方向 |
|---|---|---|
| ORCHESTRATION_EXPOSURE | 客户端/日志暴露内部工作流 | 核心私有编排只在服务端；最小化响应 |
| API_AUTHORIZATION | 越权访问项目、身份、额度 | 对象级/功能级服务器授权与隔离 |
| AGENT_TOOL_BOUNDARY | 提示词注入与越权工具执行 | 最小权限、工具参数校验、人工审批 |
| SECRETS_AND_LOGS | 密钥/业务提示词/日志泄漏 | 私有凭证、脱敏、访问与保留控制 |
| SANDBOX_ISOLATION | 代码运行触达宿主或其他项目 | 沙箱隔离、egress限制、配额 |
| SUPPLY_CHAIN | 来源不明的Skill、依赖和插件 | 许可证、版本锁定、来源与哈希 |
| RESOURCE_ABUSE | API滥用、重试账单失控 | 限流、幂等、成本预算、取消 |

参考标准：OWASP ASVS 5.0.0、OWASP API Security Top 10 2023、OWASP LLM Top 10 2025。标准用于设计与检查计划，不代表已逐条符合。Site Clone 的 project-audit 与授权取证能力可在后续交付阶段独立调用；此工作台不得用规划权限自动启动逆向或CTF测试。

## 阶段合同的最小增量

集团规划方法论仍然唯一源于 idea-to-blueprint。本轮只增加：

- 阶段0：next 主动暴露安全问题，暂不阻止普通点子澄清。
- 阶段3：提醒设计人员定义敏感状态、权限边界和异常流。
- 阶段4：强制文档 docs/04-security-threat-model.md，加上完整安全档案与每项威胁的设计处置；不完成不能确认。
- 阶段6：强制 docs/07-security-acceptance-plan.md，明示尚未运行的验证、上线前必要检查、责任人和剩余风险。
- HANDOFF.json：包含设计评审结果，并明确 runtime_security_verified=false、reverse_engineering_difficulty=NOT_MEASURED。

修改安全决策后，相关文档标记失效；已确认阶段4之后若需重新评估，先提出 architecture/security 变更并按原有机制退回。

## 适配不同 Agent 的同一条任务合同

用户/宿主明确选择任务后可创建：

~~~sh
python3 scripts/foundry.py --project /tmp/my-product task-assign --role research --artifact docs/00-asset-recall.md --objective "回收现有历史资产并区分证据与假设" --actor owner
python3 scripts/foundry.py --project /tmp/my-product task-claim --id AGT-0001 --actor researcher
python3 scripts/foundry.py --project /tmp/my-product task-deliver --id AGT-0001 --file /tmp/asset-recall.md --actor researcher
python3 scripts/foundry.py --project /tmp/my-product tasks
~~~

角色受限于 pm / research / ux / architect / security / qa；只能给当前开放阶段中约定的文档派任务。输出任务包含任务ID、负责视角、目标、单一可写文件、禁止动作、来源文档与版本。未交付任务会阻塞该阶段确认。接受重大变更时，旧任务自动取消，防止 Agent 继续交付旧版本。没有实际身份验证，actor仍是客户端声明；不能把两种标签冒充两个真人独立验收。

共享读取入口：

~~~json
{"mcpServers":{"product-foundry":{"command":"python3","args":["ABSOLUTE_PRISM_PATH/scripts/foundry.py","--project","ABSOLUTE_PROJECT_PATH","mcp"]}}}
~~~

只读 MCP 新增 foundry_security / foundry_tasks，均只传必要状态或任务元数据，不开放安全档案明文、审批、文档写入或敏感文件读取。真正执行 Agent 和审批仍需宿主明确授权，CLI 对本地写权限无身份校验。

## 安全验收与尚未做到

这次的“安全设计就绪”仅表示声明的威胁被逐项处置且有防护/验证计划，不能变成“产品安全”结论。后续工程必须补充：

1. 正式身份系统与授权审批、跨进程事务锁、租户级文档和任务隔离。
2. 源码/构建产物泄露检测、服务端对象权限负测、工具注入模拟、沙箱隔离及密钥泄露检查。
3. 针对私有编排的授权逆向评估：明确可观察面、攻击目标、时间预算、成功条件、证据及修复回归。
4. 独立安全审查人绑定实际身份与版本、发布前残余风险签批；不能由任务提交者自己审计自己。
5. 模型驱动追问/自动研究仍未接入，需经源与权限审查后接现有 Agent Runtime，不另造一套隐藏路由。

现阶段的远端CI测试仅覆盖状态和拒绝路径的合成数据，不代表产品安全或真实 Agent E2E。
