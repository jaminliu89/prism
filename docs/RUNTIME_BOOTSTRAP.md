# Prism Runtime Bootstrap｜运行时自动补齐与部署

2026-10-29 · 独立工具入口 `scripts/runtime_bootstrap.py`，不新建 Agent / 控制面。只有当前真正可操作宿主能安装和部署。集团工程所有权仍在 Engineering Agent OS / Connector OS，Prism 负责目标编排和证据回传。

## 触发：什么时候自动介入

当明确运行 Prism **Mission**（CTF/Hackathon/Dev/REA/明确实现）且一个必要程序、包或预览入口缺失时，Agent 应自动进行：
`识别任务需求 → 检查系统/项目版本与锁 → 最小安装方案 → 风险判定 → 有界执行 → 再探活 → 记录命令版本/输出摘要 → 接续原 Mission`。

- `planning`、普通 `audit`、只读 `doctor`、`plan`：**仅检查**，不得因为发现缺依赖而执行安装或对外部署。
- Mission 已经获准编写/运行工程代码时：可自主进行**低风险、项目范围内**的准备，但实际 CLI 操作仍需在当前宿主传入本次明确 `--allow-project-install`。支持本地隔离 Python venv，以及具有 `package-lock.json` 的 `npm ci --ignore-scripts`。联网下载另需 `--allow-network`，不执行依赖的 postinstall 脚本。
- macOS 上缺少固定白名单内的程序时：可提出 Homebrew 安装；真正改动用户宿主须另经实际执行者确认并传入 `--allow-host-install --allow-network`。无 brew、Linux 上需 sudo/apt、系统权限不足则 BLOCKED，由当前宿主选择已获授权的正规路径。不得默默 curl|sh、提权、改系统代理或安装 CA。
- 本地静态预览：在构建输出存在的前提下可显式 `--allow-local-preview` 开启 `127.0.0.1` loopback 并探活，返回 `LOCAL_PREVIEW_HEALTHY`，**不证明线上已发布**。
- Vercel 非生产预览：必须已有 `.vercel/project.json` 链接、已安装 `vercel` CLI、已有可用账号；**只有此次目标明确批准外发/可能费用**才传 `--allow-remote-preview --allow-external-publish --allow-network`。脚本使用 `vercel deploy --yes`（没有 `--prod`），返回退出状态，不输出凭证，不声称线上 URL/浏览器已经核验。对于其他平台，通过 Connector OS/部署原 owner 的现有受控工具与文档，不凭想象尝试通用 shell 命令。
- 正式生产、付费服务开通、域名/DNS、数据迁移、用户数据、密钥授权、修改CI机密、未经批准的外部 API 消费不能仅凭“使用 Prism”获得许可。

**注意**：这不是沙箱。项目锁文件、第三方供应链、Homebrew 程序及工程代理都需进行来源审查；`--allow-` 是本机宿主声明，不等于人类身份认证，也不保证零费用。工具执行期间不输出 stdout/stderr 原文；记录摘要而非私密内容。不自动调用任意 `package.json` script、安装未知 MCP server 或运行第三方 README 中的命令。

## 使用

先由 Agent/宿主从实际任务提炼需要的工具，默认只做计划：

```sh
python3 scripts/runtime_bootstrap.py plan --project /absolute/project \
  --tool tshark --tool node --setup python-venv --setup npm-ci --npm-path web
```

获准的项目依赖准备（先冻结锁文件、审查依赖，避免 `npm-ci` 与现有脏的 `node_modules` 冲突）：

```sh
python3 scripts/runtime_bootstrap.py apply --project /absolute/project \
  --setup python-venv --setup npm-ci --npm-path web \
  --allow-project-install --allow-network
```

缺 Wireshark CLI 的 macOS，确认 Homebrew 可用且有本轮宿主级授权：

```sh
python3 scripts/runtime_bootstrap.py apply --project /absolute/project \
  --tool tshark --allow-host-install --allow-network
```

本地静态预览（`web/dist` 已由可信 build 生成）：

```sh
python3 scripts/runtime_bootstrap.py apply --project /absolute/project \
  --preview local-static --artifact web/dist --port 8775 --allow-local-preview
python3 scripts/runtime_bootstrap.py stop-preview --project /absolute/project
```

如系统无法确认 PID 所属进程，stop-preview 不会强行杀死未知进程，应由宿主安全停止。运行数据 `.prism-tools/` 必须排除版本控制、备份与上传；该目录可能包含本地依赖、日志和 PID，建议项目加入 `.gitignore`。

已有 Vercel 预览项目在完成目标/费用/外部访问授权后：

```sh
python3 scripts/runtime_bootstrap.py apply --project /absolute/project \
  --preview vercel-preview \
  --allow-remote-preview --allow-external-publish --allow-network
```

上线后仍按既有 delivery-walkthrough / QA 责任去获取可访问 URL、构建 SHA、真实浏览器 E2E、回滚点。仅出现 `DEPLOY_COMMAND_EXITED` 不代表已部署成功、网络可达或用户已验收。

## 工作闭环与失败策略

- 依赖存在就复用，禁止无故重装或重启用户程序；版本兼容性仍须在本次工程验证。
- 项目内准备使用固定、最小版本范围；`npm ci` 的 lock 哈希仅证明输入身份，**不证明供应链安全**。
- 如果项目已有正在运行的服务或用户数据，禁止覆盖和强杀。无同环境验收证据则保持 `UNKNOWN`。
- 工具缺失但无所需授权 → `APPROVAL_REQUIRED/BLOCKED`，不将其表述为“已自动补齐”。
- 命令退出码 0、预览 HTTP 200、Vercel CLI 成功是不同层次的证据；后续任务必须继续采集应用功能证据。
- 出现不稳定安装时停止自动重试，保存日志/步骤，先恢复原现场并交当前 owner。
- CI 测试只包含合成 fixture 和本地 venv/loopback，不使用真实 GitHub/Vercel 凭证、系统 Homebrew 或付费部署。

## 角色合同

| 责任 | 主责 |
| --- | --- |
| 根据 Mission 判断缺少哪些能力 | Prism / 当前 Host Agent |
| 工具来源、版本、权限、供应链 | Connector OS / CTAB / Security |
| 项目内受控安装 | 当前获准开发宿主 |
| 预览发布和运维/回滚 | 既有 Deployment / Connector owner |
| 功能安全复验及发布放行 | Engineering Quality OS / delivery-walkthrough |
| 复用成功案例、失败边界、版本经验 | Axiom / Knowledge OS |

本功能适用于目前可用的本地/联网执行环境。仅将文件推送到 Prism 仓库不代表你的 Mac、其它 Agent、部署账户已经在运行它。
