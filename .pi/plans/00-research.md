# 启动取证 — 2026年10月27日

Known：SkillHub已有idea-to-blueprint 1.1.0、delivery-walkthrough 2.1.0/final-checklist与site-reverse-clone适配，根Registry维护归属；site clone方法本体已有独立私有仓库。Prism私有仓库已创建并读回isPrivate=true。

| 既有实现 | 解决什么 | 复用方式 | Prism差异 |
|---|---|---|---|
| idea-to-blueprint | 点子到分阶段文档蓝图 | 固定1.1.0的入口/Prompt/模板 | 统一入口中的规划模式，不再造规划方法 |
| delivery-walkthrough/checklist | 软件真实链路、交付及发布证据 | 只读收尾清单；集团发布仍回原owner | 覆盖未到交付阶段的产品证据盘点，默认AUDIT_ONLY |
| site-reverse-clone | 目标类型、契约/架构取证、复刻与归档 | 固定集团适配/工具协作合同，按需到方法本体 | 协调专项发现与需求/清单，不再造爬虫 |

来源：UPSTREAM.lock.json逐文件记录仓库/commit/路径/SHA；源快照在sources中。远端site clone固定提交读取成功，其文档中带有晚于本会话的日期，未据此推断发布时间、成熟度或验证结果；以SHA而非自述时间作为引用身份。

Unknown：跨产品语义审计质量、独立reviewer、原生设备/私有目标工具可用性。后续用实际产品目标验证；不在此造数据。

硬限制：无第三方运行依赖；clone和浏览器能力不随文字快照安装；离线时可完成文档走读，不能补造网络/运行证据。私有仓库不等于报告自动加密，默认忽略真实审计产物。
