# Product Foundry V0.3 最小工作台

2026年10月27日。本机试验工作台，非远程 SaaS。Python CLI/阶段方法论保留；前端按用户授权新增 React、Vite、Tailwind v4 和官方 shadcn/ui。没有更换模型或模型服务。

## 启动

在 Prism 仓库根目录：

```sh
npm ci --ignore-scripts --prefix web --registry=https://registry.npmjs.org
npm run build --prefix web
python3 scripts/foundry_web.py --workspace /absolute/private/foundry-projects --port 8773
```

打开 http://127.0.0.1:8773 。workspace 必须是用户自己的本地私有目录。新建项目保存在该目录中随机ID子目录；不把点子、文档和真实答案提交到仓库。既有 CLI 项目可显式挂载：

```sh
python3 scripts/foundry_web.py --workspace /absolute/private/foundry-projects --project /absolute/existing-cli-project --port 8773
```

工作台写入同一份 .foundry/project.json、事件日志和 docs，CLI 可以读回。请使用单一写入进程，不要并行从 CLI 和网页修改同项目；已有 CLI 尚无跨进程事务锁。只读挂载尚未实现。

开发时 `npm run dev --prefix web` 监听构建文件变更，仍通过 Python 同源服务查看，避免把开发代理当正式权限层。Node 22.12+，Python 3.10+；本轮实测 Node 22.23.2。锁定依赖见 web/package-lock.json。

## 可执行主流程

1. 新建点子，保留原始意图。项目/阶段左栏导航；刷新恢复最近项目。
2. 在阶段0分别填写三项答案并保存；本机记录人声明为“本机用户”。
3. 打开本阶段文档，编辑Markdown正文并提交；基础预览仅解析标题和段落，其他Markdown语法显示原文，不执行HTML。
4. 在讨论区新建议题、手动录入角色/立场/理由/依据/反例，再由负责人裁决。没有反方/质疑意见时沿用原后端拒绝逻辑。
5. 记录当前阶段自检结论和依据。满足全部后端门禁后，显式填写确认声明并进入下一阶段。
6. 阶段4的完整安全档案/威胁评估、任务领取与交付、变更提出与接受、工程交接继续使用 V0.2 CLI。本工作台显示门禁/未决变更，不自动代填或绕过。

没有生成文档、研究、角色意见或模型输出的自动执行器。不把手动输入或测试夹具称为真实专家履职。确认和审查是未认证声明，非正式身份审批。

## 接口与权限边界

scripts/foundry_web.py 是 Python 标准库 HTTPServer 适配，不复制阶段状态机。GET /api/projects 读目录；GET /api/projects/:id 读当前状态；GET /api/projects/:id/document?path=… 只读原阶段合同允许文档；GET /api/sources 读固定来源锁。POST /api/projects 创建；POST /api/projects/:id/actions 仅允许 answer/submit/review/confirm/panel-open/panel-opinion/panel-resolve。

- 服务只绑定 127.0.0.1，校验精确 Host，拒绝跨 Origin，写请求要求启动时随机 token；token 只在同源 session 响应与浏览器内存中，不写入文件/日志。无 CORS。防本机浏览器跨站写入，不等于用户认证，不能暴露公网或不可信反向代理。
- 随机项目ID限制在显式 workspace，路径与文档白名单检查复用 foundry.file_under；不能通过API读取任意宿主文件或指定任意写路径。显式 --project 属于用户授权挂载本地项目。
- 每次写入必须带整数 revision，调用原 foundry.check_rev 和各动作门禁。服务器串行处理自己的请求；不能解决原CLI的跨进程写入竞争。
- JSON请求上限256KiB，禁止未知动作。前端不使用 innerHTML，Markdown内容转义；构建静态文件限制在web/dist。
- 不开放 shell、MCP写入、模型调用、网络抓取、工程执行和发布接口；security资料不会被自动发往外部服务。
- 同一操作系统用户能直接访问本地文件与API；安全设计不是租户隔离、正式身份系统或不可篡改审计日志。

## 工程文件与检查

- web/src/App.tsx：三栏与业务交互；types.ts：受限浏览器响应合同。
- web/src/components/ui：官方 CLI 生成组件；index.css：设计变量与响应式编辑台。
- scripts/foundry_web.py：同源本机适配与动作白名单。
- tests/test_foundry_web.py：真实 HTTP 持久化/版本/路径/跨站拒绝与门禁。
- web/tests/workbench.spec.ts：Chrome真实UI主链路、刷新恢复、争议拒绝、未保存保护、键盘与三视口。
- DESIGN.md：候选设计系统；docs/verification/foundry-v03/：最终检查与独立审查范围。

```sh
python3 -m unittest discover -s tests -v
python3 scripts/prism.py doctor
npm run build --prefix web
npm test --prefix web
```

浏览器测试使用独立合成项目目录和端口8774，不修改真实项目。当前 Playwright 配置使用 macOS Google Chrome 路径；其他系统须在测试配置中明确选择可用浏览器。构建后的UI启动不需要测试浏览器。

## 回退与未完成

停止本机适配进程即可回到原CLI；未修改 foundry.py、guard/panel、上游快照。保留项目私有目录，不自动删除数据。本轮不部署、不合main、不注册新集团方法论；源码通过隔离分支交付。身份认证、跨进程事务、真实外部Agent执行、完整Markdown渲染/富文本与安全档案表单不在本轮最小工作台范围。
