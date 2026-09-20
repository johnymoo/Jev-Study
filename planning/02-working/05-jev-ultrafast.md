# 05 — jev-ultrafast（Browser Use × TypeSafe 官方优化案例）

- 研究日期：2026-09-20
- 仓库：https://github.com/browser-use/jev-ultrafast，commit `1231850`（2026-09-18）

## 概述

Browser Use 官方的浏览器 agent 优化项目：**动态索引动作空间**。每步观察生成带标号的控件表（`[3] combobox Where from? · San Francisco`），Jev 在一次请求中同时选择操作（CLICK/TYPE_TEXT/SELECT/SCROLL/WAIT/DONE/BLOCKED）与目标元素（投机式：操作为 CLICK 时只有 click_target 能执行，两个决策一次网络往返）；只有 TYPE_TEXT 才由小 LLM（`inception/mercury-2.5`，关闭推理）生成文本。

## 优化点分析

- 一次快照一次浏览器调用，原子读取可见控件（名称/值/文本），**默认循环无截图**——Jev 消费结构化状态
- 点击守卫：验证文档、表单值、目标与邻近上下文，拒绝被遮挡控件；动画不再触发重判
- 组合框等待可见建议（上限 200ms）；隐藏标签页保持渲染；只发送可见文本
- 模型输出永不变成 selector、坐标、shell 命令或可执行 JS

## 性能数据（文章声称 vs 仓库实际证据）

| 文章声称 | 仓库证据 | 判定 |
|---|---|---|
| 端到端 9.450s → 7.092s | `docs/performance.md` matched comparison：6 次交替运行取中位，9.450s vs 7.092s，优化臂 3/3 全胜，任务时间降 25.0% | ✅ 可证实 |
| 交互调用 1092 → 101 | 同上：median browser protocol calls 1,092 → 101；TypeSafe 请求 22 → 17 | ✅ 可证实 |
| Jev API 中位延迟 178ms | 录制报告：17 次 Jev 请求中位 178ms | ✅ 可证实 |
| 提速主要来自去除重复 a11y 树扫描 | README"Where the time went"：原循环每次 DOM 突变都作废决策、反复读 a11y 树、解析数百 DOM 节点；新快照一次浏览器调用读完 | ✅ 可证实 |

**仓库自己的诚实标注（文章未充分转述）**：三对样本太少，双侧 sign-test p=0.25，"不足以做强统计声明"；对比是受控小样本而非广泛的 agent 基准。

## 评估结论

这是"架构/表征改造是提速主因"的最佳官方实证：**两臂使用同样的 Jev（jev-1.13.0）和同样的 Mercury 文本模型**，收益全部来自快照与执行层改造（协议调用降 10 倍）。同时也说明 Jev 本身在链路里的贡献是稳定的百毫秒级决策，而非端到端提速的主要来源——支持文章"拿走架构，不带走模型"的结论。
