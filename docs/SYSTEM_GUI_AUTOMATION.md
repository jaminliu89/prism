# 系统级 GUI 自动化：能做什么、坑在哪

2026年11月3日 · macOS 实测记录。

## 一、能力矩阵（全部实测，不是「应该能用」）

| 动作 | 做法 | 结果 |
|---|---|---|
| 列窗口 | `System Events` 遍历 `background only is false` 的进程 | ✅ 15 个应用，各自窗口数与标题 |
| 切窗口 | `tell application "X" to activate` + 回读 `frontmost` | ✅ A → B → 切回 A |
| 鼠标点击 | `System Events` 的 `click at {x, y}` | ✅ 返回被点元素路径 |
| 键盘输入 | 剪贴板 + `cmd+V` | ✅ 30 字符整串不丢 |
| 快捷键 | `keystroke "a" using command down` | ✅ |
| 读辅助功能树 | `entire contents of window 1` | ✅ 49 个节点 |

## 二、三个真踩到的坑

### 2.1 `keystroke` 打长串会丢字符

实测输入 `dogpaw`，读回来是 `Dog-as`——**字符被吞**。

```
原因：keystroke 是逐字符注入，目标应用的事件队列跟不上时静默丢弃。
```

**做法**：长文本一律走剪贴板。

```applescript
set the clipboard to "要输入的文字"
delay 0.15
tell application "System Events" to keystroke "v" using command down
```

逐字敲（`mode: "type"`）只在需要「像人在打字」的场景用，且必须接受可能丢字。

### 2.2 AppleScript 没有 `every UI element` 这种类名

```applescript
-- ❌ 报：预期是类名称，却找到标识符 (-2741)
repeat with c in (every UI element of el)
```

**正确写法**是 `entire contents`：

```applescript
set allElems to entire contents of window 1
repeat with el in allElems
  set r to role of el        -- AXButton / AXTextArea / AXWindow …
  set nm to name of el
end repeat
```

它返回**扁平的后代列表**，所以：

- **不能按深度控制**，只能按条数截断
- 对窗口多的应用（如 Finder 14 窗）要限条数，否则一次几万个节点

### 2.3 `position of mouse` 不存在

AppleScript 拿不到当前鼠标坐标。要坐标只能：

- 自己维护「上次移动到哪里」
- 或者用浏览器那一层的 `mouse.move()`（仅限页面内）

## 三、安全边界（必须显式说明）

**这几条不是「注意事项」，是「用之前必须想清楚」：**

1. **系统级操作会真的抢焦点、真的改内容**。
   测试要用可丢弃的目标（新建文档而不是改已有文件），跑完清理并**还原原前台应用**。
2. **只读能力不抢焦点**：`ui_windows`、`ui_ax` 可以随时用，适合先「看清楚再动手」。
3. **权限失败要报得清楚**：缺辅助功能权限时统一是 `-1719 / -25211`，
   工具应返回带处理指引的结构化错误，而不是抛异常让调用方猜。
4. **不要在别人的窗口里乱点**：坐标点击没有「意图校验」，
   点错位置就是点错位置。优先用 AX 树找到元素本身，再决定要不要用坐标。

## 四、和浏览器自动化的分工

| 场景 | 用什么 | 为什么 |
|---|---|---|
| 网页内部（DOM/网络/扩展） | 浏览器协议（CDP / 页面 evaluate） | 精确、快、可断言 |
| 原生控件（按钮/菜单/文本框） | AX 树 + AppleScript | 能拿到角色和名字，不用猜像素 |
| 实在没有 API 的地方 | 屏幕坐标点击 | 兜底，但**永远最后考虑** |
| 需要「看见」才能判断 | 截图 + OCR | 视觉兜底 |

**优先级：协议 > AX 树 > 坐标点击 > 纯视觉。** 越往前越稳定、越可断言。

## 五、检查清单（接入系统级自动化时）

- [ ] 列窗口 / 读 AX 树这类**只读**能力，是否能不抢焦点就用？
- [ ] 键盘输入长文本是否走剪贴板（而不是 `keystroke`）？
- [ ] 读 AX 树是否用了 `entire contents` 且限制了条数？
- [ ] 每个写操作（切窗口 / 点击 / 打字）是否都**回读验证**了结果？
- [ ] 测试用的目标窗口是否可丢弃，跑完是否还原了原前台应用？
- [ ] 权限缺失时返回的是「带处理指引的结构化错误」还是裸异常？
