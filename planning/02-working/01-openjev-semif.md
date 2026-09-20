# OpenJev / SemIf 调研报告

- 研究日期：2026-09-20
- 仓库 commit：`ca3ba65`（浅克隆，路径 `planning/01-raw/repos/openjev`）
- 读取文件：README.md、docs/RESULTS.md、pyproject.toml、benchmarks/verify_published.py（grep 定位，全文未读）、目录清单

## 概述

SemIf（原名 OpenJev）是一个独立开源研究项目，自称复现 TypeSafe 闭源服务 **Jev** 的"接口模式"（runtime-defined 语义决策），而非复现 Jev 的模型或训练。核心思路：多数 agent 决策是小型分类（路由、重试、证据是否支持 X），与其让模型生成文本再解析成 `if`，不如**一次前向传播直接读出各类型化选项的 logits 概率**——无答案生成、无 JSON 修复、无解码循环。支持浏览器 WebGPU demo 与 Python CLI 两种使用方式。

## 实现原理

- **基座模型：Qwen/Qwen3.5-4B**（冻结，BF16 原生推理；README 指定固定 revision `851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a`）。浏览器 demo 另含 Qwen3-0.6B、MiniCPM5-2B（GGUF 量化）。
- **直接读出（direct）**：输入 = 非结构化 state + 运行时 criteria + 类型化选项描述；一次前向传播读取声明的选项字母 token 的原生 next-token logits，softmax 得到概率对。前一个 agent 已确认源码存在 `PROMPT_VERSION='direct-options-v1'` 与字母 token logits 的 softmax 归一化，与 README 描述一致。
- **共享状态复用**：同一长 state prefill 一次后可在多个 criteria 间并行分支（serial prefix reuse / parallel suffixes），速度从 2.33 decisions/s 提升到 20.03 decisions/s（777 决策 333s→38.8s，RTX 3090）；代价是 BF16 复用路径下 777 个 argmax 中 5–6 个漂移（仓库如实标注）。
- **对照实现**：Qwen3-Reranker-4B 作为原生 reranker 基线，在通用决策任务上明显弱于 direct logits（-0.115 ~ -0.188 balanced accuracy），仅检索排序时有用。
- **MLX 后端**（macOS arm64）：直接评分、串行前缀复用、并行共享状态决策。

## 评测与验证（文章声称 vs 仓库证据）

| 文章声称 | 仓库证据 | 结论 |
|---|---|---|
| 冻结 Qwen3.5-4B，零训练/零采样只读 | README 明确"frozen Qwen3.5-4B""no answer token is sampled"；RESULTS.md 明确未做 RLCD/训练 | **可证实** |
| 官方 102 个判断任务 | README/RESULTS.md 均写 "TypeSafe selected subset, 102 rows across 20 cases"；verify_published.py 引用键 `typesafe_public_102_equal_case_modal_agreement` | **可证实**（但注意：这是"从公开产物可对齐的 102 行子集"，非 TypeSafe 报告的 711 行全量） |
| SemIf 一致率 84.5% | RESULTS.md：TypeSafe subset modal agreement = **0.845**，另报告 TV 距离 0.177（Jev 为 0.127） | **可证实**（数值在仓库中，行级预测与原始结果在 `results/raw/`，但我未逐行核验数据文件本身） |
| Jev 88.3% | README/RESULTS.md："Published Jev … 0.883"，且明确声明"we did not run a live Jev endpoint"，该数字是从 TypeSafe 公开发表记录读取的 | **数值存在但不可独立证实**——仓库方自己强调样本小且经挑选、Jev 未经其复跑 |
| 复现 Jev 能力 | 仓库明确"Not reproduced"：Jev 未公开架构、并行采样器、RLCD 训练 | **不可证实**；仓库立场是复现接口模式，差距 3.8 个百分点 |

其他仓库内评测（direct Qwen3.5-4B）：自建 144 行 balanced accuracy 0.813；WANLI 256 行 0.637；judgment grid 0.806；鲁棒性扰动测试（选项反转/无关上下文等）显示选项顺序敏感仍是已知缺陷。

## 使用方式

```bash
# 依赖安装（Python 3.10+，CUDA GPU 可容纳 4B BF16）
pip install -e '.[test]'
# Apple Silicon 可选 MLX 后端：pip install -e '.[test,mlx]'，加 --backend mlx

CUDA_VISIBLE_DEVICES=0 semif-score \
  --mode direct \
  --model Qwen/Qwen3.5-4B \
  --revision 851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a \
  --input examples/decisions.jsonl \
  --output results.jsonl
# 同 state 多 criteria 时用 --mode shared：prefill 一次并行评估
```

输入 JSONL 行格式：`{id, state, question, options:[{id, description}]}`；输出含类型化选项概率、计时、模型 revision、prompt hash。浏览器版：仓库内 `webgpu-demo/index.html`（WebGPU，GGUF 量化模型）。复现脚本在 `benchmarks/`（evaluate.py、verify_published.py、shape777.py 等），文档在 `docs/REPRODUCE.md`、`docs/RESULTS.md`。

## 依赖

pyproject.toml：torch 2.10.0、transformers 5.17.0、accelerate 1.12.0、safetensors、huggingface-hub 1.31.0、tokenizers 0.23.2、numpy 2.2.6、sentencepiece、protobuf；可选 mlx / mlx-lm（仅 macOS arm64）、pytest。打包名 `semif-phase1`，CLI 入口 `semif-score`。

## 评估结论

- 实现与声称基本自洽：仓库代码、README、RESULTS 与 benchmark 脚本三方对齐，102 行 / 0.845 / 0.883 均在仓库文档中有明确出处，且附行级预测与原始结果文件，可信度较高。
- 需注意口径：0.845 是"可从公开产物对齐的 102 行挑选子集"上的 modal agreement，不是全量；0.883 是 TypeSafe 自报数，仓库方未运行 Jev、未独立验证，且作者自己强调该对比"不确立 near-Jev 能力"（概率质量 TV 距离 0.177 vs 0.127 有明显差距）。
- 技术亮点是 decision-native 直读 logits + 共享状态复用的系统路径（5.2× 快于生成式基线），而非模型能力超越 Jev。
- 建议在引用时表述为："SemIf 用冻结 Qwen3.5-4B 以 direct logits 方式在 TypeSafe 公开 102 行子集上达到 0.845 一致率（Jev 自报 0.883，未经独立验证）"。
