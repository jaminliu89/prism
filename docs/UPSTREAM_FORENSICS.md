# 上游指纹取证（Upstream Forensics）

> Prism 专项方法论：对本地运行的 API / worker 应用，判定其真实上游模型/数据供应商。源自 2026-10-29 Vibe助手 上游取证实战（案例见 `audits/2026-10-29-vibe-upstream-forensics/`，git 忽略）。

## 适用

- 需要查清某个本地工具/IDE 插件/代理背后的**真实模型 API 供应商**。
- 怀疑模型目录标记（如 `owned_by=vertex-ai`）是伪装/占位，需分辨真假。
- 复现某服务前，先摸清它的网关架构与上游链路。

## 分层取证（由易到难，逐层坐实）

### ① 代码层：定位 worker 本体，确认转发目标是否内嵌

- 目标应用是 Electron/桌面应用 → 解包 `app.asar`（`npx asar extract` 或 `@electron/asar`）。
- 在主进程脚本（`main.js` 等）中定位 worker 启动逻辑（搜 `startApiWorker` / `spawn` / `createServer`）。
- 找到 worker 真正执行的脚本（如 `resources/shell.js` / `codexterm.js`），用字符串扫描判断它是**通用 HTTP 代理（undici 打包）**还是**内嵌了模型 URL**。
- 判据：若 worker 是通用代理且**无内嵌模型 URL** → 它只是"本地下发代理"，真实上游在外部网关，需走网络层。

### ② 响应指纹层：识别归一化格式的真身

对 worker 暴露的 `/v1/models` 拉模型目录，并对各池代表模型发 `max_tokens=1` 最小请求，抓响应 usage/字段：

- **OpenAI Chat Completions 旧字段**：`prompt_tokens` / `completion_tokens` / `total_tokens`。
- **OpenAI o3/gpt-5/Responses API 指纹**：`accepted_prediction_tokens` / `rejected_prediction_tokens`（投机解码）+ `input_tokens` / `output_tokens` / `reasoning_tokens`。
- **Google Vertex/Gemini 原生**：不会返回上述 OpenAI 风格 usage。
- **关键判据**：若模型目录统一标 `owned_by=xxx`，但响应是另一家的 usage 指纹 → **`owned_by` 是网关统一硬标记/伪装，不是真实上游证据**。
- 多池模型（GPT + Claude + DeepSeek）返回**同一种归一化格式** → 典型 one-api/new-api 类聚合网关。

### ③ 网络层：绕过本地代理，抓真实出站目标

- 本机若开了全局代理（fake-ip，DNS 全返回 198.18.x）→ **关闭代理**，或用 `--noproxy '*'`、DoH 绕过。
- `lsof -nP -p <worker_pid> -iTCP`（worker 可能多进程，取监听目标端口的进程及其父进程）抓 ESTABLISHED 出站连接。
- 对该 IP 定身份：`dig` 反查（CNAME）、`ipinfo.io/<ip>/json`（归属/ASN）、`openssl s_client`（默认证书 CN，识别 CDN 泛签如 `*.cdn.myqcloud.com`）。
- 判据：worker 出站目标 = 网关域名真实 IP；托管在 CDN（如腾讯云）→ 真实模型供应商在**回源侧**，本机不可见，这是取证边界。

### ④ 落账

- 结果写 `audit.json`（含 evidence + sha256 + cases + findings），用 `python3 scripts/prism.py verify-report <abs>/audit.json` 校验。
- `resolved` 的 finding 必须带 `retest_evidence`（observed 证据列表）。
- 敏感取证结果放 `audits/`（git 忽略），不提交污染仓库。

## 工具

- `scripts/probe_upstream.py`：curl-based 上游指纹探测（内建 `--noproxy '*'` 规避本机代理、`max_tokens=1` 最小消耗、支持 `--catalog` / `--sample` / `--json`、SSE 解析、分池归类）。

## 边界声明

- 真实供应商位于网关 CDN 回源侧时，本机无法唯一点名单一云厂商；应诚实标注边界，不猜测。
- 全部只读取证；不访问未授权目标、不运行被审计代码的命令、不保存敏感凭证（token/激活码需脱敏）。
