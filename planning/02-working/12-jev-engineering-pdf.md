# 12 — 《Jev Engineering for Coding Agents》PDF 解读

- 研究日期:2026-09-22
- 对象:12 页设计笔记综述《Jev Engineering for Coding Agents》(基于 TypeSafe 创始人 Diogo Almeida 的设计笔记,"独立编译",2026-09)
- 原文:[`assets/12-jev-engineering-pdf/jev-engineering-for-coding-agents.pdf`](assets/12-jev-engineering-pdf/jev-engineering-for-coding-agents.pdf) · [Google Drive 源](https://drive.google.com/file/d/17h982xvsL3E7b80iGmOCfKp9qTOW9ohv/view) · 逐页截图见同目录 `page-01..12.png`
- 交互式可视化(路由算术计算器、架构图、token 分布等):[site/jev-visual.html](../../../site/jev-visual.html)
- 与本仓库其它报告的关系:本仓库 01–11 号报告核验的是 **Jev 判断模型本身**(API 及开源复现生态);本篇是围绕"**用 Jev 造 coding agent harness**"的架构设计综述,视角互补——前者问"Jev 靠不靠谱",本篇问"Jev 该被问什么"。

---

## 0. 文档性质与可信度

- 副标题为 "A Synthesis for Study",自述是**独立整理的学习综述**,基于 "Diogo Almeida(TypeSafe 创始人)的设计笔记",明确声明与 TypeSafe / Anthropic / OpenAI / Microsoft 无关、未经认可。
- "Jev"、"TypeSafe"、"Diogo Almeida" 这些名字很可能是**匿名化/占位处理**过的真实来源(文中 Jev 被描述为"返回带概率的 typed choice / score / noul 决策的决策模型",实际可能是某个 LLM 微调或结构化决策组件)。
- 成本数字是**示例性的**(按文中引用的 list price),token 占比表自述为"illustrative estimate"。
- 引用了一处外部数据:Microsoft fastcontext 项目报告 GPT-5.4 轨迹中,读取+搜索占 tool-use 轮次的 56.2%、主 agent token 的 46.5%。这一数据未能在本地核实,引用时需谨慎。

## 1. 核心论点

1. **Coding agent 本质上很简单**:一个 while 循环 + 模型 + 少量工具。创新空间不在循环本身,而在**循环每一轮"喂给模型什么"**。
2. **Jev 不是写代码的模型**,而是模型旁边的**决策层**:harness 把当前状态(目标、上下文、规则、可用动作、历史动作)交给 Jev,Jev 返回**带概率的、有类型的答案**(choice / score / noul),由确定性代码去验证、设阈值、分支——不需要解析自然语言。
3. 组织一切的**思想实验**:"如果 LLM 没有 KV cache,你会怎么设计 coding agent?"
   - 现在的 agent 之所以是 append-only 转写(transcript),完全是因为 KV cache 的经济学:复用缓存前缀便宜,改前面任何内容都会导致后面的全部重算。
   - 把 cache"想象掉",上下文就从"不断累积"变成"**按 query 主动组装**(assembled, not accumulated)"。

## 2. Jev 每轮要回答的六个问题(Table I)

| 决策点 | 问题 | 类型化答案 |
|---|---|---|
| Context | 这个 chunk 对当前 query 应该多"可见"? | choice: hide / short / long / full |
| Cache | 复用缓存前缀还是重建? | noul + probability |
| Routing | 这个子任务能不能离开 frontier 模型? | choice + 成本估计 |
| Tools | 哪个工具匹配当前意图? | 排序 choice, top-k |
| Permissions | 这条命令该不该跑? | allow / ask / deny |
| Security | 这个任务会碰哪些文件?(敏感度) | sensitivity score |

## 3. 六个"继承病"(Table II):现有 agent 不加思考就继承的设计

| 症状 | 根因 | 代价 |
|---|---|---|
| 1. 路由失败 | 交回大模型时要重处理全部上下文 | 混合路由比纯 frontier 还贵 |
| 2. 工具挤占上下文 | schema 必须常驻 system message | 花在无关工具上的 token;选择变差 |
| 3. 压缩盲目(compaction) | 假设所有未来轮次共享同一状态 | 不知道问题就压缩,丢掉后面需要的 |
| 4. 子代理很少触发 | 决定传什么上下文、如何合并回来太困难 | 几乎没有自动并行 |
| 5. 重启即丢失 | 有状态转写会随时间漂移/损坏 | 好状态和坏状态一起扔掉 |
| 6. "电池"之争 | 每个内置能力都永久占用上下文 | 被迫在易用与强大之间二选一 |

**六个病可以用"拿掉 KV cache"这一个视角全部解释**,并用一个动作全部治疗:状态显式化、类型化,由 Jev 按 query 决定 context / 路由 / 工具 / 权限。

## 4. 路由算术(Section II-A,Fig. 2)

记 X=上下文 token,Y=生成 token,Z=工作中额外读取的 token。价格:Opus $5/$25, Sonnet $3/$15(每百万 token)。

- 路径 1(纯 Opus):`25Y + 5Z`
- 路径 2(Opus→Sonnet→Opus):Sonnet 载入上下文 `3X` + 生成 `15Y` + 读 `3Z`,Opus 回来重读变化 `5(Y+Z)`,合计 `3X + 20Y + 8Z`

代入典型会话形状 X=0.65, Y=0.12, Z=0.23:纯 Opus = **4.15**,路由路径 = **6.19** → 想省钱的路由反而贵了约 50%;纯 frontier 只花路由方案约 2/3 的钱。

**结论**:错不在路由,而在**按 token 计价而不是按"上下文重建"计价**。路由要成立必须:① 给便宜模型一个**小型、专门构建**的上下文而非整个会话;② 回程**不强迫** frontier 模型重读 helper 产出的一切(改为合并一个"带打分的 chunk")。

## 5. Token 到底花在哪(Section III)

输入视角的典型 CLI 会话(重复读取按次计数):

| 子任务 | ~占比 | 备注 |
|---|---|---|
| 读文件内容 | 30–40% | 最大项;文件被当上下文反复读 |
| 代码库搜索 | 10–18% | grep/glob/列表,噪声大 |
| 命令输出 | 10–20% | 失败时栈跟踪和日志爆炸 |
| system prompt/工具 schema/AGENTS.md | 5–12% | 每轮都要付的固定开销 |
| 推理规划 | 5–15% | 疑难调试更高 |
| 写/改代码 | **4–10%** | diff 和 str_replace 很紧凑 |
| 给用户解释 | 2–5% | CLI agent 刻意简短 |

要点:**写代码——agent 存在的目的——是最小的支出项之一**;读取+搜索+命令输出合计约 2/3。因此最大的效率杠杆不是更好的模型或 diff 格式,而是**更聪明的检索**。
(截图核对 Fig. 3 条形图取中点值:读文件 35%、命令输出 15%、搜索 14%、系统提示 8%、推理 10%、编辑 7%、其余 3% + 用户解释。)

## 6. 基础层(Section IV)

1. **可编程权限**:不是分类器式的 auto 模式,而是策略查询;关键在"深检"——执行前检查脚本**内容**而非命令名。
   ```
   policy "exec":
     deny   if command touches ~/.ssh or .env*
     deny   if script contents contain network egress and task.scope != "deploy"
     ask    if command writes outside repo root
     allow  if command in read_only_set
     allow  if tests/ and exit code is expected
   ```
2. **Harness 作为工具路由器**:模型用自然语言描述意图,harness 用一串 typed Jev 调用选出唯一最佳(或 top 几)工具并构造参数;错误参数类型变成 validation error 而非静默失败。模型永远不需要在上下文里持有几百个 schema。

## 7. Meta-attention:上下文本身是决策对象(Section V)

- 对**每个 chunk**(工具输入/输出、内部推理、每轮对话)做 noul/打分 → 后续版本升级为**可见度阶梯**:hide / short summary / long summary / full(同一 chunk 按 query 变化:2400 行 grep 输出可以是"12 个相关命中",也可以对下一个问题完全不可见;但**从不从 state 中删除**)。
- 这是 **query-aware compression**:compaction 的思想保留(压缩),最大缺陷消失(在知道问题**之前**压缩必然丢东西;知道问题**之后**压缩就知道留什么)。
- 附录点子:harness 若能给 grep 输出标相关性热力图,就能按预算任意下采样(笔记还吐槽"这样也好看")。

## 8. 路由与子代理重访(Section VI)

- 有了"小型相关上下文"能力:便宜模型不再装载整个会话;结果作为**打分过的 chunk** 合并回来;一切成本/智能感知(cost-aware, intelligence-aware)。
- **子代理被解锁**:笔记猜测今天子代理成本的大头是"决定传什么上下文";若组装上下文变得便宜且自动,子代理可以随便开;用户还能拿到一个"花钱买更快/更好 vs 省着跑"的旋钮。
- **极端并行**:共享状态 + 锁;显式区分读/写使读任务永不争锁。
- **目标去重**:派生子任务前先注册为 subgoal,与已有 subgoal 去重,不重复开跑。

## 9. 工具/技能分层披露(Section VII,Fig. 5)

三档:**Tier 1 一行摘要**(数百个工具常驻)→ **Tier 2 选中才载入完整 schema** → **Tier 3 文档按一次性查询读**;用完即从上下文清除,不污染。

- 若内置能力"用到才花钱",**电池之争自动消失**:可以 ship 数百工具和数千文档页。
- "更好的电池":社区工具为什么常常没用?猜因模型不理解它们。第一方 harness 可内置"教模型怎么用每个工具"的提示(相当于每工具一个内置 skill),且干净上下文使工具逻辑不毒化会话。

## 10. 条件式指令(Section VIII)

- AGENTS.md 今天全量加载;提案是**按条件加载片段**:碰 `*.tsx` → style-guide;进 `billing/` → `billing/GOTCHAS.md`(笔记建议每个子目录一个 footguns 文件);写散文 → 文风样本+禁例。
- 与 skill 的区别:**skill = "现在就做这个"**;**条件式指令 = "只要条件成立就一直记住这个"**。后者需要 skill 缺少的关键属性——**对 compaction 免疫**(条件绑定,条件成立即重载;或被 pin 住不被摘要掉)。
- **结构化 skills**:可携带行为变化而不只是指令,类似 hook 但更强;现有 hook 的缺陷是一旦加上就永久驻留——结构化 skill 随触发条件挂载/卸载。
- **递归语言模型**(RLM, A. Zhang 2025):把 agent 状态尽量放进**命名变量**而非转写文本——状态是显式的,不是"上下文窗口里碰巧剩下的东西"。

## 11. 安全感知路由(Section IX)

- 路由现有两轴:难度、成本。**新增第三轴:信任/敏感度**。
- 给每个子任务估计"会碰哪类文件",把策略挂到文件类型上,据此路由:

| 会碰的文件 | 策略 | 可用模型 |
|---|---|---|
| 公开文档、开源依赖 | open | 任意,越便宜越好 |
| 应用代码 | standard | 经过审查的供应商 |
| 密钥、env、基础设施配置 | restricted | 仅第一方 frontier |
| 专有研究代码 | custom | 排除指定厂商 |

- 观点:**难度和成本不是路由的全部理由**——某些便宜 API 上的开源权重模型,数据隐私没保障;政策驱动后,这些偏好从"纪律"变成"配置"。

## 12. 后台处理(Section X,Fig. 7)

新兴模式:并行更新的 HTML 进度页("理解,而非生成,是新瓶颈")、用真实流量自动生成 eval(跑约一天再切换模型)、ELI5 讲解器等。

共性:都是**当前代码库状态的只读函数**。若昂贵检索只做**一次**、被所有后台任务共享(而非各自重做),后台任务就能大量开;且只读任务永不争锁。这是 Jev 论点的兑现处:harness 必须精确知道上下文里有什么、每个操作是读还是写。鉴于检索占 token 预算的最大头,**共享检索是单项最大的节省**。

## 13. 电池候选清单(Table V)

| 项目 | 角色 | 原生化角度 |
|---|---|---|
| headroom | 上下文压缩器 | 分类器检查压缩是否保住所需事实 |
| rtk | 工具输出压缩器 | 第一方提示让模型真正会用它 |
| ast-grep | 结构化搜索 | 手册载一次,生成 N 个 query,按相关性过滤 |
| ast-outline | 结构化大纲 | 分层调用:先选子树再下钻 |
| fastcontext | 代码库探索子代理 | 路由给它,或用结构替换其搜索 |
| fff | 路径/内容搜索 | 内存索引、按频率排序,长会话比 ripgrep 快 |

## 14. 结论与总体评价

**一句话**:把上下文窗口当作**有目的地组装**的东西,而不是**意外累积**的东西;状态显式化、类型化,每个高频决策点由 Jev 回答带概率的 typed answer。

**我的评价(批判性视角)**:
- **最强的一点**:对 KV cache 经济学如何塑造 agent 架构的刻画非常锋利,六个症状是统一框架下的推论,不是六条零散吐槽。"按 token 计价的定价模型让直觉正确的路由变贵"这一算术演算值得每个做 multi-model 系统的人亲手重算。
- **相关性高的部分**(即使不动架构也可借鉴):query-aware 压缩/可见度阶梯、按条件加载 AGENTS.md 片段 + compaction 免疫、安全敏感度作为路由轴、共享只读检索、目标去重。
- **存疑之处**:
  - "没有 KV cache"是反事实——prompt caching 真实存在且很便宜,所以"显式状态 + 每 query 重组装"的方案本身也有成本(组装/打分调用本身要花钱、要延迟),文中没有给出 Jev 决策层自身每轮的 token/延迟账,这是最大的未回答问题。
  - 每轮对每个 chunk 打分意味着高频小模型调用,失败模式(打分噪声、阈值调参)未被讨论。
  - 数字均为示例;"Jev/TypeSafe/Diogo Almeida" 疑为匿名化占位,fastcontext 的 56.2%/46.5% 数据未能核实。
  - 文档本身是"独立编译的学习综述"而非一手材料,适合作为**思路索引**,行动前应回到原始设计笔记。

## 截图核对中补充的图表细节(逐页目视)

- **Fig. 1(p.1)**:架构图左列 "Explicit State" 包含 Tool calls / User turns / Diffs+files / Reasoning / AGENTS.md / Cached prefix 六类,落到 "Chunk store(addressable · typed)";右列 "Jev Decisions" 为 Chunk scoring / Cache reuse? / Route model / Pick tool / Permit command,标注 "typed answers · probabilities";底部 Jev Harness 下是 repo / files / test logs / git history;右侧 LLMs 盒子:Frontier LLM、Sub-agent models、Cheap/open models、Background reviewers,由 security policy 连接。
- **Fig. 2(p.4)**:柱状图 Pure Opus 4.15 vs 路由 6.19,路由柱分解:load 1.95 / Sonnet gen 1.80 / Opus reload 1.75 / Sonnet reads 0.69。
- **Fig. 3(p.6)**:条形图取中点值:读文件 35%、命令输出 15%、搜索 14%、系统提示 8%、推理 10%、编辑 7%、其余 3% + 用户解释。
- **Fig. 4(p.7)**:可见度阶梯示例——grep 输出 2,400 行 → SHORT SUMMARY·12 hits;失败测试日志 → LONG SUMMARY·trace+cause;`auth/session.ts` → FULL·relevant to query;被取代的旧 plan → DON'T SHOW。中间是 "JEV, query-aware" 节点。
- **Fig. 5(p.8)**:三层阶梯,右侧标注 "cost per turn rises",Tier 2→3 箭头标 "valuable to work with only a few tools"。
- **Fig. 6(p.9)**:CURRENT TASK 分叉为三个条件(touched `*.tsx`? / inside `billing/`? / writing prose?)分别挂 style-guide.md / billing/GOTCHAS.md / voice samples + don'ts。
- **Fig. 7(p.10)**:MAIN AGENT(writes)与 SHARED RETRIEVAL(relevant files, symbols, diffs, found once)并列,五个后台任务(cross-model review、background eval generation、ELI5 explainer · quizzes、live progress page、micro-world simulations)全部挂到共享检索上,标注 "read-only · never contend for locks"。

## 附:本仓库内文件清单

- `12-jev-engineering-pdf.md` — 本报告
- `assets/12-jev-engineering-pdf/jev-engineering-for-coding-agents.pdf` — 原始 PDF(12 页)
- `assets/12-jev-engineering-pdf/page-01..12.png` — 逐页截图(110 dpi),已全部目视核对,与文本提取一致
- `site/jev-visual.html` — 交互式可视化解读站(单文件、零依赖)
