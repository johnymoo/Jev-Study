# 09 — jev-browser（Jev 驱动的浏览器 MCP 服务器）

- 研究日期：2026-09-20
- 仓库：https://github.com/MahmoudAdelbghany/jev-browser，commit `20c27dd`（2026-09-17）
- 技术栈：Node ≥20 + Playwright；Jev `jev-1.13.0`；驱动模型 `auto/best-coding` via Claude Code 2.1.245

## 概述

把 Jev 包装成浏览器 MCP 服务器给 LLM agent 用：一次 `page.evaluate` 快照（2–25ms）→ 本地按目标词重叠排序的紧凑候选列表 → **一次 Jev 并行调用**（~300ms，零 LLM token）同时决定 action、element、key、字段↔文本绑定、上步验证（prev_ok）、完成检测（goal_achieved）→ CDP 执行 → 确定性状态 diff 验证；低置信/卡死/循环时升级给 LLM（escalation contract）。

## 基准数据（文章声称 vs 仓库实际证据）

| 文章声称 | 仓库证据（RESULTS.md，2026-09-17） | 判定 |
|---|---|---|
| 单任务中位 1.8s | jev-only 栈 12 任务（jev-only n=3 共 33 轮）avg wall/task p50 **1.8s** | ✅ 可证实 |
| 成本约 $0.0005/任务 | $0.017/33 轮 ≈ $0.0005 | ✅ 可证实 |
| 完成率 97% | 32/33 = 97% | ✅ 可证实 |
| （文章未强调）与 LLM agent 对比 | vs Claude+Playwright MCP：~10× 快、~100× 便宜、同套件 97% vs 100%；同驱动下 claude-jev 比 claude-playwright 快 1.5×、省 1.6×、同为 12/12 | ✅ 补充 |

设计细节：类型化 ref 使 Jev 无法幻觉出不存在的动作（非法组合纠正性重问一次）；确定性验证覆盖 Jev 的弱信号；置信度分层策略（可逆动作 0.3、其余 0.5）把成功率从 94% 提到 97%。

## 局限（仓库自述）

- Claude 两栈 n=1（成本预算），比例仅方向性参考；本地确定性任务为主，仅 2 个 Wikipedia 实网任务
- Jev 单独会败于回溯类任务（t03 需导航返回），靠升级路径恢复——这是设计内行为
- 纯阅读抽取任务（l02）Jev 反而更慢更贵：大页面状态推给 Jev 的输入成本高于 LLM 自己读快照 → "读和答"归 LLM，"在页面上行动"归 Jev

## 评估结论

三个数字全部在仓库中可证实，且仓库提供了复现命令（`node bench/compare.mjs ...`）与程序化验证（服务端随机 8 位码防 LLM 裁判偏置），方法学可信。它给出文章结论最干净的工程佐证：**判断模型 + 确定性验证 + 升级契约**的组合可以在窄域任务上以 1/100 成本逼近 LLM agent，同时明确划出了判断模型的能力边界（回溯、纯阅读）。
