# 11 — fast-browser-use（APUS-AI-Lab：Jev System 1 的本地开源复现 + Agent Skill）

- 研究日期：2026-09-21
- 仓库：https://github.com/APUS-AI-Lab/fast-browser-use（本地为 tarball 解包，无 git 历史；main 快照，2026-09-20 前后，README 引 Qwen3.5-35B-A3B 对比数据标注日期 2026-09-20）
- 许可：MIT；致谢 jev-ultrafast、openjev、Qwen-2.5-1B-RLCD
- 定位：**与 01–10 号仓库不同，这是目前唯一一个把"Jev 判断范式"做成开箱即用、100% 本地 Agent Skill 的完整工程**，不依赖 TypeSafe Jev API。

## 概述

自称"Jev 的开源逆向工程复现"：用开源权重（默认 `mlx-community/Qwen3.5-9B-4bit`，Apple Silicon MLX；另有 PyTorch 后端支持 CUDA 上的 Qwen3.5-9B / **Qwen3.5-35B-A3B**）实现 System 1 式离散决策的浏览器自动化。核心思路与文章对 Jev 的描述一致：**把开放式文本生成变成有界类别选择**——单 token logits 打分选动作，只在填文本时才生成。

## 机制剖析（一手读码，fast_browser_use/ 共 1826 行）

1. **候选动作构造**（`model.legal_candidates`）：页面内 JS 快照扫描（`browser.py` + `snapshot.js`）只取**当前可见、可交互**元素，生成 `(CLICK, btn_7)` / `(TYPE_TEXT, input_q)` / `SELECT` / `SCROLL` / `DONE` / `BLOCKED` 候选。模型永远不写 selector，幻觉与语法错误在结构上不可能。
2. **单 token 编码**（`candidate_codes`）：候选动作映射到 tokenizer 词表中**唯一单 token** 的代码（A、B、C…AA），上限 256 个候选，只取"完整且唯一"的编码，避免共享首 token 的比较歧义。这是 openjev"直接读选项 logits"思路的工程化加强版。
3. **一次前向打分**（`LocalModel.score`）：一条 prompt 做**单次 forward**，取下一个 token 的 logits，对候选 token 子集做 Softmax 归一化（`decision_from_scores` 还会校验概率和为 1、有限性，并给出 operation/target 两级置信度，自标"非校准正确率"）。同时缓存**策略+goal 的不变前缀 KV-Cache**（按 purpose 分键），页面部分每次重算。
4. **动作/文本解耦**：只有 `TYPE_TEXT` 走生成，且 prompt 强制以 `{"text":` 开头（模型只填值不写 JSON 壳），流式边生成边解析，最多 128 token。
5. **思考通道处理**（`think_score`）：Qwen 原生 thinking 模板下，强制在 `</think>` 后立刻截断打分——"关闭思考通道再做约束打分"，防止推理文本污染 logits。
6. **守卫型 Harness**（`agent.py`）：
   - 页面 **fingerprint** + `StalePage`：决策与执行之间页面变了就作废重判；`act` 先消费决策再执行，防止重试双击。
   - `MAX_STEPS` 预算；点击守卫（遮挡/禁用/readonly 过滤在 JS 侧完成）。
   - **独立验证**（`verification.py`）：`--expect-url/--expect-title/--expect-text` 在任务结束后读新 DOM 断言，且**从不喂给模型**。
   - 可选规划模式（`FBU_PLAN=1`，最多 8–12 步清单），默认关闭（FBU_PLAN=0 全目标直跑）。

## 性能数据（仓库自发布证据，docs/performance.md）

| 声称 | 仓库证据 | 判定 |
|---|---|---|
| Wikipedia 任务（9B）：首动作 8.52s，全程 30.091s（中位），4 次单 token 决策 | M2 Pro 32GB、MLX 4-bit，3 次试验 + telemetry JSON + 独立 URL/标题断言 3/3 通过 | ✅ 自发布可查，但**样本仅 3、无第三方复现** |
| **35B-A3B 比 9B 快 1.59×**（18.902s vs 30.091s，同任务同守卫） | 2026-09-20 新增对比：torch/MX 无关，35B 决策延迟 3,012ms vs 9B 5,663ms，动作数 3 vs 4 | ⚠️ 3 对样本、自家硬件，方向合理但统计力弱（同 jev-ultrafast 的 p=0.25 问题） |
| 多场景 5.4–12s 且全部独立断言通过 | generality.json + 表单/导航四场景 | ✅ 有 telemetry，仍属自证 |

诚实点：README 明确标注分数是"Candidate-normalized，非校准正确率"；验证断言不进 prompt；模型哈希跨 HF/ModelScope pin（`model-sources.json`）。

## 与其它仓库的关系

- **openjev（01）**：同为"读选项 logits、零训练"，fast-browser-use 把它从实验脚本做成带 KV-Cache 复用、守卫、验证的**产品级循环**，并给出 candidate-encoding 的细节（唯一单 token）。
- **jev-ultrafast（05）**：那是"Jev 云 API + 架构优化"；fast-browser-use 是"去 Jev、全本地"，两者互为镜像——共同结论：**收益大头在架构/表征层，不在模型本身**。
- **jevfire（04）**：同为本地 logits 并行分类，jevfire 走 vLLM/WebGPU 极致延迟（71ms/步），fast-browser-use 走易用性（uv 安装 + Agent Skill + CLI `fbu run`）。

## 对本项目的可借鉴点

1. **GB10 直接可跑**：torch 后端原生支持 `FBU_BACKEND=torch FBU_DEVICE=cuda` + `Qwen3.5-35B-A3B`（config 校验 MoE 结构），与本机 vLLM 上的 qwen3.5-35B-A3B 同源；权重支持 `--source modelscope` 下载（符合国内加速偏好）。
2. **工程模式可移植**：策略前缀 KV-Cache 复用、`{"text":` 强制前缀防 JSON 壳幻觉、决策消费一次性（防双击）、断言与 prompt 隔离——都是低成本高收益的守卫手法，适合移植到其它 agent 循环。
3. **局限**：Apple Silicon/MLX 是一等公民，torch/CUDA 路径较新且无官方基准数字；候选上限 256 的动作空间对复杂页面可能不够；所有性能数据均为作者自测。

## 评估结论

在 01–10 的坐标系里，fast-browser-use 是**"Jev 范式本地化的完成度最高实现"**：机制上完全覆盖文章描述的 Jev 接口模式（有界类型化决策、单 token 打分、文本解耦），且免费、离线、可审计。它不提供 Jev 与开源方案的质量对比实验（那是 01/02/07 的工作），而是把 01/04/05 的结论产品化。结论支持总览的核心判断：**Jev 无非买不可的理由——这个仓库本身就是"替代品早已存在"的活的证明**。
