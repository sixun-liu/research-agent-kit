# 跨循环研究调度器

调度器位于单实验生命周期之上。它读取 append-only experiment/task events，识别研究停滞、
理论实践失衡、突破线索和流程债务。默认 `advisory`，不自动运行实验、终止进程或修改代码。

## 中断优先级

| 动作 | 优先级 | 典型触发 | 必须输出 |
|---|---:|---|---|
| `INTEGRITY` | P0 | 结果出现但未冻结、invalid provenance | 仪器/配置裁决；禁止解释结果 |
| `BREAKTHROUGH` | P1 | 未处理的反直觉观察 | 替代解释、最低成本重复、一个判别实验 |
| `REFLECT` | P2 | 同假说族连续负例或长期无进展 | 共同失败机制、因果图、一个下一实验 |
| `INTUITION` | P3 | 长期无进展、局部搜索疑似耗尽 | 盲数据漫游/跨域类比、最多三个假说、一个最低成本 probe |
| `PRACTICE_SYNC` | P2 | 连续理论循环 | 验证最新理论预测的最低成本干预 |
| `THEORY_SYNC` | P2 | 连续实践循环 | 可证伪机制预测，不是结果复述 |
| `SYNTHESIS` | P3 | 多轮未做阶段综合 | 主要矛盾、baseline、parked lanes、退出门更新 |
| `EFFICIENCY_REVIEW` | P3 | wall/compute 超预算且无进展 | 回放、缓存、早停或代理层的成本收益 |
| `HUMAN_REVIEW` | P4 | 关键人工审查积压 | 紧凑图、原始上下文和明确问题 |

## 计数语义

- 连续负例只统计：`decision=negative`、预期动作发生或不适用、完成信号确认或不适用。
- 连续负例按 `hypothesis_family` 分组；不同假说族不能相加。`failure_axis` 用于判断是共同机制
  还是异质失败。
- “进展”包括指标改善、降低不确定性、可靠关闭路线和效率提升。负结果可以是
  `route_closed` 进展。
- 理论/实践 streak 来自实验预注册的 `work_mode`，不是根据标题猜测。
- wall/compute 时间由结案显式记录；不同项目在 `scheduler.yaml` 设置预算，不在 skill 中写死。

## 操作方式

1. 每次实验结案后运行 `evaluate_research_scheduler.py --root <project>`，只读查看建议。
2. 人或主 agent 确认触发合理后，增加 `--enqueue` 将建议写入 `tasks.jsonl` 和 discussion card。
3. 处理器可以使用子 agent，但必须给出窄问题、只读输入和固定输出契约。
4. 用 `complete_research_task.py` 结案任务；任务结果可以引用 artifact/insight。
5. 调度器发现同类 task 仍 queued 时不重复入队。

## 创造性护栏

触发条件可以机械化，研究内容不能机械化。调度器只决定“现在需要反思/理论/实践/人工判断”，
不决定具体方法。`REFLECT`、`INTUITION` 和 `BREAKTHROUGH` 处理器最多保留少量候选，最后
必须收敛为一个最小判别实验，不能生成无限 brainstorm 菜单。

`discussion_root` 是草稿接口。子 agent 原始意见和发散材料留在那里；只有主 agent 综合后的
实验、insight 或 claim 才进入正典 registry。
