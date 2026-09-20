# Jev_study

> 研究 TypeSafe Jev（判断模型 API）及开源社区复现生态。信息源：yage.ai 文章《更好的替代品早已存在，Jev 留给研究的只剩时机》(2026-09-19)。

## 仓库布局

```
planning/
├── 01-raw/
│   ├── jev-timing-analysis-20260919.md   ← 原始文章（信息源）
│   └── repos/                            ← 9 个开源复现仓库（浅克隆，只读参考）
├── 02-working/                           ← 调研报告（NN-topic.md 编号）
└── 03-core/                              ← 留给定稿文档
execution/                                ← 留给后续实现代码
```

## 01-raw 中的复现仓库

| 目录 | 作者 | 文中用途 |
|---|---|---|
| openjev (SemIf) | TheoLeeCJ | 冻结 Qwen3.5-4B 零训练复现，102 任务一致率 84.5% |
| jev-behavior-study | RINNECODER | 1.1 万次调用行为研究，输入表达杠杆（1/16→16/16） |
| jev-capability-atlas | Zaious | 能力图谱，Jev 高置信幻觉案例 |
| jevfire | kikoncuo | 0.8B + WebGPU 浏览器本地 logits，71ms/步 |
| jev-ultrafast | browser-use | 官方优化案例，端到端 9.45s→7.09s |
| jev-demos | Bud-ro | 迷宫寻路一致性实测 |
| jev-phishing-bench | anisselbd | 专用分类器 81.3% vs 零样本判断 62.6% |
| WindTunnel | nekuda-ai | 感知/判断解耦，表征改造 25/49→49/49 |
| jev-browser | MahmoudAdelbghany | 单任务 1.8s / $0.0005 / 97% |

## 约定

- `planning/01-raw/` 已加入 `.gitignore`：只读参考源码，不修改、不 pull。
- 调研产物放 `planning/02-working/`，按 `NN-topic.md` 编号，一律中文。
- 所有项目文档（planning/、AGENTS.md、提交说明）使用中文；commit message 标题前缀可英文。
