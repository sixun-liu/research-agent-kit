# 阶段收敛与实验生命周期

## 阶段

| 阶段 | 一阶问题 | 允许的证据 | 退出条件 |
|---|---|---|---|
| `understanding` | 论文主张、代码谱系和协议是什么 | 论文/源码、官方产物、版本与许可审计 | claim-protocol matrix 完整并选定最小复现目标 |
| `reproduction` | 公开结果能否在冻结协议下重现 | smoke、pilot、官方同图、逐 seed 重复 | baseline 复现闭环或形成证据充分的不可复现说明 |
| `exploration` | 信号在哪里、边界在哪里 | 旧产物、离线探针、小型 smoke | 找到可证伪候选和 canonical baseline |
| `attack` | 候选机制是否成立 | 单变量、闭环、因果干预 | 候选通过主门或按停止条件关闭 |
| `convergence` | 是否跨条件稳定 | 正式口径、重复、安全集、完整图证 | 通过项目定义的 stage-exit gates |
| `writing` | 主张是否站得住 | claim-evidence matrix、限制、复现 | paper-ready claim 全部闭环 |
| `complete` | 归档与迁移 | 冻结 artifact、代码和结论 | 项目结案 |

改变阶段前必须关闭 active experiment。`understanding` 允许 baseline 暂缺；进入
`reproduction` 时必须冻结代码、配置和评测协议。之后每个阶段只保留一个 canonical baseline、一个当前主要
矛盾和一个 active candidate；其他路线显式放入 `parked_lanes`。批量填 benchmark 前先确认
候选已经进入 `convergence`。

## Canonical Baseline

Baseline 不是方法昵称。它至少绑定：稳定 ID、名称、Git commit、展开配置和评测协议。每张
实验卡记录 `baseline_id` 和唯一变量。跨 baseline 的历史比较只能生成线索，不能冒充单变量
因果证据。

## 生命周期

1. `new_experiment.py`：复现使用 `replication` 模板并绑定目标 claim、参考产物和协议；
   单变量新假说使用 `formal`；小型诊断使用 `probe/oracle/instrumentation`。
2. `freeze_experiment.py`：结果前冻结 commit、展开配置 hash、数据切片、输出、seed/repeat、
   禁用输入和完成 beacon。
3. 执行最低成本证据阶梯；长任务用 `record_checkpoint.py` 追加进展和 compute，run 后用
   `record_observation.py` 保存数据散步观察。
4. `register_artifact.py`：先登记实际存在的图、表、dump 或日志。
5. `close_experiment.py`：追加 closure event，记录事实、解释、限制、下一项和 scoreboard/claim
   状态；同时确认预期动作和完成 beacon 是否真实发生，再清空 active experiment。动作未发生
   时只能判 `inconclusive` 或 `invalid_provenance`，不能据此判方法正负。
6. `audit_research_state.py --strict`：阶段转移、主线晋级或论文 claim 前必须通过。
7. `evaluate_research_scheduler.py`：结案后检查跨循环中断；默认只读，确认后才显式入队。
8. `research_status.py`：随时只读查看 active experiment、checkpoint、审查债务和调度建议。

主张使用 `register_claim.py` 追加登记；修订通过 `supersedes` 指向旧 claim，不覆盖历史。
`paper-ready` 至少需要 experiment 与 artifact ID、限制项和已完成/不需要的人工确认。

`promote` 不等于效果看起来不错。它要求项目级晋级门已满足，并且 scoreboard、claim、artifact
和 human review 没有未说明的 pending 项。

## 数据散步

每个 run 结束后，在查看主指标之外快速检查分布、最差段、异常空间模式和恢复行为。记录
1-3 条事实观察；意外现象可进入 breakthrough lane，但不能跳过 provenance 与替代解释。

## 领域 Profile

`research/profile.yaml` 只保存领域适配项：主指标、上尾指标、禁用输入、晋级门和人工审查要求。
通用 skill 不应写入 SLAM、湿实验或特定 benchmark 的专用规则。

论文项目在建 baseline 前还应遵循 `paper-reproduction.md`。阅读和协议恢复属于
`understanding` 控制任务，不为了填生命周期而伪装成 experiment。
