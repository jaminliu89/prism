# Product Foundry V0.1 — 可执行产品推演闸门（试验能力）

**目标**：先把产品想清楚，再交给工程 Agent。保护最初意图和各阶段批准基线，新想法先进行变更影响分析，不允许静默扩张范围。

**唯一方法论来源**：本仓固定的 sources/skillhub/blueprint/MASTER_PROMPT.md（阶段 0–6）和 DOCUMENT_CONTRACT.md。源头属于集团 idea-to-blueprint。本工具增加机器流程，不复制另一套产品规划标准。CPO/PM 保留产品方向责任，原工程 QA 与发布权限不变。

## 实际实现的功能

- 建立项目目录：原始点子、阶段0简报、结构化状态与追加事件日志。
- 阶段0记录目标用户、问题、可观察成功标准；全部七阶段各有规定的独立Markdown文件。
- 按阶段提交文档、记录审查和用户确认声明；每次只开放一个待确认阶段。
- JSON版本号与可选的 --expected-revision；独立文档SHA256检查。
- 变更先提出，再接受、延期或拒绝；接受后失效受影响阶段及下游确认，并强制重新提交相关文档。
- 全部阶段确认后导出 .foundry/HANDOFF.json，提供不可变原始目标、阶段决定与文档版本；不自动调用工程Agent。
- Agent 无关的 JSON CLI；只读 MCP stdio 工具 foundry_status 与 foundry_next。

## 安装与第一条实际流程

Python 3.10+，无需第三方依赖；从本仓根目录运行：

~~~sh
python3 scripts/foundry.py --project /tmp/my-product init --idea "帮初学者做简单动画" --actor owner
python3 scripts/foundry.py --project /tmp/my-product next
python3 scripts/foundry.py --project /tmp/my-product answer --key audience --value "初学创作者" --actor owner
python3 scripts/foundry.py --project /tmp/my-product answer --key problem --value "传统动画工具太复杂" --actor owner
python3 scripts/foundry.py --project /tmp/my-product answer --key success --value "首次使用可导出一段短动画" --actor owner
~~~

让 Agent 阅读 next 指向的固定规划合同和文档要求，生成并提交当前阶段文件：

~~~sh
python3 scripts/foundry.py --project /tmp/my-product submit --artifact docs/00-asset-recall.md --file /tmp/asset-recall.md --actor research-agent
python3 scripts/foundry.py --project /tmp/my-product review --verdict pass --kind self_check --actor research-agent --note "已做结构自检；非独立审查"
python3 scripts/foundry.py --project /tmp/my-product confirm --actor owner --statement "确认阶段0当前版本，进入阶段1"
python3 scripts/foundry.py --project /tmp/my-product next
~~~

后续阶段需按 next 提交该阶段要求的全部 Markdown 文件。审查结论：pass / changes / blocked；审查类型：self_check / independent_review。所谓 independent_review 只是记录身份声明，工具阻止同名提交者自签，但无法认证真实人员，不可声称因此发生独立审计。confirm 同样只是用户审批声明；生产环境必须通过外部身份验证和审批UI。

新增功能先提出变更：

~~~sh
python3 scripts/foundry.py --project /tmp/my-product propose --category feature --description "增加作品社区" --rationale "可能提升留存，但增加运营成本" --actor ux-agent
python3 scripts/foundry.py --project /tmp/my-product status
python3 scripts/foundry.py --project /tmp/my-product decide --id CHG-0001 --outcome defer --actor owner --reason "MVP不做，留待验证"
~~~

默认影响映射：intent/audience/problem → 阶段0；research → 1；journey/state → 2；feature/ux → 3；architecture → 4；roadmap → 5；audit → 6。接受变更后需重新提交受影响文档、重新审查确认。暂不具备自动语义影响图；跨领域高风险变更应人为上调审查范围。

全部阶段确认后：

~~~sh
python3 scripts/foundry.py --project /tmp/my-product handoff --actor owner
~~~

导出的任务包始终保留 execution_authorized=false 和 release_authorized=false。工程、费用、发布等行为仍需独立授权。

## MCP 接入

适配 MCP stdio 的客户端可设置：

~~~json
{
  "mcpServers": {
    "product-foundry": {
      "command": "python3",
      "args": ["ABSOLUTE_REPO_PATH/scripts/foundry.py", "--project", "ABSOLUTE_PROJECT_DIRECTORY", "mcp"]
    }
  }
}
~~~

MCP 只能读取固定项目的状态和下一阶段，不能提交文档、确认、改变范围或执行产品代码。实际客户端兼容性、权限及身份尚未逐项 E2E 验证。

## 数据与边界

- .foundry/project.json：项目状态唯一事实源（schema 1）
- .foundry/events.jsonl：追加事件记录，非不可篡改安全审计日志
- .foundry/HANDOFF.json：工程交接约束，非执行授权
- docs/*.md：阶段独立文档

工具没有模型、浏览器、产品生成、正式用户身份认证、多进程写入锁、远程调度和图形界面。建议当前由单一写入协调进程串行调用 CLI，并在每个修改动作指定 --expected-revision。现有单元测试使用合成项目，不证明真实用户研究、外部 Agent 协作和产品质量。

## 测试

~~~sh
python3 -m unittest discover -s tests -v
python3 scripts/prism.py doctor
~~~

V0.2 优先补：真实审批权限、跨进程锁与日志事务、跨Agent接单与回执、细粒度 REQ/US/TASK/ADR 影响图，以及真实产品端到端推演。之后才考虑Web工作台和远程A2A。
