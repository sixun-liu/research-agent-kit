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

## 长时间自主作业

把长任务切成可独立收尾的短周期。每周期结束必须：

1. 停止或回收进程；
2. 保存 provenance 与 artifact index；
3. 更新 experiment status；
4. 生成或更新 review 入口；
5. 判断继续、转向或停止。

不要让长队列替代推理。出现两次同类负结果时先回到离线诊断，不继续扩大参数网格。
