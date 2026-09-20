# 06 — jev-demos（迷宫寻路一致性实测）

- 研究日期：2026-09-20
- 仓库：https://github.com/Bud-ro/jev-demos，commit `37470f9`（2026-09-17）
- 技术栈：Dart；`packages/jev_common`（API shim + 结果录制）、`packages/maze_lookahead`（空间推理/前瞻测试）

## 概述

作者（Bud-ro）用 TypeSafe System One 模型测迷宫求解，重点是**同时移动（simultaneous move making）**：一次请求问接下来的 N 步，任何回退/撞墙/踩到 G 后离开都判失败；并测试只执行前 M 步决策时的表现。

## 一致性发现（文章声称 vs 仓库实际证据）

| 文章声称 | 仓库证据 | 判定 |
|---|---|---|
| 重复相同请求无法稳定得到相同答案 | maze_lookahead README 原文："Identical requests do not always get identical answers" | ✅ 可证实 |
| 多次运行下迷宫求解率归零 | quick preset（10 个 5×5 到 2 个 100×100 迷宫、每请求 100 步问题）下 `#` 墙和 `█` 墙迷宫**均解出 0 个** | ✅ 可证实（原文用词为"solved zero mazes"，文章的"求解率归零"属实但语境是特定 preset） |
| （文章引申）与本地 logits 方案确定性对比 | 仓库未直接做本地 logits 对照；但引用了 vllm#57250 的 "Jev at home" DiffusionGemma structured-read demo：同一风格 5×5 迷宫无邻接提示、每步一次读取、20 步最优走到 G | ⚠️ 间接证据 |

其他量化发现（文章未提）：计划呈"右→下→NONE"的直线倾向，下一步准确率仅 35–46%，从不回答 UP；**告知四邻格子内容可完全消除撞墙**，加上单步问题后 5×5 迷宫解出 6/10（4 个走最优路径），失败模式均为岔路口转错后在死胡同振荡。原始数据在 `results/`。

## 评估结论

一致性缺陷证据扎实且是仓库第一手观察；"求解率归零"成立但需注意是长视野（100 步计划）+ 大迷宫的 quick preset，小迷宫 + 邻接提示下成功率显著回升——与 02 号报告（jev-behavior-study）的"输入表征杠杆"结论互相印证。对生产系统的启示：**长视野多步空间规划不该交给判断模型**，且概率抖动要求下游必须设置置信度缓冲带（与官方 0.30–0.70 转人工的建议一致）。
