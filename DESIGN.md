---
name: Prism Product Foundry
version: 0.3.0
status: proposed
mode: operate
source: user brief 2026-10-27; existing Foundry V0.2 contract
colors:
  background: '#faf9f6'
  foreground: '#292824'
  surface: '#fffefa'
  sidebar: '#eeefe8'
  review: '#f5f5f0'
  primary: '#36493e'
  action: '{colors.primary}'
  on-action: '#ffffff'
  selected: '#dde3d6'
  muted: '#696b63'
  border: '#deded5'
  error: '#873d30'
  error-surface: '#f4e5df'
rounded:
  control: 4px
  dialog: 6px
spacing:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 40px
typography:
  body:
    fontFamily: '-apple-system, BlinkMacSystemFont, PingFang SC, sans-serif'
    fontSize: 14px
    fontWeight: 400
    lineHeight: 1.6
  title:
    fontFamily: '-apple-system, BlinkMacSystemFont, PingFang SC, sans-serif'
    fontSize: 28px
    fontWeight: 500
    lineHeight: 1.6
---

# Prism 工作台设计系统

2026年10月27日。本轮候选视觉，等待用户评审；不能称为用户已批准品牌。

## 产品任务与设计判断

项目负责人输入一句点子，逐阶段补充事实与假设、编辑文档、记录不同意见，再决定是否确认当前版本。工作台承载记录和审查；不把角色名或录入意见包装成真实 Agent 执行。

比较过两种方向：暖灰编辑台与冷灰密集控制台。前者用连续文稿、边注、目录组织任务；后者更适合监控大量状态。本轮选择前者，因为阅读与判断是主任务。色彩由纸面与校阅场景推导，非套用旧 Skill 固定配色。检索工具的 Hero/CTA 推荐不用于应用信息架构。

## 版式与层级

- 桌面：左侧 224px 项目/阶段目录，中间弹性工作与文稿，右侧 286px 决策/审查。顶栏 62px。内容边距 40px，段落组之间 24–34px。
- 980px 以下：审查区移到工作区之后；600px 以下左导航由顶栏按钮展开。窄屏先完成当前工作，再查看门禁。阶段和文档不会因窄屏消失。
- 系统中文无衬线用于操作与正文，无外部字体请求。Prism 字标用 Georgia。文档一级标题使用系统宋体形成阅读层级；没有字体下载依赖。
- 项目题目 28px / 1.6；正文操作 12–14px；章节标题 17px；元数据 10–11px。辅助信息不承担唯一的关键状态提示。文件 SHA 用等宽字体与自动折行。
- 表面由背景明度和 1px 分隔线区分。按钮/输入圆角 4px；仅弹窗使用柔和偏移阴影。禁止卡片套卡片、彩色指标阵列、渐变、光晕、emoji、无限动效与编造数据。

## 组件与状态

官方 shadcn CLI 生成 Button/Input/Textarea/Tabs/Dialog，使用 Radix 可访问行为。业务页消费这些组件；CSS 变量统一语义色，index.css 负责编辑台布局。原生 select 用于短枚举选择。

按钮区分主行动、轮廓行动和文字行动。hover 有背景/文字反馈；键盘 focus 2px 轮廓。disabled 表示当前不可执行；保存过程禁用提交并显示“保存中”。弹窗可 Escape 关闭，焦点由 Radix 管理。减少动态偏好关闭动画与过渡。

加载：读取项目时显示真实读取状态。空：无项目、文档无内容、无讨论、无审查分别有对应说明。错误：原后端拒绝信息可读且不冒充成功，弹窗内显示当前表单错误。提交文档后审查失效，必须重新审查。修改未保存时阻止文档切换与退出，并可撤销。

## 可观察验收

1. 1440px 下三栏同时可见，无指标卡片替代真实工作。
2. 创建点子和回答可刷新恢复；项目可切换，原始意图保留。
3. 文档可编辑、提交、预览，显示提交修订和SHA；预览不执行HTML。
4. 争议必须有真实录入意见；无意见裁决由后端拒绝，未决议题阻止确认。
5. 文档/问题/审查缺失时确认不可用；版本冲突拒绝写入。
6. 768/375px 无横向溢出；手机导航可选所有阶段，弹窗与操作可用。
7. 页面不声称真实 Agent 已执行、身份已认证或产品已上线。独立审查与用户认可分开记录。

## 参考与来源

- [shadcn/ui 官方 Vite 安装](https://ui.shadcn.com/docs/installation/vite)：组件基础与可访问交互。
- [官方源码与 MIT 许可](https://github.com/shadcn-ui/ui)：CLI 添加组件；保留生成源码结构，业务样式在外部覆盖。
- 集团设计部门固定 Impeccable Operate 方法：以任务扫描和阅读为主；不引入 landing page 模板。
- 技术与权限真相仍为 docs/FOUNDRY_V0_1.md、docs/FOUNDRY_SECURITY_AND_AGENT_V02.md、UPSTREAM.lock.json。
