# 10 — Kev 与 Bespoke Nimble：训练方法与数据集（自研微调参考）

- 研究日期：2026-09-20
- 信息源：微信公众号文章《JEV：一个只会说「选A、打3分、是」的AI模型爆了，48小时炸出14个项目》（存档 `01-raw/wx-jev-kev-nimble-202609.md`）+ 两仓库一手核验
- 仓库：nimble `35fe1f4`（2026-09-19）、kev `20fa626`（2026-09-19）
- **定位：本报告侧重"我们以后做自己的微调决策模型时能直接抄什么"**

## 一、两条微调路线速览

| | Bespoke Nimble | Kev (Jared Palmer) |
|---|---|---|
| 基座 | Qwen3.5-9B | Qwen2.5/Qwen3 0.5B–8B（推荐 4B） |
| 方法 | LoRA（rank 16）+ 答案 token 交叉熵 | LoRA（r=16）+ 从零训练的 pointer readout head（0.46M） |
| 可训参数 | LoRA 适配器 | 9.3M（占 backbone 1.9%） |
| 训练数据 | 2,676 条对比对（10 领域） | 10–13 个公开源 ×1,000 条 + 2×448 条程序化策略对（decision-v4/v6 suite） |
| 关键超参 | lr 5e-5、effective batch 8、1 epoch、BF16、seed 17、2,048 token 限长 | lr **5e-5**（最大单项改进）、2 epochs、batch 4×accum 2、bf16 autocast |
| 成本 | 调参 L40S、终训 H100 | kev-4b 单 H100 ~40 分钟；0.5B 试验 $0.15–0.30；M5 笔记本 0.06 度电 |
| 成绩 | 324 held-out 90.12%（Jev 93.21%，基座 66.36%，Qwen3.8-27B 84.88%） | OOD：kev-4b 0.79 / kev-8b 0.80（Jev 0.86） |
| 许可 | Apache 2.0（数据/权重/配方/推理全公开） | 开源 + HF 集合 |

## 二、Nimble：contrastive data curation（最值得抄的数据方法）

**核心思想**：没有 teacher 概率可蒸馏，就构造**最小对比对（minimal pairs）**——两条样本几乎完全相同，只改一个关键事实使正确答案翻转，标签是硬的（对/错）。模型被迫学会"哪条证据才应该改变决策"，从而把 logits 校准到可用。

- 文中例子：规则"只有 Mira 可授权账户 42 退款"；对比对只把签名人 Mira→Noah，答案 true→false，其余文本（问题、政策）逐字相同
- **无需人工标注概率、无需蒸馏**；训练目标是 allowed candidate logits 上的交叉熵（直接学类型化决策）
- 仓库明确："只拿 Jev 评估，不用 Jev 输出"；保存的 Jev 概率仅留作未来 soft-target 蒸馏的选项
- 数据集：`data/train.jsonl` 2,826 条（发布模型用 2,676）/ `data/eval.jsonl` 324 条（仅终评）。覆盖 Commerce、Education、Media、Public Services、Supply Chain、Travel、Workplace 等 10 领域
- 题型分布（训练/holdout）：Choice 1,244/260、Noul（布尔）500/0、Score 932/64
- **标签全部是合成且由模型自查、无人复核**——同模型多次调用可能犯同样的错，作者自己承认此局限

## 三、Kev：架构隔离与"学习率保知识"

- **单次 prefill 多问题**：state 编码一次，多个 question 经 block-causal mask 并行独立推理（问题间互相不可见，隔离性验证到 4e-6 精度）；pointer head 对每个问题的 decide token × option token 打分后 softmax
- **训练/推理同一 renderer**：线上请求与训练数据走同一格式管线，推理不会遇到训练没见过的格式
- **学习率是保住基座能力的关键**：默认 2e-4 会把基座知识"训没"，降到 **5e-5** 保住大部分——这类微调不是学新知识，而是教模型"用"已有能力做决策（低漂移旋钮 lora_targets/head_lr/weight_decay 均不敌 lr 5e-5）
- 数据来源：公开数据集转 TypeSafe 形状（Banking77、AG News、MNLI、BoolQ、SST-5、Yelp 等）+ 程序化 policy pairs，冻结为带校验和的 suite（`evals/`）
- 可选数据增强：`--p_none_pair`（部分 Choice 记录附加 none-of-the-above 最小对）；`--option_isolation`（选项隔离子分支，置换不变但 4B 上损精度）
- 严谨性：每个 trial 记录 git commit、suite hash、代码 hash，不一致拒绝运行；训练 TF32/bf16、评估 fp32-exact（TF32 本身就会移动概率 ~1e-3）

## 四、两文互相印证的结论

1. **无需蒸馏、无需秘密配方**：LoRA + 答案 token 交叉熵 + 硬标签即可逼近 Jev（差 ~3pp）
2. **lr 5e-5 是两个项目共同的甜点**（Kev 的最大单项发现；Nimble 终选配方同为 5e-5）
3. 数据质量杠杆在**对比结构**（翻转关键事实）而非数据量——2,676 条就够把 9B 从 66% 拉到 90%

## 五、局限（做自研模型时要避的坑）

- Nimble 测试仅 324 条/162 对/6 领域，作者自认"换测试可能远不如 Jev"；单一 held-out 高分易掩盖线上风险，应补**校准曲线与分布外测试**（评论区共识）
- Kev OOD 差 Jev 6–7pp，短板集中在知识题（MMLU 0.69–0.75 vs 0.90）和日期算术——**基座缺的知识微调补不回来**
- 合成标签自查有系统性盲区；Nimble holdout 的 Noul=0（布尔判断无 held-out 覆盖）

## 六、对我们的可执行参考（GB10 自研微调）

1. **数据**：优先复刻 contrastive data curation——按业务写策略/规则文本，程序化生成最小对比对（改一个字段翻转标签），题型覆盖 Choice/Noul/Score 三类
2. **配方起点**：LoRA r=16、lr 5e-5、1–2 epochs、BF16、答案 token 交叉熵；单卡即可（kev-4b 一张 H100 40 分钟量级，GB10 上 4B 级基座可试）
3. **基座**：知识类任务别指望微调补；选带足够 MMLU 的基座（4B–9B 档），体积优先则 Kev 路线（readout head + block-causal 多问题）
4. **评测**：冻结 held-out suite + 校准曲线（ECE/可靠性图）+ OOD 集，别只看单一准确率
5. 参考实现：`repos/nimble/data/`（现成 2,826+324 条样例数据）、`repos/kev/kev/{contrastive,data,train}.py`（对比对生成与训练循环）
