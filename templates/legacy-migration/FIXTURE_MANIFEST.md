# Fixture & Regression Manifest (copy per product)

Use synthetic or properly sanitized page HTML only. Remove credentials, private messages, personal identifiers, attachment tokens and active scripts. Store original sensitive captures outside the public repository.

| Fixture ID | Platform | Snapshot DOM version/date | Scenario | Input path | Golden output path | Expected fields | Parser test | Browser test | Live-site result |
|---|---|---|---|---|---|---|---|---|---|
| example-only | chatgpt | replace | text + code + formatting | fixtures/... | fixtures/goldens/... | role/order/content | pending | pending | not-run |

## Mandatory regression contract

For each registered adapter:
1. Load sanitized HTML fixture; extract to canonical message model.
2. Assert roles, order, text, code blocks, links, math, attachments and errors where supported.
3. Serialize to Markdown; compare exact golden bytes (or a documented canonicalized representation).
4. Exercise UI/download/navigation in browser integration as applicable.
5. Report independent real-site smoke check evidence when release requires it.

Every adapter PR runs ALL prior adapter fixtures. Failure or skipped without documented exemption blocks merge. A green fixture suite does **not** prove current live-site compatibility.
