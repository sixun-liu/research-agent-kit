# 论文理解与结果复现

这套前置流程服务于“先理解，再复现；稳定后再自由探索”。论文阅读不是实验，结果复现也不是
方法消融。两者应先建立事实基座，再进入通用研究循环。

文献检索、筛选、带锚点摘录和来源晋升遵循 `literature-workflow.md`。协作者研读稿属于
`internal_synthesis`：应先快照到稳定 `references/`，再回查论文、代码或原始结果；不能把 staging
inbox 或未核调研稿直接当作论文事实。

## 阶段总览

```text
understanding -> reproduction -> exploration -> attack -> convergence -> writing
```

### Understanding

一阶问题是：论文到底主张了什么，哪份代码和哪套协议对应这些主张？

这个阶段不要求 canonical baseline 已经冻结，也不为阅读活动创建 experiment。维护短控制文档和
claim-protocol matrix，直到下面的退出门全部满足：

1. 固定论文身份：标题、作者、venue、DOI/arXiv ID、版本日期和本地文件 hash。
2. 拆出主张：方法主张、机制主张、结果主张、适用边界，分别绑定章节、公式、表格或图。
3. 核对代码谱系：论文原始代码、作者公开重实现、第三方复刻或独立重写；记录 commit、许可和
   与目标论文版本的已知漂移。
4. 恢复协议：任务、数据/环境版本、预处理、预算定义、action repeat、训练比例、模型规模、
   seed、评测 episode、聚合统计和参考曲线来源。
5. 建立成本包络：最小 smoke、单 seed pilot、正式重复各需要的 GPU 小时、磁盘和环境依赖。
6. 选择一个最小结果主张作为首个复现目标，并说明为什么它既有代表性又可在现有算力内完成。

理解产物至少包含：

- 一页论文主张图；
- paper/code/version ledger，包含来源类别、版本、稳定路径和 hash；
- claim-protocol matrix；
- 代码组件到公式的映射；
- 带页/节/公式/图表/代码锚点的 extraction table；
- 未决歧义和向导师确认的问题；
- 首个复现目标及成本估计。

摘要不能替代协议恢复。论文、公开代码和第三方实现冲突时，分别记录事实，不用“官方”一词
抹平代码谱系。

### Reproduction

一阶问题是：在冻结的代码和协议下，能否重现声明的论文结果或性能包络？

进入该阶段时必须冻结 canonical baseline。每个计算周期使用 `replication` 模板，并声明复现
等级：

- `exact_artifact`：相同代码、协议和参考产物，目标是重算或复核；
- `author_reimplementation`：使用作者公开重实现，允许明确记录的版本漂移；
- `independent_reimplementation`：独立实现同一算法和协议；
- `conceptual`：只复现定性机制，不声称数值结果等价。

复现卡必须绑定目标 claim、论文图表/官方曲线、协议匹配清单、主指标、seed/repeat policy、
停止条件和完成信号。兼容性补丁要独立提交、默认关闭，并说明它改变的是运行兼容性还是算法。

## Claim-Protocol Matrix

每个目标结果至少记录以下字段：

| 字段 | 内容 |
|---|---|
| Claim ID | 稳定 ID 和一句可核验主张 |
| Source | 论文版本、章节、图或表 |
| Reference artifact | 官方 JSON、表格、checkpoint 或数字化曲线及 hash |
| Code lineage | 原始代码/作者重实现/第三方/独立实现、commit、license |
| Task and environment | 任务、环境版本、wrapper、预处理、action repeat |
| Budget semantics | frame/env step/agent step/update 的定义和上限 |
| Training protocol | 展开配置、模型规模、replay ratio、优化器和 checkpoint 规则 |
| Evaluation protocol | policy mode、episode 数、评测频率、聚合和归一化 |
| Repetitions | seed 列表、重复数、配对方式和失败 seed 处理 |
| Acceptance envelope | 曲线/最终分数容差、方差口径和不可比条件 |
| Cost envelope | 预计 GPU 小时、磁盘、早期完整性 beacon |

字段未知时写 unknown 和取证动作，不能用默认值悄悄补齐。

## 证据阶梯

1. **现有产物审计**：先检查论文源文件、官方 score、旧日志和公开 checkpoint。
2. **环境与仪器自检**：设备、矩阵计算、环境 reset/step、metric parser 和 known-answer check。
3. **最小 smoke**：只证明 plumbing；不形成性能结论。
4. **短 pilot**：测吞吐、显存、磁盘增长、checkpoint/resume 和早期数值稳定性。
5. **单目标 replication**：跑一个冻结任务和 seed，生成与参考同坐标的曲线。
6. **重复与安全集**：按预注册 seed policy 扩展，报告逐 seed、均值、离散度和失败尾部。
7. **跨任务扩展**：只有首个结果协议闭环后才扩大 benchmark。

长跑前必须用实测吞吐计算 ETA。若 pilot 已证明完整运行不符合时间预算，先调整复现目标，
不能为了“已经开始”继续烧卡。

## 复现裁决

观察与解释分开记录，并把项目语言映射到通用 decision：

| 复现结论 | 通用 decision |
|---|---|
| 协议匹配且进入预注册性能包络 | `promote` |
| 趋势一致但 seed、预算或版本证据不足 | `promising_unresolved` |
| 协议有效但结果稳定落在包络外 | `negative` |
| 代码/环境/预算口径不匹配 | `invalid_provenance` |
| 运行或评测未完成 | `inconclusive` |

“跑通”只等于工程成功；“趋势一致”只等于部分复现；“数值复现”需要协议、重复和参考产物同时
闭环。负结果先检查版本、环境和评测口径，再讨论算法差异。

## 进入自由探索

从 `reproduction` 进入 `exploration` 至少需要：

1. 一个 canonical baseline 已冻结并完成可恢复运行；
2. 至少一个目标结果已有对照图和明确裁决，或有证据充分的不可复现说明；
3. 环境、metric、checkpoint/resume 和资源信标均已验证；
4. 论文主张与本地证据的缺口已登记；
5. 后续候选问题确实超出“修复复现协议”，需要新假说或机制干预。

此后才使用单变量 formal 消融、突破通道和跨周期 scheduler。不要把兼容性修复包装成方法创新，
也不要从单 seed 复现直接进入论文级机制结论。

## 服务器长跑纪律

研究控制面不自动启动进程，但项目执行层至少应落实：

- GPU 查询作为唯一判忙依据；
- started 信标判重、绝对 logdir、detached 进程和完整命令；
- commit、展开配置、环境版本、seed、开始时间和输出路径冻结；
- 启动前磁盘/共享内存检查；
- checkpoint 写入、恢复实测和停止窗口；
- STATUS 页面记录 running/stopped/completed、PID、进度、ETA 和最新 checkpoint；
- 停止后保留原始日志，并写明信号、原因、最后观测步和可恢复步。

进程控制只能有一个执行方。状态查询、论文研读和独立复算可以由其他协作者只读完成。
