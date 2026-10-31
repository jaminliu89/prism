# 交付与分发工程 · 证据记录

2026年10月31日。对象：`jaminliu89/video-to-text` tag `v0.5.2`（固定提交 `b8261f45d90cc5ec9353769ac78d575b4b264dc3`）的 macOS DMG。判据见 [交付与分发工程](../../RELEASE_ENGINEERING.md)，清单合同见 [交付清单合同](../../RELEASE_GATE.md)。

采集环境：Apple M2 Pro / macOS 26.5.1（25F80）/ arm64 / Python 3.13.12。全部命令在本机执行，产物从 GitHub Release 重新下载，不使用构建目录里的副本。

## 证据文件

| 文件 | 内容 |
|---|---|
| `evidence/01-shasum.txt` | 对下载回来的 DMG 执行 `shasum -a 256 -c DMG-SHA256.txt`，与 Release 资产一致 |
| `evidence/02-verify-dmg.txt` | `scripts/verify_dmg.sh` 完整验收：挂载 → 结构 → 静态链接 → 从挂载点启动 → 首页 HTTP 200 且含「蒸馏」→ 进程数 2 |
| `evidence/03-app-log.txt` | App 自己落的日志（窗口模式无终端，这是唯一可查来源） |
| `evidence/04-otool.txt` | `otool -L` 随包 ffmpeg：只依赖 `/usr/lib` 与 `/System/Library`，无 `/opt/homebrew` |
| `evidence/05-version-signing.txt` | `CFBundleShortVersionString` = `Resources/VERSION` = 0.5.2；`codesign -dv` 显示 `flags=0x2(adhoc)` |
| `evidence/06-ci-shipping-path.txt` | PR 阶段 `dmg` job 通过；同一套验收脚本在 `ci.yml` 与 `release.yml` 都被调用；Release 资产清单 |
| `evidence/07-first-run-instruction.txt` | DMG 内 `使用说明.txt` 全文：拖入 Applications、右键打开、`xattr` 处理 |
| `release-checklist.json` | 十道门的清单，引用上述 7 份证据（逐文件 SHA-256 已锁定） |

## 校验结果

```
$ python3 scripts/release_gate.py check docs/verification/release-engineering/release-checklist.json
status: READY_FOR_HANDOFF   gates: 10   open_blockers: 0   evidence: 7
signing: ad_hoc   signing_gate: OK
release_authorized: false   runtime_verified: NOT_BY_THIS_TOOL
```

`READY_FOR_HANDOFF` 的含义只是「十道门都有观测证据且自洽，可以交发布主责复核」，不是已发布，也不是独立验收。

## 本次没有覆盖的

- **Intel / 更旧 macOS**：只在 arm64 + macOS 26 上构建与启动，`LSMinimumSystemVersion 12.0` 未实测。
- **公证**：ad-hoc 签名，未走 Apple 公证；`spctl --assess` 会被拒，这是已知且已写进用户说明的状态。
- **包内完整业务流程**：只验到「启动 + 首页可访问」。转写（含模型下载）、长视频处理未在该包内跑过。
- **独立 review**：证据全部来自执行者自检，没有第二个 principal 复验；清单里也不声称有。
- **Windows / Linux 分发**：本文件只覆盖 macOS。

## 复现

```sh
gh release download v0.5.2 --repo jaminliu89/video-to-text \
   --pattern 'VideoToText-0.5.2-arm64.dmg' --pattern 'DMG-SHA256.txt'
shasum -a 256 -c DMG-SHA256.txt

gh repo clone jaminliu89/video-to-text && cd video-to-text
git checkout b8261f45d90cc5ec9353769ac78d575b4b264dc3
bash scripts/verify_dmg.sh /path/to/VideoToText-0.5.2-arm64.dmg
```

注意：`verify_dmg.sh` 会占用本机 8766 端口并在 `~/Library/Application Support/VideoToText/app.log` 写日志；已有实例在跑时用 `V2T_PORT=8799` 换端口。
