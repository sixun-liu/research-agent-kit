# GPF 科研实现工作流适配

本文件把 Claude GPF 的科研实现方法论作为 external workflow 输入映射到本 skill。它不是第二套
project stage 或 registry，不覆盖项目级 `AGENTS.md`、预注册门槛和证据权限。

## 目录

1. 来源与许可
2. 状态映射
3. 直接吸收
4. 需改写后吸收
5. 不吸收
6. 项目交接字段

## 1. 来源与许可

接收批次：2026-07-17，staging 路径 `docs_from_claude/gpf_workflows/`。

| Source | Version | SHA256 |
|---|---|---|
| `README.md` | router v2.0 | `8aa58475bf649a0bce82a12fa949af6f8fbdbe740753da577cb1d365e31d2782` |
| `_shared_conventions.md` | v1.4 | `e9bc1a872bc5e096a229858f9adc9f7e200559da5a8f091dc5ccd1ce4d8b8dca` |
| `research_implementation_workflow.md` | v2.2 | `26aad31866cc6d077d9eebbb7376ad575fda800694aae16692e53464bb9a4bc8` |

共享约定声明许可为 CC BY 4.0。本适配为摘要、映射和批判性改写；引用 GPF 的概念时保留来源与
版本。Claude 的交接说明确认当前是精选包，不包含 router 所列其他 workflow 和 tools；因此只
声明“科研实现适配已接收”，不能声明完整 GPF 系统已安装。

## 2. 状态映射

GPF Phase 只作为方法清单，持久状态仍使用本 skill：

| GPF | 本 skill | 生命周期处理 |
|---|---|---|
| Phase 1 论文拆解 | `understanding` | 文献/协议控制任务，不创建 EXP |
| Phase 2 代码评估 | `understanding` / `reproduction` 前置 | lineage、license、可运行性和成本审计 |
| Phase 3 代码整改 | `reproduction` | 兼容修复；行为 parity 用 probe，结果对齐用 replication |
| Phase 4 集成设计 | `exploration` | 形成可证伪候选，不直接改主线 |
| Phase 5 发散 | `exploration` / breakthrough lane | 开放问题和候选池，不冒充实验结论 |
| Phase 6 实验设计 | `attack` 前置 | formal preregistration、对照和停止条件 |
| Phase 7 执行迭代 | `attack` / `convergence` | evidence ladder、checkpoint、closure、scheduler |
| Phase 8 撰写 | `writing` | claim-evidence closure 后写作 |

禁止同时在 `project_state.yaml` 保存 GPF Phase 和本 skill stage。需要展示时动态计算映射。

## 3. 直接吸收

以下机制补强现有工作流：

1. **License 硬阻断**：代码评估前记录 license、兼容性和开源/商用约束；无 license 默认保留权利。
2. **论文--代码歧义四级**：`specified`、`partial`、`unspecified`、`conflict`；每项绑定论文/代码锚点。
3. **隐藏假设清单**：输入、计算、训练、环境、评估五类，进入 claim-protocol matrix。
4. **可修改性审计**：接口、耦合、验证方法和替换成本在 runtime patch 前明确。
5. **行为锚点与两顶帽子**：结构重构和行为改变分开；每个小重构先做确定性 parity 再提交。
6. **集成拓扑顺序**：依赖优先、重叠面优先、可验证性优先；一次只加入一个机制。
7. **三层循环**：小时级参数、天级方案、周级方向；连续循环无新信息时上移层级。
8. **复现写回理解**：环境坑、paper/code conflict、数值陷阱和负结果写入稳定理解材料，事实与解释分栏。

## 4. 需改写后吸收

| GPF 表述 | 本 skill 适配 |
|---|---|
| baseline 在论文值 `±2%` 通过、3 天仍超 `±5%` 止损 | 百分比不是跨领域定律；改为项目预注册 acceptance envelope、成本包络和不可比条件 |
| 发表档固定 `>=3 seeds` | seed/repeat 数由方差、效应、预算和 claim 权限预注册；单 seed 不支持稳定提升主张 |
| “均值差大于标准差”即显著 | 报逐 seed、分布、区间、效应量与适用统计方法，不把该启发式称为显著性检验 |
| 前 10--20% 曲线通常可判趋势 | 只有预注册 early proxy 与最终指标相关性已验证时才可早停 |
| 每次只调一个超参 | 因果诊断优先单变量；正式调参可用结构化搜索，但调参预算须对称且完整记录 |
| 并行跑多组配置 | 服从项目 GPU ownership、唯一启动方、信标判重和 active experiment 约束 |
| 结果不好先查随机性 | 先查 provenance、预期动作和完成信号，再按 information/calibration/alignment/consumption/feedback 分层 |

## 5. 不吸收

- 不复制 GPF 的八阶段状态机到 registry；
- 不把教学导航的骨干/次优/前沿作为实验优先级或证据强度；
- 不把行数、篇数、固定天数或百分比启发式升级为通用硬门；
- 不自动关闭安全/成本监督 hook；运行环境策略由用户和项目契约决定；
- 不让大模型处理可由 ID、hash、schema、API 或 parser 确定的问题；机械检查优先；
- 不导入未随批次到达的 GPF workflow/tools，也不猜测其行为。

## 6. 项目交接字段

Claude/GPF 向项目交付科研实现材料时至少提供：

- source version、license、稳定 ID、URL、retrieval date 和 hash；
- paper/code ambiguity 表，含 paper anchor、code anchor、状态和待裁决动作；
- hidden assumptions 与 claim-protocol matrix 的字段映射；
- baseline 可信度、reference artifact、环境/预算/evaluation 口径；
- code quality 只保留会影响复现或修改安全的发现；
- behavior anchor、compatibility patch 边界和验证命令；
- 已验证事实、internal interpretation、unverified lead 分开；
- 唯一下一取证或判别问题。

接收方抽验关键来源后，把稳定快照收入 `references/`；运行状态仍只进入本 skill registry。
