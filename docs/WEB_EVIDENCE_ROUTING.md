# Prism Web Evidence Router：Scrapling × Crawl4AI

本文件只是目标驱动编排层。集团 SkillHub 根 Registry 是权限/所有权权威；本仓 `sources/skillhub/site/tool-collaboration.json` 是固定版本的选择合同，不创建独立抓取器。

## 选择与执行
- 多页文档、FAQ、文章、Markdown → Crawl4AI 首选，Scrapling 备选。
- 商品、价格、列表、易变 DOM 的字段提取 → Scrapling 首选，Crawl4AI 结构化提取备选。
- 未知点击流程 → browser-use/EgoLite 等由宿主授权使用；稳定回归 → Playwright。
- 执行 `python3 scripts/web_evidence_router.py route --intent bulk_document_to_markdown` 或 `--intent stable_fields_prices_catalogs` 得到候选顺序。待 Connector OS/当前宿主实际验证候选后，可加 `--host-verified crawl4ai scrapling` 重算；此参数是宿主声明，不证明探活。
- 真实抓取由已经发现/授权/探活的 Python、CLI、MCP 引擎实施，Prism 本地脚本**不安装、不抓取、不认证工具**。
- 解析失败两次再切换，示例：`python3 scripts/web_evidence_router.py fallback --intent stable_fields_prices_catalogs --engine scrapling --attempts 2 --failure schema_mismatch`。备用仍须满足原出口判据。访问被拒、robots、站点策略一律 BLOCKED，不跨引擎绕过。
- 真实结果要求保存 task_id、target、revision、case_id、URL、时间、原始 HTML/快照、Markdown/JSON/CSV、失败项与 hash。调用 `python3 scripts/web_evidence_router.py verify-evidence --record evidence.json --artifact-root ./evidence` 检查本地证据文件和 hash；它不验证语义真伪。
- 输出交 CIO、REA、产品、QA 等原有 PRIMARY，遵守现有 session 只有一个写入者、最小权限、网站授权和用户数据脱敏。

## 边界
路由和证据检查的离线测试通过不代表抓取器已安装、浏览器可操作、源站允许采集或某个商业结论已核验。真实场景需在当前宿主单独留存探活与可复现目标用例。
