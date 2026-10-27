# CodeGraph 可选代码证据适配器

状态：**可选接入**。适用 Prism 工程审计、Product Foundry 工程交接后的代码影响分析。无需另建一级 Skill，不改变原 Group Registry 或发布/QA 主责。

## 约束

- 默认不执行；需要 `--allow-local-codegraph`、明确项目目录、改动文件和 CodeGraph 二进制路径。
- 只调用已安装的 `codegraph affected`，不会安装、运行 `codegraph install`、创建索引、修改全局 Agent 设置或发送源码到 LLM。
- 对第三方进程强制设置 `DO_NOT_TRACK=1`、`CODEGRAPH_TELEMETRY=0`、`CODEGRAPH_NO_UPDATE_CHECK=1`。这不是网络沙箱；敏感私有仓库使用前必须另行部署实际 egress 隔离及供应链审计。
- 不收集源码文本，不开放私有 Prompt、编排结构或路径以外的内部内容。拒绝目标目录之外的改动文件、符号链接越界、`.env` 等敏感路径；拒绝第三方工具输出的绝对或越界路径。
- 返回 `STATIC_CODE_IMPACT_CANDIDATES_ONLY`，`graph_freshness=NOT_VERIFIED`。**不得据此批准发布、断言源码不可逆向或认为依赖图无漏报。**

## 已有隔离索引上的调用方式

假设你已在一个**明确获准的沙箱项目中**通过独立步骤创建 CodeGraph 索引，且已审查安装包：

```sh
python3 scripts/prism.py codegraph-impact \
  --repo /absolute/path/to/authorized/sandbox-repo \
  --changed src/core.mjs \
  --codegraph-bin /absolute/path/to/pinned/codegraph \
  --allow-local-codegraph
```

执行结果包含变更文件、候选关联测试、响应 SHA256、局限性和未授权发布的声明。它**不执行**返回的候选测试。若想在 Product Foundry 工程任务中使用，让工程/QA Agent 从该 JSON 读取候选，实际跑测试后将结果与原产品需求、变更事件、CI 证据交叉核验。

## 主责分工

| 角色/资产 | 职责 |
|---|---|
| Product Foundry | 原始意图、规格、设计决策、变更确认 |
| CodeGraph provider | 已授权索引中的静态受影响测试候选 |
| Prism | 将这些候选作为工程证据线索；不代替真实核验 |
| QA / delivery-walkthrough | 执行相关测试、反向验证、最终验收 |
| Connector OS | 管理外部执行器版本、网络权限和供应链 |
| Axiom / Knowledge OS | 沉淀跨项目验证经验 |

## 自测

```sh
python3 -m unittest discover -s tests -v
python3 scripts/prism.py doctor
```

GitHub CI `.github/workflows/codegraph-eval.yml` 还会用固定 CodeGraph 1.6.2 的隔离合成样本运行真实 Provider 接口，并检查 Python / JavaScript 直接与间接依赖。CI 通过只证明该固定测试范围；正式私有编排层接入仍需安全审计、网络隔离、授权和动态调用覆盖试验。
