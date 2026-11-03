# design-evidence sources

## site-probe-2026-11.tsv

2026-11 对 30 个参考站点的一次实测快照。列为：`host / html_bytes / css_links / script_tags / third_party_hosts / stack_signals / note`。

读它之前先读这三条限制：

**note 列为 `unconfirmed` 的，表示该站没有命中任何硬路径框架特征，不代表它没有框架。** curl 抓到的 HTML 可能只是外壳、或者站点是自研栈。apple.com、reflex.dev、tempo.new、bolt.new、awwwards.com 属于这一类。要定性必须换真浏览器会话读渲染后的 DOM。

**note 列为 `blocked` 的，表示 WAF 拦截，无法判定。** `dribbble.com`（AWS ELB 202 + 0 字节）、`behance.net`（Varnish 403）、`packagingoftheworld.com`（Sucuri 307）。不要从表里把它们读成「没有框架」。

**`arena.ai` 那一行是覆盖值。** curl 命中 Cloudflare Turnstile（`cf-mitigated: challenge`），表里的 144592 字节与 Next.js + Turbopack 来自 ego-browser 的真实会话，`css_links` / `script_tags` 仍是 curl 抓到的 403 页面计数，不可用。

## 判读规则

`stack_signals` 只写能确认的东西：

```
硬路径    _next/ · _astro/ · /_nuxt/ · _app/immutable · data-wf-page
          · wp-content · wixstatic · ___gatsby · /assets/index-*.js
软信号    turbopack · --tw- · gsap · lottie · three.min · fonts.googleapis · .woff2
```

软信号只作线索。`tailwind` / `webflow` / `contentful` / `squarespace` 这些词在正文、注释、竞品对比页里都会出现。实例：`payloadcms.com` 的 HTML 里有 5 处 `contentful`，实际是首页的 `Payload vs Contentful` 对比文案，它自己跑的是 Payload。

`third_party_hosts` 已排除站点自身主域及其子域。apple 3、awwwards 0（全部自有资源）、linear 4 属于干净档；d-id 19、softr 20、muuuuu 103 属于挂满第三方档。

## 复测方式

`docs/DESIGN_EVIDENCE_ROUTING.md` 有完整命令配方。复测同一批站时保持同一组判据，否则两张表不可比。新增站点直接追加行，不要重写已有行——历史行是当时那一次的证据。
