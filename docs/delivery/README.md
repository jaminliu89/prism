# Prism · ENG-DELIVERY-2026-11 / read-only Issue Queue

## 唯一目标与任务所在

- Mission 目标、非目标、整体门禁、关闭条件：GitHub [Prism Issue #38](https://github.com/jaminliu89/prism/issues/38)。
- 真实任务、负责人、验收及状态：**各自 owner_repo 的 GitHub Issue 与 PR**；例如 Prism #39、#40；DCT #3、#4；VibeGuard #11；下载器 #74；Prism #41、#42。
- [mission-index.json](mission-index.json) **只记录跨仓库 Issue URL、静态依赖与哪些 Gate 适用**。没有 DONE、APPROVED、CI_STATUS、风险豁免；不能作为第二个集团任务看板。
- 原始产品目标与批准设计仍由既有 Prism Mission / Foundry 0–6 管理，集团工程看板仍归既有 board-workflow；这里不替换它们。

## 当前第一次执行

```sh
python3 scripts/delivery_queue.py validate
python3 scripts/delivery_queue.py next
python3 -m unittest discover -s tests -p 'test_delivery_queue.py' -v
```

其中 `next` 不联网、不调用模型、**不自动继续执行**。它只输出带 issue URL 的下一步调查候选（例如 WP-01 与 WP-03 可并行做只读规划/独立施工），不会授权本地写入、Git 合并或生产发布。任务实际进展必须以 GitHub API 与指定版本仓库证据重新读取。

可选择提供外部只读抓取的 issue 状态快照：

```json
{
  "issues": {
    "https://github.com/jaminliu89/prism/issues/39": "open",
    "https://github.com/jaminliu89/prism/issues/40": "open"
  }
}
```

```sh
python3 scripts/delivery_queue.py --observations /absolute/issues-snapshot.json next
```

**快照不可信，且只读状态无法证明真正交付。** 即使把所有 issue 都写成 closed，程序也只会输出 `claimed_closed_requires_verification`，始终 `release_authorized=false`。候选 PR 的 SHA、可信 CI、实际独立审查和远端保护（未来 DCT anchored gate）必须到 owner_repo 独立实证。

## Gate 关系与禁止的捷径

| Gate | 具体证据 | 主要任务 |
|---|---|---|
| G0 | 原始目标、受影响范围和真实授权 | WP-01、WP-02 |
| G1 | 架构草图、ADR、独立 Critic 与变更影响 | WP-02、WP-07 |
| G2 | Mission 验收 ID → 单切片 → 回归负例 | WP-01、WP-02、WP-04、WP-07 |
| G3 | 真正运行的测试、无关键 SKIP、真实工件 | WP-03、WP-04、WP-06、WP-07 |
| G4 | 对应 SHA 的可信 CI、独立身份审核、服务器侧保护 | WP-03、WP-05、WP-06、WP-07 |
| G5 | 安装、真实操作、异常恢复、Handoff | WP-06、WP-07、WP-08 |

严禁：把任务关闭当 CI 绿；把角色声明当审核身份；用 PR 中可编辑 YAML 自己规定 required checks；把本地 JSON receipt 当可信 review；把模拟 B 站媒体流当实际交付；绕过 VibeGuard 已有签名恢复任务。

## 执行者每轮接力算法

1. 重新读 Issue #38 和 `mission-index.json`，运行 `validate`。读取当前真实 issue、PR 和 Github Actions（必要时使用连接器），不要仅靠快照。
2. 选最先无硬阻塞的最小切片；**同一文件责任域只有一个实现者**。先判断是否已有进展、相同 PR 和未处理的 review finding，避免新建重复任务。
3. 在 owner_repo 的独立 feature branch 实现、验证、审 diff；不得修改 protected main；真正的 sandbox probe 不应被提交共享分支。
4. 输出证据与失败复现。必须要求外部 reviewer + 可信 CI 的变更才可以进入合并讨论。当前如缺受保护策略或独立身份，只能 DRAFT/NOT_READY。
5. 实际更新本仓/目标仓 Issue 的引用与下一项。只有所有任务的真实证据满足 Issue #38 的验收，才能关闭 Epic。记录最后 SHA 和失败陷阱，供后续 Agent 恢复。

本工具只给当前宿主确定的下一步，不会在对话结束后自主唤醒。真正的跨会话持续调度需要未来经过许可的宿主/自动化系统，不能拿本文件自称已上线自治团队。
