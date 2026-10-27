# V0.3 验证记录

2026年10月27日。候选本机实现，非发布验收；实现版本与逐文件摘要见 source-manifest.json。

- python-tests.log：75项真实本机Python回归，含HTTP/持久化/门禁/跨站与路径拒绝、外部文档篡改。
- browser-results.json：3项Chrome UI实跑，覆盖点子→答案→文档→争议拒绝/裁决→自检→阶段确认→刷新恢复，375/768/1440宽度、未保存保护、键盘与四标签页axe检查。
- checks.json：构建与验证范围；doctor.json：6份固定资产与外部方法锁校验。
- design-lint.json：设计令牌检查零错误/警告；design-detect.json：机械扫描无命中。这两项不证明审美质量。
- independent-review.md：不同agent principal的独立浏览器检查，保留初检HOLD、同版本修复与复验结论；不等于用户审美认可。

浏览器报告和截图均使用合成项目，不含真实客户材料；独立复验截图已保存 ui-1440.png、ui-375.png、ui-integrity.png，全部为合成数据；其余截图在忽略的work/。未上传真实私有项目数据。小视口自动fullPage截图出现Chrome拼接重复，已由独立真实视口、DOM数量与无横溢出检查确认不是重复渲染；不将异常拼接图当视觉通过证据。

原有 foundry.py/guard/panel、CLI和上游只读快照没有改动。真实Agent执行、身份认证、跨进程事务、生产部署、PMF和用户审美认可均未发生。本机服务不得暴露公网。阶段4安全档案、任务和变更完整操作保留CLI。

隔离构建补正：Tailwind改为显式只扫描web/src。reproducible-build.json记录原目录与隔离副本JS/CSS逐字节一致；新版本见source-manifest.json，独立审查追加限定复验。
