# 集团现有工具协作合同

本协议把集团现有工具组合成任务工作包；根 Registry 决定主责，本协议不注册平行项目控制面。机器可读分工见 [tool-collaboration.json](tool-collaboration.json)，它是协作合同而非已部署的自动执行器。

## 按目标分工

| 目标 | 优先候选 | 交接给下步的证据 |
|---|---|---|
| 批量清点页面、资料、文案与结构化数据 | Crawl4AI 优先；Scrapling 作为可验证替代 | URL清单、原始HTML、Markdown/JSON、失败项 |
| 价格、商品目录、表格、精确字段与页面结构变化 | Scrapling 优先；Crawl4AI 结构化提取作为替代 | URL与原始HTML/快照、字段Schema、JSON/CSV、选择器/来源与失败项 |
| 探索未知入口、多步操作与页面状态 | browser-use；宿主允许的原生浏览器或Playwright | 实际操作日志、前后状态、发现的路径与阻断 |
| 固化流程、抓取运行时证据与复验 | Playwright；集团既有web-clone脚本 | 明确断言、trace、截图、网络/控制台、回归结果 |
| 实现与修复视觉 | 集团设计部门选用frontend-design、Impeccable等 | 设计理由、令牌、实际组件与同视口对照 |
| 源码/API/架构审计与归档 | REA、工程工具箱、设计部门、Connector OS | 源码/日志定位、发现、架构图、摘要和读回 |

Crawl4AI 也支持结构化抽取，Scrapling 也能批量爬取及输出 Markdown；分工按当前证据目标选首选与备用，而不是排他性能力。Crawl4AI也有动态页面能力，Playwright也能探索；表中按主要目的分工，不制造绝对技术边界。按缺口选择最少工具，不要求每项任务把全部工具跑一遍。现有web-clone若已封装Playwright则直接复用脚本。单页明确用例可直接Playwright；批量资料研究无需硬接视觉设计；非网页目标按本体类型规则改用现有原生分析工具。

## 双采集引擎选择与失败切换

- 文档、FAQ、文章、多页面 Markdown 归档：优先 Crawl4AI；精准字段、商品目录、价格或易变选择器：优先 Scrapling。先验可用性与版本，二者均可作为对方经过实测的替代。
- 输出共同包含 task_id/target/revision/case_id、原始 URL、采集时间、原始HTML或快照引用、sha256、字段Schema及状态；无法取得原件时写 PARTIAL，不凭一段 Markdown 或 JSON 声称目标全站完整。
- 同法失败最多两次就切换观测面或备用引擎。备用仍须满足原出口判据；不把 HTTP 200 当字段正确、不把 MCP 工具已登记当成功运行。
- 遵守站点授权、robots/条款与合理速率。不借切换引擎绕过访问权限、验证码或反爬限制；出现门控先报告 BLOCKED 及合法后续条件。
- `tool-collaboration.json` 的 selection_rules 供 Prism 的任务路由器使用；它只决定候选顺序，不授权安装、联网或数据外传。

## 开工与交接

1. 先恢复任务、验收条件、目标版本、现有资料和工具能力；把用户说明已有与当前会话实测可用分别记录。通过Connector OS发现接口并做最小适用探活；不因工具库有名字就重装MCP或调用云端付费版。
2. 按采集、探索、实现/修复、复验、归档选择适用工作包。每包明确目标、输入证据、选用工具及理由、出口判据和失败替代路线。流程已知时跳过重复探索。
3. 所有工具共享同一task_id/target/revision/case_id证据索引。交接记录工具接口和版本、时间、证据路径与sha256、SOURCE/PARTIAL/GUESS、脱敏说明及next_condition；缺失项显式说明，不能伪造原始记录。
4. browser-use发现路径后，将关键路径交Playwright或宿主认可的可重复操作接口重放并断言。浏览器智能体“完成”摘要不能代替真实结果。Crawl4AI的提取文本关联原始URL/HTML，不证明整个用户流程成功。
5. 同一浏览器会话仅一个写入者；并行读取使用隔离上下文。按当前宿主浏览器规范执行，不擅自迁移cookie/token或绕过原生接口。原始网络证据可能含敏感字段，归档前脱敏；保留受控原件引用。
6. 同法失败两次后换观测面、引擎或层级，写原因；替代工具满足同一出口条件才算替代成功。未满足则明确blocked及下一条件。
7. 修复由当前工程负责人承接，同版本回归；独立QA与正式交付继续走现有合同。最后保存架构证据、发现、修复/未验证项与归档读回。

## 视觉目标先定

- faithful_clone：原站已观测事实和批准范围决定视觉与交互；frontend-design只帮助工程实现和细节质量，不擅自换字体、配色、布局或叙事。
- redesign：用户批准的产品范围及DESIGN.md优先；设计部门按需选一个主设计方法，再由工程实现和Playwright复验。
- audit：对照已有需求/设计审查；只有修复获授权才改页面。截图相似不证明API链通过，自动断言通过不证明审美获批。

## 设计来源

用户参考：https://collectivebrain.de/en/skills/anthropic-frontend-design/ 。它是Collective Brain整理的精简改编，不能标为Anthropic官方完整快照。
官方方法：https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md ，本轮核对Git blob `a5333457c414d20d625f307df945842c0952ecc3`。使用前核对当前授权源及其LICENSE.txt；此处只记录来源和方法分工，不复制重许可上游正文，不声称已安装。
设计部门既有四工具与LOCK不变；按现有入口调用，避免全量叠加冲突提示词。

## 验证边界

规则/JSON检查只证明合同一致。当前登记不证明本机已安装browser-use/Crawl4AI、模型凭据可用、浏览器可连接或某目标审计完成。真实项目执行时保存探活、实际用例与复验产物，才能报告对应能力已验证。
