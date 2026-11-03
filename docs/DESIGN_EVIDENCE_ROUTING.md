# 设计证据路由（Design Evidence Routing）

**归属**：CTAB 定方法并执行，Security 审安全结论，Group Asset Governor 决定哪条发现进 Golden Stack。回写归 Archivist。
**版本**：2026-11，基于 30 个参考站点实测（`sources/design-evidence/site-probe-2026-11.tsv`）

Prism 在这里不做设计审判。只做三件事：取证、判读、移交。视觉复刻、品牌定稿、发布授权都不在 Prism 内。

## 何时触发

- 用户给一批网址，要求「吸收审美」「看底层规律」「这些站什么选型」
- 新产品的设计系统选型（token 体系、字体策略、payload 预算）
- 竞品站的交付方式取证（自托管还是 CDN、第三方域数量）
- Site Clone 之前的基线取证：先确认对方是什么栈，再谈复刻

## 不触发

- 单个浏览器扩展拆包 → `browser-extension-recon`
- 原生包体（DMG / PKG / APK / asar / EXE）→ `software-artifact-forensics`
- 只要视觉风格提取、不关心技术栈 → `html-style-recon`

## 工具选择

| 需求 | 工具 | 判据 |
|---|---|---|
| 批量存活与源站 | `curl -sI`，8 worker 并行 | 看回源 `server` header；Cloudflare 在前 ≠ 托管在 CF |
| 框架指纹 | 抓 HTML 存盘后正则 | 硬路径优先，字符串命中只是线索 |
| payload 判读 | HTML 字节 + css/js 计数 + 第三方域计数 | 看 HTML 里有没有真实正文，不看字节数 |
| 设计系统 token | 抽 `:root` 与 `[data-theme]` 块 | 看 token 命名体系，不看截图 |
| Cloudflare challenge 站 | 真浏览器会话（ego-browser） | curl 403 时不要猜，换会话重测 |

串行 curl 三十站必超时。单站 18s 上限，失败的照常进表标 `blocked`，不从结果里静默丢掉。

## 三条判读硬规则

**硬路径优先。** `_next/` `_astro/` `/_nuxt/` `_app/immutable` `data-wf-page` `wp-content` `wixstatic` `/assets/index-*.js` 是硬证据。`tailwind` `webflow` `squarespace` `contentful` 这类词在正文、注释、竞品对比页里都会出现，单命中不能定性。实例：`payloadcms.com` 命中 "Contentful" 是因为首页有 `Payload vs Contentful` 对比文案，它自己没有用 Contentful；只有 `_next/` 是对的。

**403 / WAF 拦截写未知。** Cloudflare 403、Sucuri 307、AWS 202 + 0 字节，都是「无法判定」。结论栏必须写 `blocked`，不能写「没有框架」。

**Cloudflare 在前 ≠ 托管在 Cloudflare。** `server: cloudflare` 只说明前面挡了一层；`nginx` / `Apple` / `awselb` / `Vercel` 才是源站线索。

## token 指纹表

| 特征 | 设计系统 |
|---|---|
| `--color-base-00..100` / `--background-primary` / `--interactive-accent` / `--metadata-*` | Obsidian |
| `--tw-*` | Tailwind |
| `--p-*` | PrimeNG |
| `--mdc-*` | Material |
| `--radix-*` | Radix / shadcn |
| `--paper` / `--ink` / `--rule` / `--band` | 纸墨系自研（qiaomu 类） |
| `--bg` / `--fg` / `--surface` / `--border` | shadcn 默认 / Vercel 系 |
| `--surface` / `--line` / `--signal` / `--ink-2..4` | Parchment 4.0 |

发现自己拼凑却「异常精细」时先怀疑移植。三条可查证据：token 前缀、仓库里残留的他人工程元数据（`*.xcodeproj/xcuserdata/<别人的名字>.xcuserdatad`）、`DESIGN.md` / `CLAUDE.md` 里写明的参考系。

深浅主题若是「两套完整 base 映射 + 语义别名」而不是简单反色，说明这是成熟设计系统。

## payload 判读：极简 ≠ 小

payload = 网络传输的有效载荷。三层含义不要混：页面 payload（首屏 HTML + CSS + JS + 字体）、API payload（请求体 JSON）、Agent payload（一次请求塞进模型的指令）。

页面层有两种假象：

| 现象 | 实例 | 真相 |
|---|---|---|
| HTML 5–9 KB | `studio.nxcode.io` 5 KB、`tempo.new` 8.4 KB | SPA 空壳，`<div id="root">` 里什么都没有。HTML 小 ≠ 首屏小，反而更慢 |
| HTML 1 MB+ | `linear.app` 1.26 MB + 46 个 CSS | Server Components 流式直出，首屏内容已在里面。看着臃肿其实更快 |

判据：看 HTML 里有没有真实正文（`<h1>` 文案、段落文本），不看字节数。

## 实测基线（2026-11）

完整数据：`sources/design-evidence/site-probe-2026-11.tsv`。以下为可复用的部分：

| 站点 | 栈 | 托管 | 第三方域 | 备注 |
|---|---|---|---|---|
| apple.com | 自研 + 自有 CDN | Apple | 3 | JS 按模块拆 `*.built.js` |
| linear.app | Next.js | Cloudflare | 4 | 46 个 CSS，服务端直出 |
| payloadcms.com | Next.js（**webpack**，turbopack 计数 0） | Vercel | 10 | 官网自托管 Payload：`/api/pages|posts|users|media` 全 200 |
| hermes-agent.nousresearch.com | Next.js + Turbopack | Vercel | 6 | 字体含 `AeonikFonoProTRIAL-Regular`（商业字体试用版） |
| arena.ai | Next.js + Turbopack | Cloudflare + Turnstile | 5 | curl 403，须真浏览器会话 |
| awwwards.com | Webflow | nginx | 20 | GSAP + Lottie + Three.js |
| muuuuu.org | WordPress | Vercel 前置 | 103 | Lottie |
| studio.nxcode.io | Vite SPA 空壳 | Cloudflare | 1 | 5 KB HTML |

## 七条可复用规律

每条都挂实测数字，不写形容词。

1. **第三方域数量决定观感档次，不是 CSS 技巧。** apple 3、awwwards 0（自有资源）、linear 4；d-id 19、softr 20、muuuuu 103。
2. **「精细动效」八成是 Lottie + GSAP，不是手写 WebGL。** 30 站里 Lottie 5、GSAP 2、Three.js 1。
3. **高端产品站几乎不用 Tailwind。** 命中只落在工具站；linear / apple / durable / manus / lovart / payloadcms 都没有。
4. **字体策略分档次。** Google Fonts 直挂 = 跨域且无法控制子集；自托管 + `unicode-range` 切片 = 高端。中文站不可能走 Google Fonts。
5. **分析工具即隐私立场。** GA 是标配；Umami / Plausible 自托管是「我不卖你数据」的无声声明。
6. **结构同质化严重。** landing 公式 mast → hero → 功能分节 → testimonials → pricing → CTA → footer，除作品集站外基本全覆盖。
7. **架构在收敛。** 30 站里 Next.js 10、Astro 2、Webflow 3、WordPress 2、自研 4。门槛已不在选型，而在那 5 个域里每个是什么。

## 「吸收审美」这类指令的有效性判断（必做）

用户常把这批网址包装成「让 agent 吸收这些站的审美」。这个指令大概率失效，要直接说，不要顺着做。

判据：数一数有多少是同一品类的营销页。AI app builder 那一批（bolt / replit / emergent / base44 / softr / capacity / durable / floot / nxcode / tempo / camelai）是同一个模板换皮，看 11 个同质页只能得到模板的均值，不是审美。

还要点出两类「看起来是参考、其实是二手」：别人整理的 skill 说明页 / 教程站；AI UI 生成器 / 提示词市场。

报告里明确列出「值得深读的 4–7 个」和「价值只在商业模式的 20 个」。用户要的是判断，不是礼貌。

## 输出合同

```
一 实测技术选型表   site / 框架 / 托管 / 第三方域 / 备注（403 写 blocked）
二 可复用规律 5–7 条  每条挂实测数字
三 payload 判读     三层定义 + 两种假象对照（含用户点名的站）
四 值得深读的 N 个   其余站为什么没价值
然后               可搬回自家产品的动作 + 必写「不建议抄的一条」
```

三分证据：`确认`（有直接证据可复现）、`无法证实`（有异常但证据不足，写清缺口）、`未知`（明确标注）。不写「应该没问题」。

## 与 Parchment 4.0 的映射

这是「纳入集团」的实际落地。2026-11 的 Parchment 升级（分支 `feature/p4-editorial-depth`）已经把三条落进 token：

| 从实测学到的 | Parchment 落点 |
|---|---|
| 反相区块切版面（qiaomu `band`、apple 深色模块） | `color.semantic.inverse` + `.p-band`，暗色下自动翻转极性 |
| 墨级强线分区块 | `color.semantic.borderStrong` + `.p-rule-strong` |
| 行宽是排印约束不是容器宽 | `composition.measure.cn = 36em` / `latin = 66ch` |
| 字体按用途命名而非字体名 | `typography.family.{ui,display,editorial,cnBody,mono}` |
| 近方角只给阅读块 | `shape.editorial = 2px`，控件保持 8px |
| 极简 ≠ 小 payload | QUALITY-GATE 新增「Payload and delivery budget」门 |

两条明确不搬：**圆角不整体放方**（组件库的 2px 按钮读作渲染错误）；**`--font-mono` 不映射到衬线**（创作工作区的代码、时间码、参数值需要等宽）。

中文 measure 必须是 `em` 不是 `ch`：`ch` 量的是 `0` 的宽度（衬线里约 0.6em），36ch 会静默变成 60 字一行。这条是本次取证里唯一一个「看起来对、实际错」的坑，实测 36em @15px = 540px 才等于 36 个汉字。

## 明确不做

- 不从营销页推断产品设计能力
- 不把 token 命名体系当成品牌定稿
- 不声称视觉复刻完成（复刻归 `site-reverse-clone`，需单独授权）
- 不用工具绿色输出替代真实复验
