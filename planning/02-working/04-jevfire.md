# 04 — jevfire（本地 vLLM/WebGPU 并行分类解码）

- 研究日期：2026-09-20
- 仓库：https://github.com/kikoncuo/jevfire，commit `5df83b5`（2026-09-18）
- 许可证：MIT；无再训练、无第二模型

## 概述

JEVfire 是对 Jev 的独立复现（作者自述受 harshatheg 的 Qwen-2.5-1B-RLCD demo 启发，"Named in tribute to JEV"）。核心思路：**用预训练模型现有的 language-model head 对经验证的单 token 标签打分**，把胜者映射到允许值，JSON 由应用代码拼装——即文章所说的"前向传播 + logits 归一化"路线，零训练。独立决策字段通过 vLLM 批量并行执行，共享 instruction/context 前缀以利用 prefix cache。

## 技术架构

- **CUDA/vLLM 后端**：实测模型 Qwen3.8-27B-FP8，RTX PRO 6000 Blackwell，vLLM 0.29.0；对 vLLM 的 patch 仅改 `sampling_params.py` 一个常量。
- **浏览器后端**：WebLLM + WebGPU，模型为 Qwen3.5-0.8B 的 MLC 转换（Apache 2.0）。
- **结构性保证**：schema 决定键和候选集，模型无法发明字段或集合外的值——但作者明确说明这是结构性保证而非事实正确性保证，模型仍可选错值。
- 三个浏览器实验：Super Mario World 1-1（Qwen + 显式物理守卫的混合结果）、Slipstream 四车并驾、村庄 demo。

## 性能数据（文章声称 vs 仓库实际证据）

| 文章声称 | 仓库证据 | 判定 |
|---|---|---|
| 0.8B Qwen + WebGPU，马里奥每步 71.26ms | README 精确吻合：final-build run 71.26ms mean worker inference、511 accepted choices、40.12s 通关，设备为 Apple M4 Max（非文章暗示的消费级 GPU 场景，且"excludes model download and CPU forecasting"） | ✅ 可证实（有 Measurement receipt） |
| 比 Jev API 178ms 快、无网络往返 | 71ms 为 worker 推理延迟，非整个控制回路延迟；仓库未直接对比 Jev API | ⚠️ 部分可证实，对比系文章推断 |
| 本地方案确定性高 | README 未直接强调确定性，但单 token logits 打分机制上成立 | ⚠️ 机制上成立，未做专门实测 |

额外发现（文章未提）：CUDA 侧合成 28 字段任务上，JEVfire 比生成等价约束 JSON 快 **10.29×**（496.9ms vs 5113.1ms，fresh prefix；warm prefix 达 14.77×），基准含 260 请求初始实验 + 2622 请求调参（均为重复 fixture），原始数据发布在 `benchmarks/results/benchmark.json`。

## 评估结论

仓库工程质量高（CI、原始基准数据、诚实的局限性披露——如"这是 Qwen+物理守卫的混合结果"、"5 samples/cell 只是初步延迟估计"）。它最有力地验证了文章核心论点：**logits 提取式判断没有任何技术壁垒，且本地并行批量分类在延迟上可以大幅反超**。但需注意 71ms 的适用前提（0.8B 浏览器模型 + 单步决策 + 排除下载/预测开销）与 Jev 的云端 27B 级别能力并非同一量级的比较。
