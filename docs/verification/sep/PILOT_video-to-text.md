# SEP 试点编排记录 — video-to-text

Prism 不复制产品代码；本文件只指向试点仓证据。

| 项 | 值 |
|---|---|
| 产品仓库 | https://github.com/jaminliu89/video-to-text |
| Owner | jaminliu89 |
| Baseline | `docs/sep/baseline.md` @ PR [#7](https://github.com/jaminliu89/video-to-text/pull/7) → `c4beed6` |
| Feature registry | `docs/feature-registry.yaml` @ PR [#8](https://github.com/jaminliu89/video-to-text/pull/8) → `bad56cff` |
| Critical smoke | `scripts/sep_smoke.py` @ PR [#9](https://github.com/jaminliu89/video-to-text/pull/9) → `81e791b` |
| Branch protection | PR [#10](https://github.com/jaminliu89/video-to-text/pull/10) → `b7a3267`；必需检查 `check`；`enforce_admins=true` |
| Small feature #08 | `cli.py smoke` @ PR [#11](https://github.com/jaminliu89/video-to-text/pull/11) → `96262bf` |
| #09 smoke / 打包 CI | `96262bf` 与回退 merge `ee5df12` 上 check/macos-mlx/dist/dmg success |
| #09 代码回退 | [PR #13](https://github.com/jaminliu89/video-to-text/pull/13) revert `e585f5f`；`DRILL_MARKER.txt` 已删除 |
| #09 生产发布 | **BLOCKED**（无 tag / Release 授权）。记录：`docs/sep/step-09.md` |
| 边界 | SkillHub / Vibeguard 未改；Prism 仅维护 SEP 合同与路线图 |

更新：2026-11-02 16:30（Asia/Shanghai）
