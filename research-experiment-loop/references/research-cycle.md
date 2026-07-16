# 研究实验循环

## 目的

这套循环用于创造性研究，不是把科研变成机械填表。它解决三类常见失控：

1. 没有先查旧产物就重复烧卡；
2. 代码、配置、dump 和结论跨状态漂移；
3. 数字、图和解释散落，下一轮无法恢复真正的认知。

## 两条并行通道

### 计划通道

来自 benchmark 缺口、机制矩阵、审稿风险或明确待办。它保证覆盖面和收尾能力。

### 直觉/突破通道

来自异常的大幅收益、反直觉图像、跨信号矛盾或失败模式。进入该通道需满足至少一项：

- 效应远大于常见运行波动；
- 可能改变方法主线或理论解释；
- 解释现有多个未决现象；
- 低成本就能做出高区分度判别。

突破通道不是免审通道。优先级提高，同时必须列出随机性、口径漂移、数据泄漏和替代机制。

## 一轮标准流程

### A. 恢复

读取 `AGENTS.md`、当前状态、计划、短清单、scoreboard、最近 devlog 和 machine registry。
核对 canonical repo 的 branch/commit/tracked dirty。只把有 fingerprint 的结果当正式证据。
同时核对当前阶段、北极星、主要矛盾、canonical baseline ID、active candidate 和 parked lanes。
方法昵称相同但 baseline ID 不同的结果只能作历史对照。
机器状态由 `researchctl.py status` 恢复；`CURRENT_STATE.md` 只补充人工判断。PLAN 决定阶段意图，
TODO 只选择近期动作，不能用其中的文字覆盖 registry 事实。

### B. 一句话问题

问题要能让两个解释产生不同预测。例如：

> 改善来自更纯的静态尺度估计，还是来自关键帧随机漂移？

“试试看是否更好”不是可判别问题。

### C. 预注册

至少记录：

- hypothesis 与 alternatives；
- independent variable；
- control 与不变量；
- primary/tail/visual metrics；
- output 和 provenance；
- promotion/stop conditions。

还要记录 baseline ID、唯一变量、预期中间动作和完成正向信号。预期动作没有发生时，结果不能
解释成方法正负证据。

小型机制诊断使用 `probe`，外部理想参考使用 `oracle`，仪器自检使用 `instrumentation`。
三者自动标为 diagnostic/debug-only，不能直接 `promote`；若发现值得主张的效果，另建
`formal` 卡并重新冻结正式口径，不把诊断卡改名升格。

### D. 证据梯度

先复用已有 dump。离线统计能回答就不跑 tracking；tracking 能判负就不跑 mapping；
单序列未过机制门槛就不铺 benchmark。每一级都应产出明确裁决，而不是“再扫几个参数”。

### E. 受控修改

一次只引入一个机制变量。诊断开关默认关闭，禁止序列名分支。代码变化后冻结新 commit，
再生成 dump；不要用旧 dump 证明新 runtime 路径。

### F. 双轴和上尾

平均 ATE 不能替代 median/max/worst-window。Mapping 坏帧与 tracking 坏段必须分开定位。
对闭环系统还要检查当前动作是否改变未来 pose/depth/signal，避免把旁路结论外推到在线系统。

### G. 人工审查

紧凑图应把可比较项放在相同行/列，包含原图、动作/信号和最终输出。无对应项留空，
不要为了填满版面混入无关图。记录用户是否亲眼确认，不把自动指标当最终视觉裁决。

### H. 结案

分别写：事实、观察、解释、反证、裁决、下一项最小判别实验。完成的动作进 devlog，
可引用结果才进 scoreboard，突破线索进 insights registry。
只有形成可复用路线决策或机制结论时才追加 DEVLOG；TODO 删除已完成动作并保留唯一下一问题。
PLAN 仅在主要矛盾、路线地位或阶段退出门变化时更新。

每个 run 结束后做一次短数据散步：检查分布、最差段、异常空间模式和恢复行为，保存1-3条
观察。结案时明确 artifact、人工审查、scoreboard 和 claim registry 是已更新、无需更新还是
仍 pending；`promote` 不允许 pending。

结案后运行只读 scheduler。连续负例必须按同一假说族统计；理论/实践失衡、意外观察和耗时
停滞分别触发对应任务。触发器只改变下一轮工作模式，不直接决定科学结论或自动发车。

## 阶段外循环

实验内循环解决单个可证伪问题；每个块结束后检查阶段退出门。进入收敛期后停止无关新路线，
只允许 canonical candidate 的重复、安全集、正式口径与图证。进入写作期后，新实验必须直接
关闭 claim-evidence matrix 的缺口，否则停车。详见 `stage-and-lifecycle.md`。

## 长时间自主作业

把长任务切成可独立收尾的短周期。每周期结束必须：

1. 停止或回收进程；
2. 保存 provenance 与 artifact index；
3. 更新 experiment status；
4. 生成或更新 review 入口；
5. 判断继续、转向或停止。

不要让长队列替代推理。出现两次同类负结果时先回到离线诊断，不继续扩大参数网格。
单次运行较长时，在机制边界或固定 compute chunk 后写一条 checkpoint；只记录新增 compute、
是否有实质进展和动作状态。状态未变化时不写长篇日志，运行 `research_status.py` 即可恢复现场。
