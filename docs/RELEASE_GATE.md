# 交付清单合同（release gate）

`scripts/release_gate.py` 核对的字段约定。目的是让「这次分发验过了」这句话可以被机器检查，而不是靠口头声明。

判据背景见 [交付与分发工程](RELEASE_ENGINEERING.md)。

## 这份合同证明什么

- 十道门都在，没有漏项；
- 每道标 `pass` 的门都有**观测证据**（不是 fixture，不是推断）；
- 证据文件的哈希、产物哈希、版本号三者自洽；
- ad-hoc 签名/未签名的包，一定配了首次打开说明。

## 这份合同不证明什么

- 不证明证据内容真实：文件哈希对得上，不代表那条命令真的在目标机器上跑过；
- 不证明产物可用：它只核对结构，不做运行；
- 不构成发布许可：上线仍由 delivery-walkthrough/checklist 主责决定。

所以输出里固定带 `release_authorized: false` 和 `runtime_verified: NOT_BY_THIS_TOOL`。

## 清单结构

```json
{
  "schema_version": 1,
  "product": "video-to-text",
  "version": "0.5.2",
  "platform": "macos-arm64",
  "channel": "release",
  "executor": "填写执行者标识",
  "signing": "ad_hoc",
  "artifacts": [
    {
      "id": "dmg",
      "name": "VideoToText-0.5.2-arm64.dmg",
      "kind": "dmg",
      "sha256": "64位小写十六进制",
      "size": 149354817,
      "checksum_source": "Release asset DMG-SHA256.txt",
      "local_path": "evidence/VideoToText-0.5.2-arm64.dmg"
    }
  ],
  "evidence": [
    {
      "id": "ev-sha",
      "kind": "command_output",
      "source": "observed",
      "path": "evidence/01-shasum.txt",
      "sha256": "64位小写十六进制",
      "note": "在下载目录执行 shasum -a 256 -c"
    }
  ],
  "gates": [
    {"id": "artifact_integrity", "status": "pass", "artifact": "dmg", "evidence": ["ev-sha"]}
  ],
  "limitations": ["没有开发者证书，用户首次打开需右键→打开"]
}
```

### 顶层字段

只允许上表出现的字段；多一个就拒绝，避免清单变成第二个真相源。

| 字段 | 约束 |
|---|---|
| `schema_version` | 必须为 `1` |
| `product` / `version` / `platform` / `executor` | 非空字符串 |
| `channel` | `release` 或 `preview` |
| `signing` | `notarized` / `developer_id` / `ad_hoc` / `unsigned` |
| `artifacts` | 非空数组，见下 |
| `evidence` | 数组，可为空（但标 `pass` 的门必须引用到） |
| `gates` | 十项，见下 |
| `limitations` | 字符串数组，可为空 |

### artifacts

- `id` 唯一；`name` 只能是文件名（不能带路径分隔符），且**必须包含 `version`**——这条挡住「包名还是 0.5.0、清单写 0.5.2」。
- `kind`：`dmg` / `pkg` / `app` / `zip` / `tar` / `exe` / `appimage` / `deb`。
- `sha256`：64 位小写十六进制；`size`：正整数。
- `local_path` 可选。给了就必须是相对路径、不越界、文件存在，且哈希与大小都要对上；不给则只核声明值，此时 `checksum_source` 必填，说明这个校验和从哪来（Release 资产、CI 日志、签名服务器等）。

### evidence

- `kind`：`command_output` / `log` / `screenshot` / `release_asset` / `note`。
- `source`：`observed` / `fixture` / `inferred`。**只有 `observed` 能支撑 `pass`**——用 fixture 或推断把门标成通过，一律拒绝。
- `path` 必须是清单同目录下的相对路径，越界拒绝；文件必须存在且哈希匹配。

### gates

十项必须齐全，缺一项或出现未知项都拒绝。这是清单的核心价值：允许你写「不知道」，不允许你悄悄跳过。

| id | 问的问题 |
|---|---|
| `artifact_integrity` | 产物有名字、大小、校验和，且能被复算 |
| `install_path` | 验的是分发形态（挂载后的包），不是构建树 |
| `cold_start` | 打包后的二进制真的启动了，入口可访问 |
| `self_contained_runtime` | 不依赖构建机的路径 |
| `code_signing` | 签名状态写清楚，用户知道怎么打开 |
| `log_capture` | 出问题时有日志可查 |
| `process_hygiene` | 没有失控的子进程 |
| `ci_exercises_shipping_path` | CI 跑的是发货路径 |
| `version_consistency` | 包内版本 == 发布版本 == 文件名 |
| `first_run_instruction` | 用户知道第一步做什么 |

`status`：`pass` / `fail` / `blocked` / `unknown` / `not_applicable`。

- `pass` 必须引用至少一条 `observed` 证据；
- `fail` / `blocked` / `unknown` 必须写 `reason`，且计入阻塞项；
- `not_applicable` 必须写 `reason`，不计入阻塞项；
- `artifact` 可选，填了必须是已声明的产物 id（把门绑到具体产物上）。

**额外硬规则**：`signing` 是 `ad_hoc` 或 `unsigned` 时，`first_run_instruction` 必须是 `pass`。没有公证的包，用户第一道坎就是「打不开」，这条不给过就等于把问题丢给用户。

## 用法

```sh
python3 scripts/release_gate.py template --product my-app --version 1.0.0 --platform macos-arm64 > release.json
# 填完证据后再核
python3 scripts/release_gate.py check release.json
```

通过时输出 `READY_FOR_HANDOFF`；有阻塞项输出 `BLOCKED`（清单本身结构合法）；结构有问题则 `REJECTED` 并说明第一个不合规字段。

`READY_FOR_HANDOFF` 的含义只是「证据齐全且自洽，可以交给发布主责复核」，不是「已发布」。
